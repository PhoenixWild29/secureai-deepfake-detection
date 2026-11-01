"""Alembic ``20261101_0009`` matches the indexes declared on ``JobRow``."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from secureai_shared.db import Base


def _admin_url() -> str:
    configured = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://secureai:secureai@127.0.0.1:5432/secureai",
    )
    return make_url(configured).set(database="postgres").render_as_string(hide_password=False)


def _database_url(name: str) -> str:
    return make_url(_admin_url()).set(database=name).render_as_string(hide_password=False)


def _require_postgres() -> None:
    try:
        engine = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
    except Exception as exc:
        if os.environ.get("REQUIRE_SERVICES") == "1":
            pytest.fail(f"postgres unavailable: {exc}")
        pytest.skip(f"postgres unavailable: {exc}")


def _recreate(name: str) -> None:
    engine = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    engine.dispose()


def _drop(name: str) -> None:
    engine = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    engine.dispose()


def _job_indexes(url: str) -> dict[str, str]:
    engine = create_engine(url)
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE schemaname = 'public' AND tablename = 'jobs'"
            )
        ).all()
    engine.dispose()
    return {name: definition for name, definition in rows}


def test_alembic_job_indexes_match_the_model() -> None:
    _require_postgres()
    migrated = "secureai_index_migration"
    modeled = "secureai_index_model"
    previous = os.environ.get("DATABASE_URL")
    try:
        _recreate(migrated)
        _recreate(modeled)
        os.environ["DATABASE_URL"] = _database_url(migrated)
        root = Path(__file__).resolve().parents[1]
        config = Config(str(root / "alembic.ini"))
        config.set_main_option("script_location", str(root / "alembic"))
        command.upgrade(config, "head")
        from_alembic = _job_indexes(_database_url(migrated))

        model_engine = create_engine(_database_url(modeled))
        Base.metadata.create_all(model_engine)
        model_engine.dispose()
        from_model = _job_indexes(_database_url(modeled))
        assert from_alembic == from_model
        assert "ix_jobs_personal_created_id" in from_alembic
        assert "ix_jobs_org_created_id" in from_alembic
        assert "ix_jobs_user_id" not in from_alembic
        assert "ix_jobs_org_id" not in from_alembic
        assert "ix_jobs_status" in from_alembic
        assert "WHERE (org_id IS NULL)" in from_alembic["ix_jobs_personal_created_id"]
        assert "WHERE (org_id IS NOT NULL)" in from_alembic["ix_jobs_org_created_id"]
        assert "created_at DESC" in from_alembic["ix_jobs_personal_created_id"]
        assert "id DESC" in from_alembic["ix_jobs_org_created_id"]

        command.downgrade(config, "20261101_0008")
        downgraded = _job_indexes(_database_url(migrated))
        assert "ix_jobs_user_id" in downgraded
        assert "ix_jobs_org_id" in downgraded
        assert "ix_jobs_personal_created_id" not in downgraded
        assert "ix_jobs_org_created_id" not in downgraded

        command.upgrade(config, "head")
        assert _job_indexes(_database_url(migrated)) == from_model
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        _drop(migrated)
        _drop(modeled)
