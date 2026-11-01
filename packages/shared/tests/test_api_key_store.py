"""API key hashing, plan gate, and both stores."""

from __future__ import annotations

from sqlalchemy import create_engine, select

from secureai_shared.api_keys import (
    MAX_ACTIVE_KEYS,
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
