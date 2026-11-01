"""Pro and Team API keys.

The plaintext secret is returned once by the API and is not stored. Lookup
hashes the presented bearer token and compares that digest to the stored
SHA-256 with ``hmac.compare_digest``. A revoked row stays in the table so
the same secret stops working immediately.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from secureai_shared.attestation import may_issue_attestation
from secureai_shared.db import ApiKeyRow

PREFIX = "sai_"
PREFIX_LEN = 12
MAX_ACTIVE_KEYS = 25
_TOKEN = re.compile(r"sai_[A-Za-z0-9_-]{32,128}")
_DUMMY_HASH = hashlib.sha256(b"secureai-unused-api-key").hexdigest()


class ApiKeyNameError(ValueError):
    """The label cannot be stored."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ApiKeyLimit(Exception):
    """This personal account or workspace already has the maximum number of live keys."""

    detail = "API key limit reached. Revoke an existing key first."


@dataclass(frozen=True)
class ApiKeyRecord:
    """Public key metadata. This object never carries the secret or its hash."""

    id: str
    user_id: str
    org_id: str | None
    name: str
    prefix: str
    created_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None


@dataclass(frozen=True)
class _StoredKey:
    id: str
    user_id: str
    org_id: str | None
    name: str
    prefix: str
    secret_hash: str
    created_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None

    def public(self) -> ApiKeyRecord:
        return ApiKeyRecord(
            id=self.id,
            user_id=self.user_id,
            org_id=self.org_id,
            name=self.name,
            prefix=self.prefix,
            created_at=self.created_at,
            revoked_at=self.revoked_at,
            last_used_at=self.last_used_at,
        )


class ApiKeyStore(Protocol):
    def create(self, *, user_id: str, org_id: str | None, name: str) -> tuple[ApiKeyRecord, str]: ...

    def list_keys(self, *, user_id: str, org_id: str | None) -> list[ApiKeyRecord]: ...

    def revoke(self, key_id: str, *, user_id: str, org_id: str | None) -> bool: ...

    def authenticate(self, token: str) -> ApiKeyRecord | None: ...

    def mark_used(self, key_id: str, *, now: datetime | None = None) -> None: ...


def may_use_api_key(plan: str) -> bool:
    """Pro and Team can mint and present keys.

    ``plan`` is an ``effective_plan`` result. This is the paid half of
    ``may_issue_attestation``. A dev workstation with unlimited quota can
    export a PDF on the free plan, and still cannot create or use an API key.
    """

    return may_issue_attestation(auth_mode="clerk", quota_mode="enforce", plan=plan)


def clean_key_name(name: str) -> str:
    if any(ord(char) < 32 or ord(char) == 127 for char in name):
        raise ApiKeyNameError("API key name must be 1 to 80 characters.")
    cleaned = name.strip()
    if not cleaned or len(cleaned) > 80:
        raise ApiKeyNameError("API key name must be 1 to 80 characters.")
    return cleaned


