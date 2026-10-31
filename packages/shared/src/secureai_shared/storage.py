"""Object storage for uploaded media.

Filesystem is the local/dev default. S3-compatible storage (Railway bucket,
MinIO, R2) is the deployed path. Object keys are server-generated.
"""

from __future__ import annotations

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

    def materialize(self, key: str) -> LocalMedia:
        path = self._path(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        return LocalMedia(path=path, cleanup=False)

    def presign_put(self, key: str, content_type: str | None) -> str | None:
        del key, content_type
        return None

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

    def __init__(self, client: object, bucket: str) -> None:
        self.client = client
        self.bucket = bucket
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

    def materialize(self, key: str) -> LocalMedia:
        self._check(key)
        handle = tempfile.NamedTemporaryFile(suffix=Path(key).suffix, delete=False)
        handle.close()
        dest = Path(handle.name)
        self.client.download_file(self.bucket, key, str(dest))  # type: ignore[attr-defined]
        return LocalMedia(path=dest, cleanup=True)

    def presign_put(self, key: str, content_type: str | None) -> str | None:
        self._check(key)
        return self.client.generate_presigned_url(  # type: ignore[attr-defined]
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ContentType": content_type or "application/octet-stream",
            },
            ExpiresIn=900,
        )

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
        return S3Storage(build_s3_client(settings), settings.s3_bucket)
    raise RuntimeError(f"Unsupported STORAGE_BACKEND={settings.storage_backend!r}")
