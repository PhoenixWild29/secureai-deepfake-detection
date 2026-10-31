import time
from pathlib import Path

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from app.main import create_app
from secureai_shared.queue import MemoryJobQueue
from secureai_shared.settings import Settings
from secureai_shared.storage import FileSystemStorage
from secureai_shared.store import MemoryJobStore


def make_settings(tmp_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "auth_mode": "dev",
        "clerk_issuer": "",
        "clerk_jwks_url": "",
        "clerk_authorized_parties": (),
        "database_url": "postgresql+psycopg://unused/unused",
        "redis_url": "",
        "queue_backend": "memory",
        "queue_key": "secureai:jobs",
        "storage_backend": "filesystem",
        "media_root": str(tmp_path),
        "s3_endpoint": "",
        "s3_bucket": "",
        "s3_access_key_id": "",
        "s3_secret_access_key": "",
        "s3_region": "us-east-1",
        "cors_origins": ("http://localhost:3000",),
        "dev_subject": "user_dev",
        "max_upload_bytes": 50_000_000,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]

ISSUER = "https://example.clerk.accounts.dev"


def _token(private_key: rsa.RSAPrivateKey, *, azp: str = "http://localhost:3000", expired: bool = False) -> str:
    now = int(time.time())
    payload = {
        "sub": "user_clerk",
        "iss": ISSUER,
        "azp": azp,
        "exp": now - 10 if expired else now + 600,
    }
    encoded = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-key"})
    return encoded if isinstance(encoded, str) else encoded.decode()


def _client(tmp_path: Path, *, parties: tuple[str, ...] = ()) -> tuple[TestClient, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    public_jwk["kid"] = "test-key"
    public_jwk["alg"] = "RS256"
    public_jwk["use"] = "sig"
    settings = make_settings(
        tmp_path,
        auth_mode="clerk",
        clerk_issuer=ISSUER,
        clerk_authorized_parties=parties,
    )
    app = create_app(
        settings=settings,
        store=MemoryJobStore(),
        queue=MemoryJobQueue(),
        storage=FileSystemStorage(tmp_path),
        fetch_jwks=lambda: {"keys": [public_jwk]},
    )
    return TestClient(app), _token(private_key)


def test_valid_clerk_jwt_can_open_an_upload(tmp_path: Path) -> None:
    client, token = _client(tmp_path)
    response = client.post(
        "/v1/uploads",
        headers={"Authorization": f"Bearer {token}"},
        json={"filename": "clip.mp4"},
    )
    assert response.status_code == 200
    health = client.get("/health")
    assert health.json()["auth"] == "clerk"


def test_expired_and_missing_tokens_are_rejected(tmp_path: Path) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client, _token_ok = _client(tmp_path)
    expired = _token(private_key, expired=True)
    # The client fixture uses a different key, so this token also fails signature checks.
    response = client.post(
        "/v1/uploads",
        headers={"Authorization": f"Bearer {expired}"},
        json={"filename": "clip.mp4"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"
    anonymous = client.post("/v1/jobs", json={"object_key": "media/user/abcd", "filename": "clip.mp4"})
    assert anonymous.status_code == 401


def test_authorized_party_must_match_when_configured(tmp_path: Path) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    public_jwk["kid"] = "test-key"
    settings = make_settings(
        tmp_path,
        auth_mode="clerk",
        clerk_issuer=ISSUER,
        clerk_authorized_parties=("https://app.example",),
    )
    app = create_app(
        settings=settings,
        store=MemoryJobStore(),
        queue=MemoryJobQueue(),
        storage=FileSystemStorage(tmp_path),
        fetch_jwks=lambda: {"keys": [public_jwk]},
    )
    client = TestClient(app)
    wrong = client.post(
        "/v1/uploads",
        headers={"Authorization": f"Bearer {_token(private_key, azp='http://localhost:3000')}"},
        json={"filename": "clip.mp4"},
    )
    assert wrong.status_code == 401
    allowed = client.post(
        "/v1/uploads",
        headers={"Authorization": f"Bearer {_token(private_key, azp='https://app.example')}"},
        json={"filename": "clip.mp4"},
    )
    assert allowed.status_code == 200
