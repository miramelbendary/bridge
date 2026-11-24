"""Test fixtures.

The schema is built by running the real Alembic migrations (never `create_all`), so every test run
also exercises the migrations. Set TEST_DATABASE_URL to run against PostgreSQL (as CI does);
otherwise a temporary SQLite file is used.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, update

from app.core.config import Settings
from app.main import create_app
from app.models import Base, Scenario, Specialization, User
from app.models.user import Role
from app.services.scenarios import sync_from_files
from app.services.users import register_local_user

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_SECRET = "test-secret-for-bridge-unit-tests-0123456789"
PASSWORD = "correct-horse-battery"


def alembic_config(database_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["database_url"] = database_url
    cfg.attributes["configure_logger"] = False
    return cfg


@pytest.fixture(scope="session")
def database_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        url = f"sqlite:///{tmp_path_factory.mktemp('db') / 'bridge_test.db'}"
    cfg = alembic_config(url)
    command.downgrade(cfg, "base")  # clean slate on a reused PostgreSQL database
    command.upgrade(cfg, "head")
    yield url


@pytest.fixture
def make_settings(database_url: str) -> Callable[..., Settings]:
    def _make(**overrides) -> Settings:
        values = {
            "environment": "test",
            "database_url": database_url,
            "auth_provider": "local",
            "local_jwt_secret": TEST_SECRET,
            "cors_origins": ["http://localhost:3000"],
            "auth_rate_limit_attempts": 1000,
        }
        values.update(overrides)
        return Settings(_env_file=None, **values)

    return _make


@pytest.fixture
def settings(make_settings) -> Settings:
    return make_settings()


SEEDED_SPECIALIZATIONS = ("translation", "international_trade", "infocom")


@pytest.fixture(autouse=True)
def _clean_tables(database_url: str) -> Iterator[None]:
    yield
    engine = create_engine(database_url)
    with engine.begin() as conn:
        # Break the scenarios <-> scenario_versions cycle, then delete children before parents.
        conn.execute(update(Scenario).values(current_version_id=None))
        for table in reversed(Base.metadata.sorted_tables):
            if table.name == "specializations":
                conn.execute(
                    delete(Specialization).where(Specialization.code.not_in(SEEDED_SPECIALIZATIONS))
                )
            else:
                conn.execute(table.delete())
    engine.dispose()


@pytest.fixture
def synced(app) -> None:
    """Load the real scenario files into the test database."""
    with app.state.db.session_factory() as session:
        sync_from_files(session)
        session.commit()


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def register(client) -> Callable[..., dict]:
    def _register(email: str = "student@example.com", password: str = PASSWORD, name="Student"):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "display_name": name},
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _register


@pytest.fixture
def create_user(app) -> Callable[..., User]:
    """Create a user directly in the database with any role (as the admin CLI would)."""

    def _create(email: str, role: Role = Role.STUDENT, password: str = PASSWORD) -> User:
        with app.state.db.session_factory() as session:
            user = register_local_user(session, email=email, password=password, display_name="X")
            user.role = role.value
            session.commit()
            return user

    return _create


@pytest.fixture
def login(client) -> Callable[..., str]:
    def _login(email: str, password: str = PASSWORD) -> str:
        resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    return _login


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
