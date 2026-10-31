"""S3 behavior against a fake client. CI does not need a live bucket."""

from pathlib import Path

import pytest

from secureai_shared.storage import S3Storage, new_object_key


class FakeS3:
    def __init__(self) -> None:
        self.created = False
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.conditions: list[object] = []
        self.dest: str | None = None

    def head_bucket(self, **kwargs: object) -> None:
        del kwargs
        raise RuntimeError("missing bucket")

    def create_bucket(self, **kwargs: object) -> None:
        del kwargs
        self.created = True

    def generate_presigned_post(
        self,
        *,
        Bucket: str,
        Key: str,
        Fields: dict[str, str],
        Conditions: list[object],
        ExpiresIn: int,
    ) -> dict[str, object]:
        del Bucket, ExpiresIn
        self.conditions = Conditions
        return {
            "url": "https://s3.example/bucket",
            "fields": {"key": Key, "Content-Type": Fields["Content-Type"], "policy": "signed"},
        }

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        del Bucket
        if Key not in self.objects:
            raise RuntimeError("missing")
        body, etag = self.objects[Key]
        return {"ContentLength": len(body), "ETag": f'"{etag}"'}

    def download_file(self, bucket: str, key: str, dest: str) -> None:
        del bucket, key
        self.dest = dest
        Path(dest).write_bytes(b"partial")
        raise RuntimeError("download failed")


def test_presign_caps_content_length_and_skips_bucket_create() -> None:
    client = FakeS3()
    storage = S3Storage(client, "secureai", auto_create=False, max_bytes=32)
    key = new_object_key("user_dev", "clip.mp4")
    ticket = storage.presign_post(key, "video/mp4")
    assert ticket is not None
    assert ticket.url.startswith("https://s3.example/")
    assert ["content-length-range", 1, 32] in client.conditions
    assert client.created is False


def test_auto_create_is_opt_in() -> None:
    client = FakeS3()
    S3Storage(client, "secureai", auto_create=True)
    assert client.created is True


def test_object_stat_reads_size_and_etag() -> None:
    client = FakeS3()
    storage = S3Storage(client, "secureai")
    key = new_object_key("user_dev", "clip.mp4")
    client.objects[key] = (b"abcdef", "abc123")
    stat = storage.object_stat(key)
    assert stat is not None
    assert stat.size == 6
    assert stat.etag == "abc123"


def test_failed_download_removes_the_temp_file() -> None:
    client = FakeS3()
    storage = S3Storage(client, "secureai")
    key = new_object_key("user_dev", "clip.mp4")
    with pytest.raises(RuntimeError, match="download failed"):
        storage.materialize(key)
    assert client.dest is not None
    assert not Path(client.dest).exists()
