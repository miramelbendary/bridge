"""Evaluation tooling reports only recorded data."""

from __future__ import annotations

import uuid

from app.services import evaluation
from tests.conftest import auth


def test_report_on_empty_database_has_no_invented_numbers(app):
    with app.state.db.session_factory() as s:
        data = evaluation.report(s)
    assert data["completion_rate_percent"] is None
    assert data["ai_vs_human"]["mae_points_real_ai"] is None
    assert data["unavailable_here"]


def test_report_and_consistency_after_a_reviewed_attempt(
    app, client, synced, register, create_user, login, settings
):
    from app.models.user import Role

    token = register("eval@example.com")["access_token"]
    sid = client.post(
        "/api/v1/sessions", headers=auth(token), json={"scenario_slug": "delayed-shipment"}
    ).json()["session_id"]
    client.post(
        f"/api/v1/sessions/{sid}/actions",
        headers=auth(token),
        json={"action_id": "review_shipment_documents"},
    )
    aid = client.post(f"/api/v1/sessions/{sid}/finish", headers=auth(token)).json()["assessment_id"]
    create_user("p@example.com", Role.PROFESSOR)
    ptoken = login("p@example.com")
    cid = client.post(
        "/api/v1/teach/courses", headers=auth(ptoken), json={"name": "Course C"}
    ).json()["id"]
    client.post(
        f"/api/v1/teach/courses/{cid}/members",
        headers=auth(ptoken),
        json={"email": "eval@example.com"},
    )
    client.post(
        f"/api/v1/teach/assessments/{aid}/reviews",
        headers=auth(ptoken),
        json={
            "criterion_id": "commercial_knowledge",
            "new_score": 90,
            "justification": "Better than scored.",
        },
    )
    with app.state.db.session_factory() as s:
        data = evaluation.report(s)
        cons = evaluation.consistency(s, settings, uuid.UUID(sid), runs=2)
    assert data["sessions_completed"] == 1 and data["completion_rate_percent"] == 100.0
    assert data["ai_vs_human"]["criterion_corrections_mock"] == 1
    assert data["ai_vs_human"]["mae_points_mock"] is not None
    assert all(
        v["stdev"] == 0 for v in cons["criteria"].values()
    )  # mock evaluator is deterministic
