"""Platform API: authorization boundaries, idempotency, concurrency, courses, authoring,
resources, recommendations and administrator controls."""

from __future__ import annotations

import copy
import uuid

import pytest
from sqlalchemy import select

from app.models import AuditLog, SimulationSession
from app.models.user import Role
from app.services import sessions as session_service
from app.services.scenarios import get_by_slug
from tests.conftest import auth

JUST = "Under CIF the seller missed the shipment date through its own error; Clause 7 applies."


@pytest.fixture
def people(client, synced, create_user, login):
    create_user("s1@example.com", Role.STUDENT)
    create_user("s2@example.com", Role.STUDENT)
    create_user("prof@example.com", Role.PROFESSOR)
    create_user("other.prof@example.com", Role.PROFESSOR)
    create_user("admin@example.com", Role.ADMIN)
    return {k: login(f"{k}@example.com") for k in ("s1", "s2", "prof", "admin")} | {
        "other": login("other.prof@example.com")
    }


def start(client, token, **body):
    payload = {
        "scenario_slug": "delayed-shipment",
        "mode": "training",
        "difficulty": "beginner",
    } | body
    r = client.post("/api/v1/sessions", headers=auth(token), json=payload)
    assert r.status_code == 201, r.text
    return r.json()["session_id"]


def act(client, token, sid, action, justification="", key=None):
    headers = auth(token) | ({"Idempotency-Key": key} if key else {})
    return client.post(
        f"/api/v1/sessions/{sid}/actions",
        headers=headers,
        json={"action_id": action, "justification": justification},
    )


def make_course(client, prof_token, *emails):
    cid = client.post(
        "/api/v1/teach/courses", headers=auth(prof_token), json={"name": "Trade 101"}
    ).json()["id"]
    for e in emails:
        assert (
            client.post(
                f"/api/v1/teach/courses/{cid}/members", headers=auth(prof_token), json={"email": e}
            ).status_code
            == 201
        )
    return cid


# ------------------------------------------------------------------ scenarios
def test_students_see_published_scenarios_from_all_specializations(client, people):
    items = client.get("/api/v1/scenarios", headers=auth(people["s1"])).json()
    assert {i["specialization"]["code"] for i in items} == {
        "international_trade",
        "translation",
        "infocom",
    }
    assert len(items) == 6
    detail = client.get("/api/v1/scenarios/media-crisis", headers=auth(people["s1"])).json()
    assert detail["learning_objectives"] and "Simulated" not in detail["title"]


def test_unknown_or_unpublished_scenario_is_404(client, people):
    assert client.get("/api/v1/scenarios/nope", headers=auth(people["s1"])).status_code == 404
    client.post(
        "/api/v1/admin/scenarios/media-crisis/status",
        headers=auth(people["admin"]),
        json={"status": "draft"},
    )
    assert (
        client.get("/api/v1/scenarios/media-crisis", headers=auth(people["s1"])).status_code == 404
    )
    r = client.post(
        "/api/v1/sessions", headers=auth(people["s1"]), json={"scenario_slug": "media-crisis"}
    )
    assert r.status_code == 404


# ------------------------------------------------------------------ ownership
def test_students_cannot_see_or_act_on_other_students_sessions(client, people):
    sid = start(client, people["s1"])
    for path in ("", "/timeline", "/assessment"):
        assert (
            client.get(f"/api/v1/sessions/{sid}{path}", headers=auth(people["s2"])).status_code
            == 404
        )
    assert act(client, people["s2"], sid, "review_shipment_documents").status_code == 404
    mine = client.get("/api/v1/sessions", headers=auth(people["s2"])).json()
    assert mine == []


def test_professor_sees_only_course_members_and_cannot_act(client, people):
    sid = start(client, people["s1"])
    assert client.get(f"/api/v1/sessions/{sid}", headers=auth(people["prof"])).status_code == 404
    make_course(client, people["prof"], "s1@example.com")
    view = client.get(f"/api/v1/sessions/{sid}", headers=auth(people["prof"]))
    assert view.status_code == 200 and view.json()["read_only"] is True
    assert act(client, people["prof"], sid, "review_shipment_documents").status_code == 404
    assert client.get(f"/api/v1/sessions/{sid}", headers=auth(people["other"])).status_code == 404