def secret_hash(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def hashes_equal(stored_hash: str, computed_hash: str) -> bool:
    """Constant-time compare of two SHA-256 hex digests."""

    if len(stored_hash) != len(computed_hash):
        return False
    return hmac.compare_digest(stored_hash, computed_hash)


def new_secret() -> str:
    return PREFIX + secrets.token_urlsafe(32)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _in_scope(row: _StoredKey | ApiKeyRow, *, user_id: str, org_id: str | None) -> bool:
    if org_id is not None:
        return row.org_id == org_id
    return row.org_id is None and row.user_id == user_id


def _from_row(row: ApiKeyRow) -> ApiKeyRecord:
    return ApiKeyRecord(
        id=row.id,
        user_id=row.user_id,
        org_id=row.org_id,
        name=row.name,
        prefix=row.prefix,
        created_at=row.created_at,
        revoked_at=row.revoked_at,
        last_used_at=row.last_used_at,
    )


class MemoryApiKeyStore:
    def __init__(self, *, max_active: int = MAX_ACTIVE_KEYS) -> None:
        self._max_active = max_active
        self._by_id: dict[str, _StoredKey] = {}
        self._by_hash: dict[str, str] = {}
        self._lock = threading.Lock()

    def create(self, *, user_id: str, org_id: str | None, name: str) -> tuple[ApiKeyRecord, str]:
        label = clean_key_name(name)
        secret = new_secret()
        digest = secret_hash(secret)
        now = _now()
        with self._lock:
            if self._active_count(user_id=user_id, org_id=org_id) >= self._max_active:
                raise ApiKeyLimit()
            key_id = self._new_id()
            stored = _StoredKey(
                id=key_id,
                user_id=user_id,
                org_id=org_id,
                name=label,
                prefix=secret[:PREFIX_LEN],
                secret_hash=digest,
                created_at=now,
                revoked_at=None,
                last_used_at=None,
            )
            self._by_id[key_id] = stored
            self._by_hash[digest] = key_id
        return stored.public(), secret

    def list_keys(self, *, user_id: str, org_id: str | None) -> list[ApiKeyRecord]:
        with self._lock:
            rows = [
                row.public()
                for row in self._by_id.values()
                if _in_scope(row, user_id=user_id, org_id=org_id)
            ]
        rows.sort(key=lambda row: row.created_at, reverse=True)
        return rows

    def revoke(self, key_id: str, *, user_id: str, org_id: str | None) -> bool:
        with self._lock:
            row = self._by_id.get(key_id)
            if row is None or not _in_scope(row, user_id=user_id, org_id=org_id):
                return False
            if row.revoked_at is None:
                self._by_id[key_id] = replace(row, revoked_at=_now())
            return True

    def authenticate(self, token: str) -> ApiKeyRecord | None:
        row = self._match(token)
        if row is None or row.revoked_at is not None:
            return None
        return row.public()

    def mark_used(self, key_id: str, *, now: datetime | None = None) -> None:
        stamp = now or _now()
        with self._lock:
            row = self._by_id.get(key_id)
            if row is None or row.revoked_at is not None:
                return
            self._by_id[key_id] = replace(row, last_used_at=stamp)

    def _match(self, token: str) -> _StoredKey | None:
        if not isinstance(token, str) or len(token) > 180 or _TOKEN.fullmatch(token) is None:
            hashes_equal(_DUMMY_HASH, secret_hash("invalid-api-key"))
            return None
        digest = secret_hash(token)
        with self._lock:
            key_id = self._by_hash.get(digest)
            row = None if key_id is None else self._by_id.get(key_id)
            stored = row.secret_hash if row is not None else _DUMMY_HASH
        if not hashes_equal(stored, digest):
            return None
        return row

    def _active_count(self, *, user_id: str, org_id: str | None) -> int:
        return sum(
            1
            for row in self._by_id.values()
            if row.revoked_at is None and _in_scope(row, user_id=user_id, org_id=org_id)
        )

    def _new_id(self) -> str:
        for _attempt in range(5):
            key_id = "key_" + uuid4().hex[:12]
            if key_id not in self._by_id:
                return key_id
        raise RuntimeError("could not allocate an API key id")


class PostgresApiKeyStore:
    def __init__(
        self,
        database_url: str | None = None,
        engine: object | None = None,
        *,
        max_active: int = MAX_ACTIVE_KEYS,
    ) -> None:
        if engine is None:
            if not database_url:
                raise RuntimeError("PostgresApiKeyStore requires a database url or an engine")
            from sqlalchemy import create_engine

            engine = create_engine(database_url, pool_pre_ping=True)
        self.engine = engine
        self._max_active = max_active
        self._session_factory = sessionmaker(engine, expire_on_commit=False)  # type: ignore[arg-type]
        # SQLite tests have no advisory lock. One process still cannot race
        # itself. Postgres workers rely on the transaction lock below.
        self._guards: dict[str, threading.Lock] = {}
        self._guards_lock = threading.Lock()

    def create(self, *, user_id: str, org_id: str | None, name: str) -> tuple[ApiKeyRecord, str]:
        label = clean_key_name(name)
        secret = new_secret()
        digest = secret_hash(secret)
        now = _now()
        scope = _scope_key(user_id, org_id)
        if self.engine.dialect.name == "postgresql":
            return self._insert(user_id, org_id, label, secret, digest, now, scope, lock_db=True)
        with self._thread_guard(scope):
            return self._insert(user_id, org_id, label, secret, digest, now, scope, lock_db=False)

    def _insert(
        self,
        user_id: str,
        org_id: str | None,
        label: str,
        secret: str,
        digest: str,
        now: datetime,
        scope: str,
        *,
        lock_db: bool,
    ) -> tuple[ApiKeyRecord, str]:
        with self._session() as session:
            if lock_db:
                # Count-then-insert races when nothing is locked: two workers
                # can both see 24 live keys. There is no parent row for a
                # personal scope, so a transaction advisory lock stands in
                # for SELECT … FOR UPDATE. It releases on commit or rollback.
                session.execute(
                    text(
                        "SELECT pg_advisory_xact_lock("
                        "hashtext('secureai-api-key'), hashtext(:scope))"
                    ),
                    {"scope": scope},
                )
            if self._active_count(session, user_id=user_id, org_id=org_id) >= self._max_active:
                raise ApiKeyLimit()
            row = ApiKeyRow(
                id=self._new_id(session),
                user_id=user_id,
                org_id=org_id,
                name=label,
                prefix=secret[:PREFIX_LEN],
                secret_hash=digest,
                created_at=now,
                revoked_at=None,
                last_used_at=None,
            )
            session.add(row)
            session.flush()
            return _from_row(row), secret

    def list_keys(self, *, user_id: str, org_id: str | None) -> list[ApiKeyRecord]:
        with self._session() as session:
            query = select(ApiKeyRow).order_by(ApiKeyRow.created_at.desc())
            query = _scope_clause(query, user_id=user_id, org_id=org_id)
            return [_from_row(row) for row in session.scalars(query).all()]

    def revoke(self, key_id: str, *, user_id: str, org_id: str | None) -> bool:
        with self._session() as session:
            row = session.get(ApiKeyRow, key_id)
            if row is None or not _in_scope(row, user_id=user_id, org_id=org_id):
                return False
            if row.revoked_at is None:
                row.revoked_at = _now()
            return True

    def authenticate(self, token: str) -> ApiKeyRecord | None:
        if not isinstance(token, str) or len(token) > 180 or _TOKEN.fullmatch(token) is None:
            hashes_equal(_DUMMY_HASH, secret_hash("invalid-api-key"))
            return None
        digest = secret_hash(token)
        with self._session() as session:
            row = session.scalar(select(ApiKeyRow).where(ApiKeyRow.secret_hash == digest))
            stored = row.secret_hash if row is not None else _DUMMY_HASH
            revoked = None if row is None else row.revoked_at
            public = None if row is None else _from_row(row)
        if not hashes_equal(stored, digest):
            return None
        if public is None or revoked is not None:
            return None
        return public

    def mark_used(self, key_id: str, *, now: datetime | None = None) -> None:
        stamp = now or _now()
        with self._session() as session:
            row = session.get(ApiKeyRow, key_id)
            if row is None or row.revoked_at is not None:
                return
            row.last_used_at = stamp

    def _active_count(self, session: Session, *, user_id: str, org_id: str | None) -> int:
        query = (
            select(func.count())
            .select_from(ApiKeyRow)
            .where(ApiKeyRow.revoked_at.is_(None))
        )
        query = _scope_clause(query, user_id=user_id, org_id=org_id)
        return int(session.scalar(query) or 0)

    @contextmanager
    def _thread_guard(self, scope: str) -> Iterator[None]:
        with self._guards_lock:
            guard = self._guards.get(scope)
            if guard is None:
                guard = threading.Lock()
                self._guards[scope] = guard
        with guard:
            yield

    def _new_id(self, session: Session) -> str:
        for _attempt in range(5):
            key_id = "key_" + uuid4().hex[:12]
            if session.get(ApiKeyRow, key_id) is None:
                return key_id
        raise RuntimeError("could not allocate an API key id")

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


def _scope_key(user_id: str, org_id: str | None) -> str:
    if org_id is not None:
        return f"org:{org_id}"
    return f"user:{user_id}"


def _scope_clause(query: object, *, user_id: str, org_id: str | None) -> object:
    if org_id is not None:
        return query.where(ApiKeyRow.org_id == org_id)  # type: ignore[attr-defined]
    return query.where(ApiKeyRow.org_id.is_(None), ApiKeyRow.user_id == user_id)  # type: ignore[attr-defined]
