"""Ed25519 report attestation: canonical bytes, sign, verify, and the audit row."""

from __future__ import annotations

import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from secureai_shared.attestation import (
    ALGORITHM,
    AttestationKeyError,
    AttestationRecord,
    MemoryAttestationStore,
    PostgresAttestationStore,
    attestation_payload,
    canonical_json,
    format_number,
    load_attestation_key,
    may_issue_attestation,
    normalize_pem,
)
from secureai_shared.db import Base, JobRow
from secureai_shared.settings import load_settings
from secureai_shared.storage import new_object_key
from secureai_shared.store import PostgresJobStore

WHEN = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


def _pem() -> str:
    key = Ed25519PrivateKey.generate()
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _payload(**overrides: object) -> str:
    values: dict[str, object] = {
        "job_id": "job_abc123abc123",
        "org_id": None,
        "prediction": "real",
        "confidence": 0.84,
        "model": "cpu-multisignal-v1",
        "signals": {"texture": 0.2, "motion": 0.1},
        "updated_at": WHEN,
        "limitations": "not legal evidence",
    }
    values.update(overrides)
    return attestation_payload(**values)  # type: ignore[arg-type]


def test_canonical_payload_is_compact_and_stable() -> None:
    payload = _payload()
    assert payload == _payload()
    assert payload == (
        '{"confidence":0.84,"job_id":"job_abc123abc123","limitations":"not legal evidence",'
        '"model":"cpu-multisignal-v1","org_id":null,"prediction":"real",'
        '"signals":{"motion":0.1,"texture":0.2},"status":"completed",'
        '"updated_at":"2026-11-01T12:00:00+00:00"}'
    )
    assert format_number(0.1) == "0.1"
    assert format_number(1) == "1"
    assert format_number(0.0) == "0"
    with pytest.raises(ValueError, match="non-finite"):
        format_number(float("nan"))
    assert canonical_json({"b": 1, "a": True}) == '{"a":true,"b":1}'


def test_sign_and_verify_round_trip() -> None:
    key = load_attestation_key(_pem(), "v1")
    payload = _payload(org_id="org_abc123abc123")
    signature = key.sign(payload)
    assert key.algorithm == ALGORITHM
    assert key.verify(payload, signature)
    assert key.verify(payload, signature, "v1")
    assert key.verify(payload, signature, None)
    assert not key.verify(payload, signature, "v2")
    assert not key.verify(payload + " ", signature)
    flipped = ("A" if signature[10] != "A" else "B")
    assert not key.verify(payload, signature[:10] + flipped + signature[11:])
    assert not key.verify(payload, "not-base64")
    assert "BEGIN PRIVATE KEY" not in repr(key)
    assert key.public_pem.startswith("-----BEGIN PUBLIC KEY-----")


def test_escaped_pem_and_bad_key_id() -> None:
    pem = _pem().strip().replace("\n", "\\n")
    settings = load_settings(
        {
            "AUTH_MODE": "dev",
            "DATABASE_URL": "postgresql+psycopg://db",
            "REDIS_URL": "redis://localhost:6379/0",
            "ATTESTATION_PRIVATE_KEY": pem,
            "ATTESTATION_KEY_ID": "rotate.v2",
        },
        role="api",
    )
    assert "\\n" not in settings.attestation_private_key
    loaded = load_attestation_key(settings.attestation_private_key, settings.attestation_key_id)
    assert loaded.key_id == "rotate.v2"
    assert normalize_pem("") == ""
    with pytest.raises(RuntimeError, match="ATTESTATION_PRIVATE_KEY"):
        load_settings(
            {
                "AUTH_MODE": "dev",
                "DATABASE_URL": "postgresql+psycopg://db",
                "REDIS_URL": "redis://localhost:6379/0",
                "ATTESTATION_PRIVATE_KEY": "not-a-pem",
            },
            role="worker",
        )
    with pytest.raises(AttestationKeyError, match="ATTESTATION_KEY_ID"):
        load_attestation_key(_pem(), "bad id")


def test_plan_gate() -> None:
    assert may_issue_attestation(auth_mode="clerk", quota_mode="enforce", plan="pro")
    assert may_issue_attestation(auth_mode="clerk", quota_mode="enforce", plan="team")
    assert not may_issue_attestation(auth_mode="clerk", quota_mode="enforce", plan="free")
    assert not may_issue_attestation(auth_mode="clerk", quota_mode="unlimited", plan="free")
    assert may_issue_attestation(auth_mode="dev", quota_mode="unlimited", plan="free")
    assert not may_issue_attestation(auth_mode="dev", quota_mode="enforce", plan="free")