def test_professor_cannot_manage_another_professors_course(client, people):
    cid = make_course(client, people["prof"])
    assert (
        client.get(f"/api/v1/teach/courses/{cid}", headers=auth(people["other"])).status_code == 404
    )
    r = client.post(
        f"/api/v1/teach/courses/{cid}/members",
        headers=auth(people["other"]),
        json={"email": "s2@example.com"},
    )
    assert r.status_code == 404


def test_students_denied_teaching_and_admin_endpoints(client, people):
    for method, path in [
        ("get", "/api/v1/teach/courses"),
        ("get", "/api/v1/teach/review-queue"),
        ("get", "/api/v1/teach/resources"),
        ("get", "/api/v1/admin/settings"),
        ("get", "/api/v1/admin/usage"),
    ]:
        assert getattr(client, method)(path, headers=auth(people["s1"])).status_code == 403
    assert client.get("/api/v1/admin/usage", headers=auth(people["prof"])).status_code == 403


# ------------------------------------------------------------------ simulation robustness
def test_idempotency_key_prevents_double_application(client, people):
    sid = start(client, people["s1"])
    first = act(client, people["s1"], sid, "request_transport_quotes", key="abc")
    assert first.json()["result"]["replayed"] is False
    act(client, people["s1"], sid, "choose_partial_air", JUST, key="def")
    replay = act(client, people["s1"], sid, "choose_partial_air", JUST, key="def")
    assert replay.status_code == 200 and replay.json()["result"]["replayed"] is True
    budget = next(v for v in replay.json()["view"]["variables"] if v["id"] == "budget")
    assert budget["value"] == 6000 - 4200  # applied exactly once


def test_stale_state_write_is_rejected(app, client, people):
    sid = start(client, people["s1"])
    with app.state.db.session_factory() as a, app.state.db.session_factory() as b:
        sa = a.get(SimulationSession, uuid.UUID(sid))
        sb = b.get(SimulationSession, uuid.UUID(sid))
        session_service.perform_action(a, sa, "review_shipment_documents", "", None)
        a.commit()
        with pytest.raises(session_service.ConflictError):
            session_service.perform_action(b, sb, "request_transport_quotes", "", None)


def test_session_recovery_after_reload(client, people):
    sid = start(client, people["s1"])
    act(client, people["s1"], sid, "review_shipment_documents")
    reloaded = client.get(f"/api/v1/sessions/{sid}", headers=auth(people["s1"])).json()
    assert any(t["id"] == "review_documents" and t["status"] == "done" for t in reloaded["tasks"])
    assert reloaded["clock"] == 20


def test_engine_errors_are_reported_with_codes(client, people):
    sid = start(client, people["s1"], mode="assessment")
    r = client.post(f"/api/v1/sessions/{sid}/hint", headers=auth(people["s1"]))
    assert r.status_code == 422 and r.json()["detail"]["code"] == "hints_disabled"
    r = act(client, people["s1"], sid, "choose_partial_air", JUST)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "action_unavailable"


def test_finished_session_is_read_only(client, people):
    sid = start(client, people["s1"])
    client.post(f"/api/v1/sessions/{sid}/finish", headers=auth(people["s1"]))
    assert act(client, people["s1"], sid, "review_shipment_documents").status_code == 409


def test_old_sessions_keep_their_scenario_version(app, client, people):
    sid = start(client, people["s1"])
    definition = client.get(
        "/api/v1/teach/scenarios/delayed-shipment/definition", headers=auth(people["prof"])
    ).json()["definition"]
    edited = copy.deepcopy(definition)
    edited["title"] = "Delayed International Shipment (revised)"
    r = client.post(
        "/api/v1/teach/scenarios",
        headers=auth(people["prof"]),
        json={"definition": edited, "change_note": "title"},
    )
    assert r.status_code == 201 and r.json()["version"] == 2
    assert (
        client.get(f"/api/v1/sessions/{sid}", headers=auth(people["s1"])).json()["title"]
        == "Delayed International Shipment"
    )
    new_sid = start(client, people["s1"])
    assert (
        client.get(f"/api/v1/sessions/{new_sid}", headers=auth(people["s1"]))
        .json()["title"]
        .endswith("(revised)")
    )


