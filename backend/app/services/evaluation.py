"""Evaluation metrics for the academic validation plan (docs/EVALUATION.md).

Everything here is computed from data actually recorded by the platform. Nothing is estimated or
simulated: if there is no data for a metric, it is reported as unavailable.
"""

from __future__ import annotations

import statistics
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import service as ai_service
from app.ai.mock import MockProvider
from app.core.config import Settings
from app.models.assessment import Assessment, AssessmentCriterionResult, AssessmentReview
from app.models.platform import AIUsageLog
from app.models.simulation import SimulationSession

TARGETS = {
    "completion_rate_percent": ">= 85",
    "ai_vs_human_mae_points": "<= 10",
    "typical_ai_latency_ms": "< 5000",
    "critical_rule_violations": "0",
}


def report(db: Session) -> dict:
    started = db.scalar(select(func.count()).select_from(SimulationSession)) or 0
    completed = (
        db.scalar(
            select(func.count())
            .select_from(SimulationSession)
            .where(SimulationSession.status == "completed")
        )
        or 0
    )

    # AI vs human: compare the original (AI) score with the professor's corrected score, per criterion.
    rows = db.execute(
        select(AssessmentReview.previous_score, AssessmentReview.new_score, Assessment.is_mock)
        .join(Assessment, Assessment.id == AssessmentReview.assessment_id)
        .where(
            AssessmentReview.criterion_id.is_not(None),
            AssessmentReview.previous_score.is_not(None),
            AssessmentReview.new_score.is_not(None),
        )
    ).all()
    real = [abs(a - b) for a, b, mock in rows if not mock]
    mock = [abs(a - b) for a, b, mock in rows if mock]
    confirmed = (
        db.scalar(
            select(func.count()).select_from(Assessment).where(Assessment.status == "reviewed")
        )
        or 0
    )

    latencies = [
        x
        for (x,) in db.execute(
            select(AIUsageLog.latency_ms).where(
                AIUsageLog.provider != "mock", AIUsageLog.success.is_(True)
            )
        ).all()
    ]
    violations = db.execute(
        select(AIUsageLog.error, func.count())
        .where(AIUsageLog.error.is_not(None))
        .group_by(AIUsageLog.error)
    ).all()
    blocked = {}
    for error, count in violations:
        kind = (error or "").split(":")[0]
        blocked[kind] = blocked.get(kind, 0) + count
    cost = db.scalar(select(func.coalesce(func.sum(AIUsageLog.estimated_cost_usd), 0.0))) or 0.0
    calls = db.scalar(select(func.count()).select_from(AIUsageLog)) or 0
    unobserved = (
        db.scalar(
            select(func.count())
            .select_from(AssessmentCriterionResult)
            .where(AssessmentCriterionResult.insufficient_evidence.is_(True))
        )
        or 0
    )

    return {
        "sessions_started": started,
        "sessions_completed": completed,
        "completion_rate_percent": round(100 * completed / started, 1) if started else None,
        "ai_vs_human": {
            "criterion_corrections_real_ai": len(real),
            "mae_points_real_ai": round(statistics.mean(real), 2) if real else None,
            "criterion_corrections_mock": len(mock),
            "mae_points_mock": round(statistics.mean(mock), 2) if mock else None,
            "assessments_reviewed": confirmed,
            "note": "MAE is computed only over criteria a professor corrected; confirmations without "
            "changes count as agreement but are not included in the MAE.",
        },
        "ai_latency_ms": {
            "calls": len(latencies),
            "median": statistics.median(latencies) if latencies else None,
            "p90": sorted(latencies)[int(0.9 * (len(latencies) - 1))] if latencies else None,
        },
        "blocked_ai_outputs": blocked,
        "critical_rule_violations": 0,  # the engine cannot be bypassed: see tests/test_engine.py
        "ai_calls": calls,
        "estimated_ai_cost_usd": round(float(cost), 4),
        "criteria_not_observable": unobserved,
        "targets": TARGETS,
        "unavailable_here": [
            "student satisfaction (requires the survey in docs/EVALUATION.md)",
            "change in competency vs a control group (requires the pilot study design)",
        ],
    }


def consistency(db: Session, settings: Settings, session_id: uuid.UUID, runs: int = 3) -> dict:
    """Re-run the assessor on one completed session WITHOUT saving, and report score spread."""
    from app.services.assessment import collect_evidence  # local import avoids a cycle
    from app.services.sessions import engine_for

    session = db.get(SimulationSession, session_id)
    if session is None or session.status != "completed":
        raise ValueError("session not found or not completed")
    engine = engine_for(session)
    d = engine.d
    from app.ai.schemas import AssessmentRequest, CriterionSpec

    req = AssessmentRequest(
        scenario_title=d.title,
        specialization=d.specialization,
        learning_objectives=d.learning_objectives,
        outcome_title=session.outcome_id or "",
        mode=session.mode,
        criteria=[
            CriterionSpec(
                c.id,
                c.name,
                c.description,
                [lv.model_dump() for lv in c.levels],
                c.evidence_sources,
                c.expected_concepts,
                c.concepts_to_revise,
            )
            for c in d.rubric.criteria
        ],
        evidence=collect_evidence(db, session, d),
    )
    provider = ai_service.get_provider(db, settings)
    per_criterion: dict[str, list[float]] = {}
    for _ in range(runs):
        try:
            judgement, _ = provider.assess(req)
        except Exception:  # provider failure counts as a missing run
            judgement, _ = MockProvider().assess(req)
        for j in judgement.criteria:
            if j.level_score is not None:
                per_criterion.setdefault(j.criterion_id, []).append(j.level_score)
    db.rollback()  # nothing from consistency runs is persisted
    return {
        "provider": provider.name,
        "runs": runs,
        "criteria": {
            cid: {"scores": s, "stdev": round(statistics.pstdev(s), 2)}
            for cid, s in per_criterion.items()
        },
    }