def test_memory_store_keeps_the_first_signature() -> None:
    store = MemoryAttestationStore()
    record = AttestationRecord(
        job_id="job_abc123abc123",
        key_id="v1",
        algorithm=ALGORITHM,
        payload=_payload(),
        signature="c2ln",
        created_at=WHEN,
    )
    assert store.save(record) == record
    later = replace(record, created_at=WHEN + timedelta(seconds=5))
    assert store.save(later).created_at == WHEN
    changed = replace(record, signature="bmV3", created_at=WHEN + timedelta(seconds=9))
    assert store.save(changed).signature == "bmV3"
    assert store.get(record.job_id) is not None
    assert store.get(record.job_id).created_at == WHEN + timedelta(seconds=9)  # type: ignore[union-attr]


def _postgres_jobs() -> PostgresJobStore:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://secureai:secureai@127.0.0.1:5432/secureai",
    )
    try:
        probe = PostgresJobStore(url)
        with probe.engine.connect() as connection:
            connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS secureai_attestation_test")
            connection.commit()
        probe.engine.dispose()
        schema_url = url + ("&" if "?" in url else "?") + "options=-csearch_path%3Dsecureai_attestation_test"
        store = PostgresJobStore(schema_url)
        from secureai_shared.db import Base

        Base.metadata.drop_all(store.engine)
        Base.metadata.create_all(store.engine)
    except Exception as exc:
        if os.environ.get("REQUIRE_SERVICES") == "1":
            pytest.fail(f"postgres unavailable: {exc}")
        pytest.skip(f"postgres unavailable: {exc}")
    return store


def test_postgres_store_keeps_the_first_signature() -> None:
    jobs = _postgres_jobs()
    created = jobs.create(
        user_id="user_pg",
        filename="clip.mp4",
        content_type="video/mp4",
        byte_size=4,
        object_key=new_object_key("user_pg", "clip.mp4"),
    )
    store = PostgresAttestationStore(engine=jobs.engine)
    record = AttestationRecord(
        job_id=created.id,
        key_id="v1",
        algorithm=ALGORITHM,
        payload=_payload(job_id=created.id),
        signature="c2ln",
        created_at=WHEN,
    )
    assert store.save(record).created_at == WHEN
    again = store.save(replace(record, created_at=WHEN + timedelta(seconds=5)))
    assert again.created_at == WHEN
    updated = store.save(replace(record, signature="bmV3", created_at=WHEN + timedelta(seconds=9)))
    assert updated.signature == "bmV3"
    loaded = store.get(created.id)
    assert loaded is not None
    assert loaded.signature == "bmV3"
    assert loaded.created_at == WHEN + timedelta(seconds=9)


def _sqlite_attestation_store() -> tuple[PostgresAttestationStore, str]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    job_id = "job_abc123abc123"
    with Session(engine) as session:
        session.add(
            JobRow(
                id=job_id,
                user_id="user_dev",
                org_id=None,
                filename="clip.mp4",
                content_type="video/mp4",
                byte_size=4,
                object_key="media/user_dev/" + ("a" * 32) + ".mp4",
                object_etag=None,
                status="completed",
                prediction="real",
                confidence=0.5,
                detail=None,
                attempt=0,
                created_at=WHEN,
                updated_at=WHEN,
            )
        )
        session.commit()
    return PostgresAttestationStore(engine=engine), job_id


def _record(job_id: str, signature: str = "c2ln") -> AttestationRecord:
    return AttestationRecord(
        job_id=job_id,
        key_id="v1",
        algorithm=ALGORITHM,
        payload=_payload(job_id=job_id),
        signature=signature,
        created_at=WHEN,
    )


def test_insert_conflict_returns_the_first_attestation() -> None:
    store, job_id = _sqlite_attestation_store()
    record = _record(job_id)
    assert store.save(record).signature == "c2ln"

    def boom(candidate: AttestationRecord) -> AttestationRecord:
        del candidate
        raise IntegrityError("INSERT", {}, Exception("duplicate key"))

    store._write = boom  # type: ignore[method-assign]
    again = store.save(replace(record, created_at=WHEN + timedelta(seconds=4)))
    assert again.signature == "c2ln"
    stored_at = again.created_at
    if stored_at.tzinfo is None:
        stored_at = stored_at.replace(tzinfo=timezone.utc)
    assert stored_at == WHEN


def test_insert_conflict_still_updates_a_different_signature() -> None:
    store, job_id = _sqlite_attestation_store()
    record = _record(job_id)
    assert store.save(record).signature == "c2ln"
    real = store._write
    state = {"raised": False}

    def once(candidate: AttestationRecord) -> AttestationRecord:
        if not state["raised"]:
            state["raised"] = True
            raise IntegrityError("INSERT", {}, Exception("duplicate key"))
        return real(candidate)

    store._write = once  # type: ignore[method-assign]
    updated = store.save(replace(record, signature="bmV3", created_at=WHEN + timedelta(seconds=9)))
    assert updated.signature == "bmV3"
    loaded = store.get(job_id)
    assert loaded is not None
    assert loaded.signature == "bmV3"
