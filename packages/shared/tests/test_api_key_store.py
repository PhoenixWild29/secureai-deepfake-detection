"""API key hashing, plan gate, and both stores."""

from __future__ import annotations

import os
import threading
import time

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.pool import QueuePool

from secureai_shared.api_keys import (
    MAX_ACTIVE_KEYS,
    ApiKeyLimit,
    MemoryApiKeyStore,
    PostgresApiKeyStore,
    hashes_equal,
    may_use_api_key,
    secret_hash,
)
from secureai_shared.attestation import may_issue_attestation
from secureai_shared.db import ApiKeyRow, Base


def test_paid_plans_match_attestation_without_the_dev_bypass() -> None:
    for plan in ("free", "pro", "team", "enterprise"):
        assert may_use_api_key(plan) is may_issue_attestation(
            auth_mode="clerk", quota_mode="enforce", plan=plan
        )
    assert may_issue_attestation(auth_mode="dev", quota_mode="unlimited", plan="free") is True
    assert may_use_api_key("free") is False
    assert may_use_api_key("pro") is True
    assert may_use_api_key("team") is True


def test_hash_compare_rejects_a_one_character_change() -> None:
    secret = "sai_" + "a" * 40
    digest = secret_hash(secret)
    assert hashes_equal(digest, secret_hash(secret))
    assert hashes_equal(digest, secret_hash(secret[:-1] + "b")) is False
    assert hashes_equal("ab", "abcd") is False
    assert secret not in digest
    assert "sai_" not in digest


def test_memory_store_keeps_only_the_hash_and_revoke_is_immediate() -> None:
    store = MemoryApiKeyStore(max_active=2)
    first, secret = store.create(user_id="user_dev", org_id=None, name=" laptop ")
    assert first.name == "laptop"
    assert secret.startswith("sai_")
    assert first.prefix == secret[:12]
    assert secret not in repr(store._by_id)
    assert secret not in repr(store._by_hash)
    assert store.authenticate(secret) is not None
    assert store.authenticate(secret + "x") is None
    assert store.revoke(first.id, user_id="user_dev", org_id=None) is True
    assert store.authenticate(secret) is None
    assert store.revoke(first.id, user_id="user_other", org_id=None) is False

    _second, _secret = store.create(user_id="user_dev", org_id=None, name="two")
    _third, _other = store.create(user_id="user_dev", org_id=None, name="three")
    try:
        store.create(user_id="user_dev", org_id=None, name="four")
    except Exception as exc:
        assert "limit" in str(exc.detail).lower()
    else:
        raise AssertionError("expected the active key cap")
    assert MAX_ACTIVE_KEYS == 25


def _race_one_scope(store: PostgresApiKeyStore) -> None:
    """Two overlapping creates for one scope must not both pass the cap."""

    state = {"overlap": 0, "max": 0}
    gate = threading.Lock()
    original = store._active_count

    def slow(session: object, *, user_id: str, org_id: str | None) -> int:
        with gate:
            state["overlap"] += 1
            state["max"] = max(state["max"], state["overlap"])
        try:
            time.sleep(0.2)
            return original(session, user_id=user_id, org_id=org_id)  # type: ignore[arg-type]
        finally:
            with gate:
                state["overlap"] -= 1

    store._active_count = slow  # type: ignore[method-assign]
    ok: list[str] = []
    limited: list[str] = []
    errors: list[BaseException] = []

    def once(name: str) -> None:
        try:
            record, _secret = store.create(user_id="user_cap", org_id=None, name=name)
            ok.append(record.id)
        except ApiKeyLimit:
            limited.append(name)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=once, args=(name,)) for name in ("one", "two")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    assert state["max"] == 1
    assert len(ok) == 1
    assert len(limited) == 1
    live = [
        row
        for row in store.list_keys(user_id="user_cap", org_id=None)
        if row.revoked_at is None
    ]
    assert len(live) == 1


def _race_two_scopes(store: PostgresApiKeyStore) -> None:
    """Different personal scopes must not share the cap lock."""

    started = threading.Barrier(2)
    original = store._active_count

    def slow(session: object, *, user_id: str, org_id: str | None) -> int:
        started.wait(timeout=2)
        return original(session, user_id=user_id, org_id=org_id)  # type: ignore[arg-type]

    store._active_count = slow  # type: ignore[method-assign]
    errors: list[BaseException] = []

    def once(user_id: str) -> None:
        try:
            store.create(user_id=user_id, org_id=None, name="one")
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=once, args=(user_id,)) for user_id in ("user_a", "user_b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []


def test_sqlite_store_serializes_the_live_key_cap() -> None:
    """In-process creates share one scope lock when the database cannot.

    SQLite shared-cache rejects a second writer instead of waiting, so the
    two-scope case runs against Postgres below.
    """

    engine = create_engine(
        "sqlite:///file:apikeycap?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
        poolclass=QueuePool,
        pool_size=4,
        max_overflow=4,
    )
    Base.metadata.create_all(engine)
    _race_one_scope(PostgresApiKeyStore(engine=engine, max_active=1))


def test_postgres_store_round_trip_on_sqlite() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    store = PostgresApiKeyStore(engine=engine)
    record, secret = store.create(user_id="user_dev", org_id=None, name="ci")
    with engine.connect() as connection:
        row = connection.execute(select(ApiKeyRow.secret_hash, ApiKeyRow.prefix, ApiKeyRow.name)).one()
    assert row.prefix == secret[:12]
    assert row.secret_hash == secret_hash(secret)
    assert secret not in row.secret_hash
    assert store.authenticate(secret).id == record.id  # type: ignore[union-attr]
    listed = store.list_keys(user_id="user_dev", org_id=None)
    assert [item.id for item in listed] == [record.id]
    assert store.revoke(record.id, user_id="user_dev", org_id=None) is True
    assert store.authenticate(secret) is None
    again = store.list_keys(user_id="user_dev", org_id=None)
    assert again[0].revoked_at is not None


def test_postgres_live_key_cap_does_not_race() -> None:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://secureai:secureai@127.0.0.1:5432/secureai",
    )
    schema = "secureai_api_key_cap"
    try:
        probe = create_engine(url, pool_pre_ping=True)
        with probe.connect() as connection:
            connection.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            connection.commit()
        probe.dispose()
    except Exception as exc:
        if os.environ.get("REQUIRE_SERVICES") == "1":
            pytest.fail(f"postgres unavailable: {exc}")
        pytest.skip(f"postgres unavailable: {exc}")

    schema_url = url + ("&" if "?" in url else "?") + f"options=-csearch_path%3D{schema}"
    engine = create_engine(schema_url, pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    try:
        _race_one_scope(PostgresApiKeyStore(engine=engine, max_active=1))
        _race_two_scopes(PostgresApiKeyStore(engine=engine, max_active=1))
    finally:
        engine.dispose()
