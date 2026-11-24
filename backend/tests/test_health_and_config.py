from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import INSECURE_DEV_SECRET, Settings
from app.main import create_app


def test_liveness(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_readiness_reports_database_up(client):
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": "up"}


def test_readiness_reports_database_down(make_settings, tmp_path):
    from fastapi.testclient import TestClient

    # A directory path cannot be opened as a SQLite database file -> connection fails.
    bad = make_settings(database_url=f"sqlite:///{tmp_path}")
    with TestClient(create_app(bad)) as c:
        resp = c.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["database"] == "down"


def test_security_headers_present(client):
    resp = client.get("/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in resp.headers["Content-Security-Policy"]
    assert resp.headers["Cache-Control"] == "no-store"


def test_cors_allows_only_configured_origin(client):
    ok = client.options(
        "/api/v1/auth/login",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = client.options(
        "/api/v1/auth/login",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in bad.headers


def test_short_local_secret_rejected(database_url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url=database_url, local_jwt_secret="short")


def test_default_secret_rejected_in_production():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            database_url="postgresql+psycopg://u:p@db/bridge",
            local_jwt_secret=INSECURE_DEV_SECRET,
        )


def test_sqlite_rejected_in_production():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            database_url="sqlite:///x.db",
            local_jwt_secret="p" * 40,
        )


def test_wildcard_cors_rejected(database_url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url=database_url, cors_origins=["*"])


def test_cors_origins_accepts_comma_separated_string(database_url):
    s = Settings(
        _env_file=None, database_url=database_url, cors_origins="http://a.test, http://b.test"
    )
    assert s.cors_origins == ["http://a.test", "http://b.test"]


def test_docs_disabled_in_production():
    from fastapi.testclient import TestClient

    prod = Settings(
        _env_file=None,
        environment="production",
        database_url="postgresql+psycopg://u:p@localhost:1/none",
        local_jwt_secret="p" * 40,
    )
    with TestClient(create_app(prod)) as c:
        assert c.get("/docs").status_code == 404
        assert c.get("/openapi.json").status_code == 404
        assert "Strict-Transport-Security" in c.get("/health").headers
