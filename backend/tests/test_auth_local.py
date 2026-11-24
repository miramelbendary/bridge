from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select

from app.models import AuditLog, User
from tests.conftest import PASSWORD, TEST_SECRET, auth


def test_register_returns_token_and_student_role(client, register):
    body = register("Alice@Example.com")
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "alice@example.com"  # normalized
    assert body["user"]["role"] == "student"
    me = client.get("/api/v1/users/me", headers=auth(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"
    assert "users:read_all" not in me.json()["permissions"]


def test_password_is_hashed_not_stored(app, register):
    register("hash@example.com")
    with app.state.db.session_factory() as s:
        user = s.scalar(select(User).where(User.email == "hash@example.com"))
    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("$argon2id$")


def test_register_cannot_choose_role(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "sneaky@example.com",
            "password": PASSWORD,
            "display_name": "Sneaky",
            "role": "admin",
        },
    )
    assert resp.status_code == 422  # unknown fields are rejected outright


def test_register_duplicate_email_conflict(client, register):
    register("dup@example.com")
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "DUP@example.com", "password": PASSWORD, "display_name": "Dup"},
    )
    assert resp.status_code == 409


def test_register_rejects_weak_password_and_bad_email(client):
    short = client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": "short", "display_name": "A"},
    )
    assert short.status_code == 422
    bad_email = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": PASSWORD, "display_name": "A"},
    )
    assert bad_email.status_code == 422


def test_login_success_and_failure(client, register, login):
    register("bob@example.com")
    assert login("BOB@example.com")
    wrong = client.post(
        "/api/v1/auth/login", json={"email": "bob@example.com", "password": "wrong-password!"}
    )
    unknown = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )
    # Same response for wrong password and unknown account (no account enumeration).
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_login_events_are_audited_without_secrets(app, client, register):
    register("audit@example.com")
    client.post(
        "/api/v1/auth/login", json={"email": "audit@example.com", "password": "nope-nope-1"}
    )
    with app.state.db.session_factory() as s:
        entries = list(s.scalars(select(AuditLog).order_by(AuditLog.occurred_at)))
    actions = [(e.action, e.outcome) for e in entries]
    assert ("auth.register", "success") in actions
    assert ("auth.login", "failure") in actions
    for e in entries:
        assert "password" not in str(e.details).lower()
        assert "nope-nope-1" not in str(e.details)


def test_inactive_user_cannot_login_or_use_token(app, client, register, login):
    token = register("gone@example.com")["access_token"]
    with app.state.db.session_factory() as s:
        user = s.scalar(select(User).where(User.email == "gone@example.com"))
        user.is_active = False
        s.commit()
    assert client.get("/api/v1/users/me", headers=auth(token)).status_code == 401
    resp = client.post(
        "/api/v1/auth/login", json={"email": "gone@example.com", "password": PASSWORD}
    )
    assert resp.status_code == 401


def test_missing_and_malformed_tokens_rejected(client):
    assert client.get("/api/v1/users/me").status_code == 401
    assert client.get("/api/v1/users/me", headers=auth("garbage")).status_code == 401
    assert client.get("/api/v1/users/me", headers={"Authorization": "Basic abc"}).status_code == 401


def _forge(sub: str, *, secret=TEST_SECRET, **overrides) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": sub,
        "iss": "bridge-local",
        "aud": "bridge-api",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    claims.update(overrides)
    return jwt.encode(claims, secret, algorithm="HS256")


def test_token_tampering_rejected(client, register):
    user_id = register("t@example.com")["user"]["id"]
    assert client.get("/api/v1/users/me", headers=auth(_forge(user_id))).status_code == 200
    bad_cases = [
        _forge(user_id, secret="another-secret-that-is-long-enough-000000"),
        _forge(user_id, exp=datetime.now(UTC) - timedelta(seconds=1)),
        _forge(user_id, aud="someone-else"),
        _forge(user_id, iss="evil"),
        _forge("not-a-uuid"),
        _forge("00000000-0000-0000-0000-000000000000"),
    ]
    for token in bad_cases:
        assert client.get("/api/v1/users/me", headers=auth(token)).status_code == 401


def test_alg_none_token_rejected(client, register):
    user_id = register("none@example.com")["user"]["id"]
    token = jwt.encode(
        {
            "sub": user_id,
            "iss": "bridge-local",
            "aud": "bridge-api",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        key=None,
        algorithm="none",
    )
    assert client.get("/api/v1/users/me", headers=auth(token)).status_code == 401


def test_role_claim_in_token_is_ignored(client, register):
    user_id = register("claim@example.com")["user"]["id"]
    token = _forge(user_id, role="admin")
    assert client.get("/api/v1/admin/users", headers=auth(token)).status_code == 403


def test_auth_rate_limit(make_settings):
    from fastapi.testclient import TestClient

    from app.main import create_app

    app = create_app(make_settings(auth_rate_limit_attempts=3, auth_rate_limit_window_seconds=60))
    with TestClient(app) as c:
        codes = [
            c.post(
                "/api/v1/auth/login", json={"email": "x@example.com", "password": "whatever-1"}
            ).status_code
            for _ in range(4)
        ]
    assert codes == [401, 401, 401, 429]


def test_local_endpoints_disabled_in_supabase_mode(make_settings):
    from fastapi.testclient import TestClient

    from app.main import create_app

    app = create_app(make_settings(auth_provider="supabase", supabase_jwt_secret="s" * 40))
    with TestClient(app) as c:
        assert c.get("/api/v1/auth/config").json()["provider"] == "supabase"
        resp = c.post(
            "/api/v1/auth/login", json={"email": "x@example.com", "password": "whatever-1"}
        )
        assert resp.status_code == 404
