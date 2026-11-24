from __future__ import annotations

from sqlalchemy import select

from app.models import AuditLog
from app.models.user import Role
from app.security.permissions import ROLE_PERMISSIONS, Permission, has_permission
from tests.conftest import auth


def test_permission_matrix_fails_closed():
    assert has_permission("student", Permission.PROFILE_READ_OWN)
    assert not has_permission("student", Permission.USERS_READ_ALL)
    assert not has_permission("professor", Permission.USERS_READ_ALL)
    assert has_permission("admin", Permission.USERS_MANAGE_ROLES)
    assert not has_permission("superuser", Permission.PROFILE_READ_OWN)
    assert set(ROLE_PERMISSIONS) == set(Role)


def test_specializations_seeded_and_listed(client, register):
    token = register()["access_token"]
    resp = client.get("/api/v1/specializations", headers=auth(token))
    assert resp.status_code == 200
    codes = {s["code"] for s in resp.json()}
    assert codes == {"translation", "international_trade", "infocom"}


def test_specializations_require_auth(client):
    assert client.get("/api/v1/specializations").status_code == 401


def test_student_selects_specialization(client, register):
    token = register()["access_token"]
    resp = client.patch(
        "/api/v1/users/me/profile",
        headers=auth(token),
        json={"specialization_code": "international_trade", "display_name": "Amira"},
    )
    assert resp.status_code == 200, resp.text
    profile = resp.json()["profile"]
    assert profile["display_name"] == "Amira"
    assert profile["specialization"]["code"] == "international_trade"
    me = client.get("/api/v1/users/me", headers=auth(token)).json()
    assert me["profile"]["specialization"]["code"] == "international_trade"


def test_unknown_specialization_rejected(client, register):
    token = register()["access_token"]
    resp = client.patch(
        "/api/v1/users/me/profile", headers=auth(token), json={"specialization_code": "physics"}
    )
    assert resp.status_code == 422


def test_profile_update_cannot_change_role(client, register):
    token = register()["access_token"]
    resp = client.patch("/api/v1/users/me/profile", headers=auth(token), json={"role": "admin"})
    assert resp.status_code == 422


def test_student_and_professor_denied_admin_routes(app, client, create_user, login):
    create_user("s@example.com", Role.STUDENT)
    create_user("p@example.com", Role.PROFESSOR)
    for email in ("s@example.com", "p@example.com"):
        token = login(email)
        assert client.get("/api/v1/admin/users", headers=auth(token)).status_code == 403
        assert client.get("/api/v1/admin/audit-logs", headers=auth(token)).status_code == 403
    with app.state.db.session_factory() as s:
        denied = list(s.scalars(select(AuditLog).where(AuditLog.outcome == "denied")))
    assert len(denied) == 4


def test_admin_lists_users_and_changes_role(client, create_user, login):
    create_user("admin@example.com", Role.ADMIN)
    target = create_user("prof@example.com", Role.STUDENT)
    token = login("admin@example.com")

    users = client.get("/api/v1/admin/users", headers=auth(token))
    assert users.status_code == 200
    assert {u["email"] for u in users.json()} >= {"admin@example.com", "prof@example.com"}

    resp = client.patch(
        f"/api/v1/admin/users/{target.id}/role", headers=auth(token), json={"role": "professor"}
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "professor"

    # The new role takes effect immediately (role is read from the DB, not from tokens).
    prof_token = login("prof@example.com")
    me = client.get("/api/v1/users/me", headers=auth(prof_token)).json()
    assert me["role"] == "professor"

    logs = client.get(
        "/api/v1/admin/audit-logs",
        headers=auth(token),
        params={"action": "admin.user.role_changed"},
    ).json()
    assert logs[0]["details"] == {"from": "student", "to": "professor"}


def test_admin_cannot_demote_self_or_last_admin(client, create_user, login):
    admin = create_user("solo@example.com", Role.ADMIN)
    token = login("solo@example.com")
    resp = client.patch(
        f"/api/v1/admin/users/{admin.id}/role", headers=auth(token), json={"role": "student"}
    )
    assert resp.status_code == 409


def test_role_change_unknown_user_and_invalid_role(client, create_user, login):
    create_user("a2@example.com", Role.ADMIN)
    token = login("a2@example.com")
    missing = client.patch(
        "/api/v1/admin/users/00000000-0000-0000-0000-000000000000/role",
        headers=auth(token),
        json={"role": "professor"},
    )
    assert missing.status_code == 404
    other = create_user("o@example.com")
    invalid = client.patch(
        f"/api/v1/admin/users/{other.id}/role", headers=auth(token), json={"role": "superuser"}
    )
    assert invalid.status_code == 422
