"""Object storage for uploaded media.

Filesystem is the local/dev default. S3-compatible storage (Railway bucket,
MinIO, R2) is the deployed path. Object keys are server-generated.
"""

from __future__ import annotations

import hashlib
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from secureai_shared.settings import Settings

_KEY = re.compile(r"media/[A-Za-z0-9_-]{1,80}/[a-f0-9]{32}\.(mp4|mov|webm|avi|mkv|bin)")
_SUFFIXES = {".mp4", ".mov", ".webm", ".avi", ".mkv"}


@dataclass(frozen=True)
class LocalMedia:
    path: Path
    cleanup: bool


@dataclass(frozen=True)
class ObjectStat:
    """Size and fingerprint recorded at enqueue and checked again before scoring."""

    size: int
    etag: str


@dataclass(frozen=True)
class PresignedUpload:
    """Browser POST. `fields` includes the policy that caps content-length-range."""

    url: str
    fields: dict[str, str]


def sanitize_user(user_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", user_id)[:80]
    return cleaned or "user"


def clean_filename(filename: str) -> str:
    base = Path(filename).name.replace("\x00", "")
    if not base or base in {".", ".."}:
        raise ValueError("invalid filename")
    return base[:255]


def new_object_key(user_id: str, filename: str) -> str:
    suffix = Path(clean_filename(filename)).suffix.lower()
    if suffix not in _SUFFIXES:
        suffix = ".bin"
    return f"media/{sanitize_user(user_id)}/{uuid4().hex}{suffix}"


def is_owned_key(user_id: str, key: str) -> bool:
    prefix = f"media/{sanitize_user(user_id)}/"
    return key.startswith(prefix) and _KEY.fullmatch(key) is not None


class FileSystemStorage:
    """Store objects under MEDIA_ROOT. Suitable for local/dev."""

    supports_presign = False

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes, content_type: str | None) -> None:
        del content_type
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def materialize(self, key: str, *, etag: str | None = None) -> LocalMedia:
        path = self._path(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        if etag is not None:
            current = hashlib.md5(path.read_bytes()).hexdigest()
            if current != etag.strip('"'):
                raise FileNotFoundError(key)
        return LocalMedia(path=path, cleanup=False)

    def object_size(self, key: str) -> int | None:
        stat = self.object_stat(key)
        if stat is None:
            return None
        return stat.size

    def object_stat(self, key: str) -> ObjectStat | None:
        path = self._path(key)
        if not path.is_file():
            return None
        data = path.read_bytes()
        return ObjectStat(size=len(data), etag=hashlib.md5(data).hexdigest())

    def presign_post(self, key: str, content_type: str | None) -> PresignedUpload | None:
        del key, content_type
        return None

    def delete(self, key: str) -> None:
        """Remove the object. A missing file is already gone."""

        self._path(key).unlink(missing_ok=True)

    def _path(self, key: str) -> Path:
        if _KEY.fullmatch(key) is None:
            raise ValueError("invalid object key")
        root = self.root.resolve()
        path = (root / key).resolve()
        if not path.is_relative_to(root):
            raise ValueError("invalid object key")
        return path


class S3Storage:
    """S3-compatible bucket. `client` is a boto3 S3 client."""

    supports_presign = True

    def __init__(
        self,
        client: object,
        bucket: str,
        *,
        auto_create: bool = False,
        max_bytes: int = 50_000_000,
    ) -> None:
        self.client = client
        self.bucket = bucket
        self.max_bytes = max_bytes
        if auto_create:
            self._ensure_bucket()

    def put(self, key: str, data: bytes, content_type: str | None) -> None:
        self._check(key)
        self.client.put_object(  # type: ignore[attr-defined]
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type or "application/octet-stream",
        )

    def exists(self, key: str) -> bool:
        self._check(key)
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)  # type: ignore[attr-defined]
        except Exception:
            return False
        return True

    def materialize(self, key: str, *, etag: str | None = None) -> LocalMedia:
        """Download the object. When `etag` is set, S3 must still match it.

        IfMatch rejects a rewrite that landed between the head check and this
        GET, so the new bytes are not scored.
        """

        self._check(key)
        handle = tempfile.NamedTemporaryFile(suffix=Path(key).suffix, delete=False)
        handle.close()
        dest = Path(handle.name)
        extra: dict[str, str] | None = None
        if etag:
            quoted = etag if etag.startswith('"') else f'"{etag}"'
            extra = {"IfMatch": quoted}
        try:
            kwargs: dict[str, object] = {"ExtraArgs": extra} if extra else {}
            self.client.download_file(self.bucket, key, str(dest), **kwargs)  # type: ignore[attr-defined]
        except Exception:
            dest.unlink(missing_ok=True)
            raise
        return LocalMedia(path=dest, cleanup=True)

    def object_size(self, key: str) -> int | None:
        stat = self.object_stat(key)
        if stat is None:
            return None
        return stat.size

    def object_stat(self, key: str) -> ObjectStat | None:
        self._check(key)
        try:
            head = self.client.head_object(Bucket=self.bucket, Key=key)  # type: ignore[attr-defined]
        except Exception:
            return None
        length = head.get("ContentLength")
        if length is None:
            return None
        etag = str(head.get("ETag", "")).strip('"')
        return ObjectStat(size=int(length), etag=etag)

    def presign_post(self, key: str, content_type: str | None) -> PresignedUpload | None:
        """Presigned POST whose policy rejects bodies outside 1..max_bytes.

        content-length-range is the cap. The worker later re-reads size and
        ETag, so a rewrite after the job is accepted fails the job instead of
        being scored.
        """

        self._check(key)
        content_type = content_type or "application/octet-stream"
        payload = self.client.generate_presigned_post(  # type: ignore[attr-defined]
            Bucket=self.bucket,
            Key=key,
            Fields={"Content-Type": content_type},
            Conditions=[
                ["content-length-range", 1, self.max_bytes],
                {"Content-Type": content_type},
            ],
            ExpiresIn=900,
        )
        url = payload.get("url") if isinstance(payload, dict) else None
        fields = payload.get("fields") if isinstance(payload, dict) else None
        if not isinstance(url, str) or not isinstance(fields, dict):
            return None
        return PresignedUpload(url=url, fields={str(name): str(value) for name, value in fields.items()})

    def delete(self, key: str) -> None:
        """Remove the object. A missing key is already gone."""

        self._check(key)
        self.client.delete_object(Bucket=self.bucket, Key=key)  # type: ignore[attr-defined]

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)  # type: ignore[attr-defined]
        except Exception:
            self.client.create_bucket(Bucket=self.bucket)  # type: ignore[attr-defined]

    def _check(self, key: str) -> None:
        if _KEY.fullmatch(key) is None:
            raise ValueError("invalid object key")


def build_s3_client(settings: Settings) -> object:
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint or None,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
    )


def build_storage(settings: Settings) -> FileSystemStorage | S3Storage:
    if settings.storage_backend == "filesystem":
        return FileSystemStorage(Path(settings.media_root))
    if settings.storage_backend == "s3":
        return S3Storage(
            build_s3_client(settings),
            settings.s3_bucket,
            auto_create=settings.s3_auto_create_bucket,
            max_bytes=settings.max_upload_bytes,
        )
    raise RuntimeError(f"Unsupported STORAGE_BACKEND={settings.storage_backend!r}")
