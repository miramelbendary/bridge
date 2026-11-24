"""Migrations must match the ORM models exactly and must be reversible."""

from __future__ import annotations

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.models import Base
from tests.conftest import alembic_config


def test_models_and_migrations_in_sync(database_url):
    engine = create_engine(database_url)
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": True})
        diff = compare_metadata(ctx, Base.metadata)
    engine.dispose()
    assert diff == [], f"Models and migrations differ; create a migration: {diff}"


def test_downgrade_and_upgrade_roundtrip(tmp_path):
    url = f"sqlite:///{tmp_path / 'roundtrip.db'}"
    cfg = alembic_config(url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    engine = create_engine(url)
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    engine.dispose()
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    assert {"users", "user_profiles", "specializations", "audit_logs"} <= set(
        inspect(engine).get_table_names()
    )
    engine.dispose()