def test_invalid_scenario_edit_is_rejected_with_errors(client, people):
    definition = client.get(
        "/api/v1/teach/scenarios/delayed-shipment/definition", headers=auth(people["prof"])
    ).json()["definition"]
    definition["rubric"]["criteria"][0]["weight"] = 1
    check = client.post(
        "/api/v1/teach/scenarios/validate",
        headers=auth(people["prof"]),
        json={"definition": definition},
    ).json()
    assert check["valid"] is False and check["errors"]
    r = client.post(
        "/api/v1/teach/scenarios", headers=auth(people["prof"]), json={"definition": definition}
    )
    assert r.status_code == 422


def test_rubric_editing_creates_new_version(client, people):
    definition = client.get(
        "/api/v1/teach/scenarios/delayed-shipment/definition", headers=auth(people["prof"])
    ).json()["definition"]
    rubric = definition["rubric"]
    rubric["criteria"][0]["weight"] += 5
    rubric["criteria"][1]["weight"] -= 5
    r = client.put(
        "/api/v1/teach/scenarios/delayed-shipment/rubric",
        headers=auth(people["prof"]),
        json={"rubric": rubric},
    )
    assert r.status_code == 200 and r.json()["created"] is True and r.json()["version"] == 2


def test_only_admins_publish(client, people):
    r = client.post(
        "/api/v1/admin/scenarios/media-crisis/status",
        headers=auth(people["prof"]),
        json={"status": "archived"},
    )
    assert r.status_code == 403


# ------------------------------------------------------------------ courses, review, progress
def test_assignment_controls_mode_and_difficulty(client, people):
    cid = make_course(client, people["prof"], "s1@example.com")
    client.post(
        f"/api/v1/teach/courses/{cid}/assignments",
        headers=auth(people["prof"]),
        json={"scenario_slug": "delayed-shipment", "mode": "assessment", "difficulty": "advanced"},
    )
    assignments = client.get("/api/v1/me/assignments", headers=auth(people["s1"])).json()
    assert len(assignments) == 1
    sid = start(
        client,
        people["s1"],
        assignment_id=assignments[0]["id"],
        mode="training",
        difficulty="beginner",
    )
    view = client.get(f"/api/v1/sessions/{sid}", headers=auth(people["s1"])).json()
    assert view["mode"] == "assessment" and view["difficulty"] == "advanced"
    assert client.get("/api/v1/me/assignments", headers=auth(people["s2"])).json() == []


def test_professor_review_keeps_original_and_is_audited(app, client, people):
    make_course(client, people["prof"], "s1@example.com")
    sid = start(client, people["s1"])
    act(client, people["s1"], sid, "review_shipment_documents")
    aid = client.post(f"/api/v1/sessions/{sid}/finish", headers=auth(people["s1"])).json()[
        "assessment_id"
    ]
    queue = client.get("/api/v1/teach/review-queue", headers=auth(people["prof"])).json()
    assert [q["assessment_id"] for q in queue] == [aid]
    assert client.get("/api/v1/teach/review-queue", headers=auth(people["other"])).json() == []
    r = client.post(
        f"/api/v1/teach/assessments/{aid}/reviews",
        headers=auth(people["prof"]),
        json={
            "criterion_id": "commercial_knowledge",
            "new_score": 88,
            "justification": "Good use of the packing list.",
        },
    )
    assert r.status_code == 200
    body = r.json()
    crit = next(c for c in body["criteria"] if c["criterion_id"] == "commercial_knowledge")
    assert crit["final_score"] == 88 and crit["original_score"] != 88
    assert body["status"] == "reviewed" and body["reviews"][0]["justification"]
    short = client.post(
        f"/api/v1/teach/assessments/{aid}/reviews",
        headers=auth(people["prof"]),
        json={"justification": "short"},
    )
    assert short.status_code == 422
    denied = client.post(
        f"/api/v1/teach/assessments/{aid}/reviews",
        headers=auth(people["other"]),
        json={
            "criterion_id": "commercial_knowledge",
            "new_score": 10,
            "justification": "Not my student at all.",
        },
    )
    assert denied.status_code == 404
    with app.state.db.session_factory() as s:
        assert (
            s.scalar(select(AuditLog).where(AuditLog.action == "assessment.reviewed")) is not None
        )


