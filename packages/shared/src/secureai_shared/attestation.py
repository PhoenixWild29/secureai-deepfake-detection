"""Ed25519 attestation over a completed detection report.

The signature covers one canonical JSON string. Verify those exact UTF-8
bytes. Parsing the JSON and encoding it again can change the bytes and
make a real signature look invalid.

This is not a blockchain anchor and not legal evidence. It shows that the
API's attestation key signed this payload. The detector's limits still apply.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from sqlalchemy.orm import Session, sessionmaker

from secureai_shared.db import JobAttestationRow

ALGORITHM = "Ed25519"
NOT_CONFIGURED = "Attestation is not configured"
_KEY_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_SIGNATURE_BYTES = 64


class AttestationKeyError(ValueError):
    """The configured private key or key id cannot be used."""


def may_issue_attestation(*, auth_mode: str, quota_mode: str, plan: str) -> bool:
    """Pro and Team can issue. A private dev workstation with unlimited quota can too.

    ``AUTH_MODE=clerk`` stays on the plan check even when quotas are unlimited.
    ``past_due`` is already folded into ``plan`` by ``effective_plan``.
    """

    if plan in {"pro", "team"}:
        return True
    return auth_mode == "dev" and quota_mode == "unlimited"


def normalize_pem(raw: str) -> str:
    """Accept a PEM block, a quoted PEM, or a one-line PEM with ``\\n`` escapes."""

    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()
    text = text.replace("\\n", "\n").strip()
    if not text:
        return ""
    if "PRIVATE KEY" not in text:
        raise AttestationKeyError(
            "ATTESTATION_PRIVATE_KEY must be an unencrypted Ed25519 PKCS8 PEM"
        )
    if not text.endswith("\n"):
        text += "\n"
    return text


def validate_key_id(key_id: str) -> str:
    cleaned = key_id.strip() or "v1"
    if _KEY_ID.fullmatch(cleaned) is None:
        raise AttestationKeyError(
            "ATTESTATION_KEY_ID must be 1 to 64 characters of letters, digits, '.', '_' or '-'"
        )
    return cleaned


class AttestationKey:
    """One unencrypted Ed25519 key. ``repr`` does not include key material."""

    def __init__(self, private_key: Ed25519PrivateKey, key_id: str, public_pem: str) -> None:
        self._private = private_key
        self.key_id = key_id
        self.public_pem = public_pem
        self.algorithm = ALGORITHM

    def __repr__(self) -> str:
        return f"AttestationKey(key_id={self.key_id!r}, algorithm={ALGORITHM!r})"

    def sign(self, payload: str) -> str:
        raw = self._private.sign(payload.encode("utf-8"))
        return base64.b64encode(raw).decode("ascii")

    def verify(self, payload: str, signature: str, key_id: str | None = None) -> bool:
        """True when ``signature`` is standard base64 over the exact payload bytes.

        A ``key_id`` that does not match this key is false. Omitted ``key_id``
        checks the current key only.
        """

        if key_id is not None and key_id != self.key_id:
            return False
        try:
            raw = base64.b64decode(signature, validate=True)
        except Exception:
            return False
        if len(raw) != _SIGNATURE_BYTES:
            return False
        try:
            self._public.verify(raw, payload.encode("utf-8"))
        except InvalidSignature:
            return False
        return True

    @property
    def _public(self) -> Ed25519PublicKey:
        return self._private.public_key()


def load_attestation_key(pem: str, key_id: str) -> AttestationKey:
    """Load an unencrypted PKCS8 Ed25519 private key. Rejects other key types."""

    text = normalize_pem(pem)
    if not text:
        raise AttestationKeyError(
            "ATTESTATION_PRIVATE_KEY must be an unencrypted Ed25519 PKCS8 PEM"
        )
    cleaned_id = validate_key_id(key_id)
    try:
        loaded = serialization.load_pem_private_key(text.encode("utf-8"), password=None)
    except Exception as exc:
        raise AttestationKeyError(
            "ATTESTATION_PRIVATE_KEY must be an unencrypted Ed25519 PKCS8 PEM"
        ) from exc
    if not isinstance(loaded, Ed25519PrivateKey):
        raise AttestationKeyError(
            "ATTESTATION_PRIVATE_KEY must be an unencrypted Ed25519 PKCS8 PEM"
        )
    public_pem = loaded.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    return AttestationKey(loaded, cleaned_id, public_pem)


def format_number(value: float) -> str:
    """Up to 6 decimal places, trailing zeros removed. Non-finite input is rejected."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("attestation number must be int or float")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite number")
    text = f"{round(number, 6):.6f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def canonical_json(value: object) -> str:
    """Compact JSON with sorted object keys and stable numbers."""

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return format_number(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, Mapping):
        parts: list[str] = []
        for key in sorted(value, key=str):
            if not isinstance(key, str):
                raise TypeError("object keys must be strings")
            parts.append(f"{canonical_json(key)}:{canonical_json(value[key])}")
        return "{" + ",".join(parts) + "}"
    raise TypeError(f"cannot encode {type(value).__name__}")


def iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat()


def attestation_payload(
    *,
    job_id: str,
    org_id: str | None,
    prediction: str | None,
    confidence: float | None,
    model: str | None,
    signals: Mapping[str, float],
    updated_at: datetime,
    limitations: str,
) -> str:
    """Canonical report bytes. Every field is present. ``org_id`` may be null."""

    body: dict[str, object] = {
        "confidence": None if confidence is None else float(confidence),
        "job_id": job_id,
        "limitations": limitations,
        "model": model,
        "org_id": org_id,
        "prediction": prediction,
        "signals": {name: float(number) for name, number in signals.items()},
        "status": "completed",
        "updated_at": iso_utc(updated_at),
    }
    return canonical_json(body)


def payload_digest(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AttestationRecord:
    job_id: str
    key_id: str
    algorithm: str
    payload: str
    signature: str
    created_at: datetime


def _same(current: AttestationRecord, new: AttestationRecord) -> bool:
    return (
        current.payload == new.payload
        and current.key_id == new.key_id
        and current.signature == new.signature
        and current.algorithm == new.algorithm
    )


class AttestationStore(Protocol):
    def get(self, job_id: str) -> AttestationRecord | None: ...

    def save(self, record: AttestationRecord) -> AttestationRecord: ...


class MemoryAttestationStore:
    def __init__(self) -> None:
        self._rows: dict[str, AttestationRecord] = {}
        self._lock = threading.Lock()

    def get(self, job_id: str) -> AttestationRecord | None:
        with self._lock:
            return self._rows.get(job_id)

    def save(self, record: AttestationRecord) -> AttestationRecord:
        with self._lock:
            current = self._rows.get(record.job_id)
            if current is not None and _same(current, record):
                return current
            self._rows[record.job_id] = record
            return record


class PostgresAttestationStore:
    def __init__(self, database_url: str | None = None, engine: object | None = None) -> None:
        if engine is None:
            if not database_url:
                raise RuntimeError("PostgresAttestationStore requires a database url or an engine")
            from sqlalchemy import create_engine

            engine = create_engine(database_url, pool_pre_ping=True)
        self.engine = engine
        self._session_factory = sessionmaker(engine, expire_on_commit=False)  # type: ignore[arg-type]

    def get(self, job_id: str) -> AttestationRecord | None:
        with self._session() as session:
            row = session.get(JobAttestationRow, job_id)
            return None if row is None else _record(row)

    def save(self, record: AttestationRecord) -> AttestationRecord:
        digest = payload_digest(record.payload)
        with self._session() as session:
            row = session.get(JobAttestationRow, record.job_id)
            if row is None:
                session.add(
                    JobAttestationRow(
                        job_id=record.job_id,
                        key_id=record.key_id,
                        algorithm=record.algorithm,
                        payload=record.payload,
                        payload_sha256=digest,
                        signature=record.signature,
                        created_at=record.created_at,
                    )
                )
                return record
            current = _record(row)
            if _same(current, record):
                return current
            row.key_id = record.key_id
            row.algorithm = record.algorithm
            row.payload = record.payload
            row.payload_sha256 = digest
            row.signature = record.signature
            row.created_at = record.created_at
            return record

    @contextmanager
    def _session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def _record(row: JobAttestationRow) -> AttestationRecord:
    return AttestationRecord(
        job_id=row.job_id,
        key_id=row.key_id,
        algorithm=row.algorithm,
        payload=row.payload,
        signature=row.signature,
        created_at=row.created_at,
    )