def test_course_progress_and_csv_export(client, people):
    cid = make_course(client, people["prof"], "s1@example.com")
    sid = start(client, people["s1"])
    act(client, people["s1"], sid, "review_shipment_documents")
    client.post(f"/api/v1/sessions/{sid}/finish", headers=auth(people["s1"]))
    progress = client.get(
        f"/api/v1/teach/courses/{cid}/progress", headers=auth(people["prof"])
    ).json()
    assert progress["students"][0]["attempts"] == 1
    csv = client.get(f"/api/v1/teach/courses/{cid}/export.csv", headers=auth(people["prof"]))
    assert csv.headers["content-type"].startswith("text/csv")
    assert "s1@example.com" in csv.text


def test_competencies_and_explainable_recommendations(client, people):
    profile = client.get("/api/v1/me/competencies", headers=auth(people["s1"])).json()
    assert profile == []
    recs = client.get("/api/v1/me/recommendations", headers=auth(people["s1"])).json()
    assert recs and all(r["reasons"] for r in recs)
    sid = start(client, people["s1"])
    client.post(f"/api/v1/sessions/{sid}/finish", headers=auth(people["s1"]))
    profile = client.get("/api/v1/me/competencies", headers=auth(people["s1"])).json()
    assert profile and all("confidence" in p for p in profile)


# ------------------------------------------------------------------ resources
def test_resource_upload_search_and_visibility(client, people):
    note = "# CIF obligations\n\nUnder CIF the seller pays freight and insurance to the destination port."
    key = "# Answer key\n\nThe correct transport option is partial air freight of pallet two for the TC units."
    for title, content, vis in [
        ("Trade notes", note, "students"),
        ("Answer key", key, "professors"),
    ]:
        r = client.post(
            "/api/v1/teach/resources",
            headers=auth(people["prof"]),
            json={"title": title, "filename": "notes.md", "content": content, "visibility": vis},
        )
        assert r.status_code == 201, r.text
    hits = client.get(
        "/api/v1/me/resources/search",
        params={"q": "CIF freight seller"},
        headers=auth(people["s1"]),
    ).json()
    assert hits and hits[0]["title"] == "Trade notes"
    hidden = client.get(
        "/api/v1/me/resources/search",
        params={"q": "answer key partial air pallet"},
        headers=auth(people["s1"]),
    ).json()
    assert all(h["title"] != "Answer key" for h in hidden)


def test_resource_upload_validation(client, people):
    bad = client.post(
        "/api/v1/teach/resources",
        headers=auth(people["prof"]),
        json={
            "title": "x" * 5,
            "filename": "malware.exe",
            "content": "some content that is long enough",
        },
    )
    assert bad.status_code == 422


# ------------------------------------------------------------------ admin
def test_admin_settings_and_usage(client, people):
    r = client.patch(
        "/api/v1/admin/settings",
        headers=auth(people["admin"]),
        json={"changes": {"ai_provider": "anthropic"}},
    )
    assert r.status_code == 422  # no API key configured
    r = client.patch(
        "/api/v1/admin/settings",
        headers=auth(people["admin"]),
        json={"changes": {"registration_open": False}},
    )
    assert r.json()["values"]["registration_open"] is False
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "long-enough-pw", "display_name": "N"},
    )
    assert reg.status_code == 403
    usage = client.get("/api/v1/admin/usage", headers=auth(people["admin"])).json()
    assert "breakdown" in usage and "completion_rate" in usage


def test_admin_deactivates_user_and_manages_specializations(client, people):
    users = client.get("/api/v1/admin/users", headers=auth(people["admin"])).json()
    s2 = next(u for u in users if u["email"] == "s2@example.com")
    client.patch(
        f"/api/v1/admin/users/{s2['id']}/active",
        headers=auth(people["admin"]),
        json={"is_active": False},
    )
    assert client.get("/api/v1/users/me", headers=auth(people["s2"])).status_code == 401
    r = client.post(
        "/api/v1/admin/specializations",
        headers=auth(people["admin"]),
        json={"code": "law", "name": "Law", "description": "Legal practice"},
    )
    assert r.status_code == 201
    codes = [
        s["code"] for s in client.get("/api/v1/specializations", headers=auth(people["s1"])).json()
    ]
    assert "law" in codes


def test_demo_seed_is_idempotent(app, settings, synced):
    from app.services.demo import seed

    with app.state.db.session_factory() as s:
        first = seed(s, settings)
        s.commit()
        second = seed(s, settings)
        s.commit()
    assert any(line.startswith("created") for line in first)
    assert not any(line.startswith("created") for line in second)
    with app.state.db.session_factory() as s:
        assert get_by_slug(s, "delayed-shipment") is not None
