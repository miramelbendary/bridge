"""Competency profiles and transparent, rule-based scenario recommendations."""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment import Assessment, AssessmentCriterionResult
from app.models.scenario import Scenario
from app.models.simulation import SimulationSession
from app.models.user import User
from app.services.scenarios import definition_of, list_scenarios
from app.simulation.competencies import label
from app.simulation.schema import DIFFICULTY_ORDER

WEAK_THRESHOLD = 65
STRONG_THRESHOLD = 80


def _confidence(n: int) -> str:
    if n <= 1:
        return "low"
    if n <= 3:
        return "medium"
    return "high"


def competency_profile(db: Session, user_id: uuid.UUID) -> list[dict]:
    rows = db.execute(
        select(AssessmentCriterionResult, SimulationSession.completed_at)
        .join(Assessment, AssessmentCriterionResult.assessment_id == Assessment.id)
        .join(SimulationSession, Assessment.session_id == SimulationSession.id)
        .where(SimulationSession.user_id == user_id)
        .order_by(SimulationSession.completed_at)
    ).all()
    data: dict[str, list[tuple[float, object]]] = defaultdict(list)
    unobserved: dict[str, int] = defaultdict(int)
    for result, completed_at in rows:
        if result.final_score is None:
            unobserved[result.competency] += 1
        else:
            data[result.competency].append((result.final_score, completed_at))
    profile = []
    for comp in sorted(set(data) | set(unobserved)):
        scores = [s for s, _ in data.get(comp, [])]
        n = len(scores)
        profile.append(
            {
                "competency": comp,
                "label": label(comp),
                "average": round(sum(scores) / n, 1) if n else None,
                "latest": scores[-1] if n else None,
                "attempts": n,
                "not_observed": unobserved.get(comp, 0),
                "trend": [
                    {"score": s, "at": at.isoformat() if at else None}
                    for s, at in data.get(comp, [])
                ],
                "confidence": _confidence(n),
                "note": (
                    "Based on a single attempt — treat as a first indication, not a stable measure."
                    if n == 1
                    else ("Not yet observed in any attempt." if n == 0 else "")
                ),
            }
        )
    return profile


def recommendations(db: Session, user: User, limit: int = 3) -> list[dict]:
    profile = {p["competency"]: p for p in competency_profile(db, user.id)}
    weak = {
        c: p
        for c, p in profile.items()
        if p["average"] is not None and p["average"] < WEAK_THRESHOLD
    }
    my_spec = user.profile.specialization_id if user.profile else None

    attempts = db.execute(
        select(SimulationSession, Assessment)
        .outerjoin(Assessment, Assessment.session_id == SimulationSession.id)
        .where(SimulationSession.user_id == user.id, SimulationSession.status == "completed")
    ).all()
    best_by_scenario: dict[uuid.UUID, tuple[float | None, str]] = {}
    for sess, assessment in attempts:
        sid = sess.scenario_version.scenario_id
        score = assessment.final_overall if assessment else None
        prev = best_by_scenario.get(sid)
        if prev is None or (score or 0) > (prev[0] or 0):
            best_by_scenario[sid] = (score, sess.difficulty)

    candidates = []
    for scenario in list_scenarios(db, include_unpublished=False):
        d = definition_of(scenario.current_version)  # type: ignore[arg-type]
        comps = {c.competency: c.weight for c in d.rubric.criteria}
        reasons = []
        score = 0.0
        targeted = [c for c in comps if c in weak]
        if targeted:
            score += sum(comps[c] for c in targeted)
            reasons.append(
                "Practises "
                + ", ".join(f"{label(c)} (your average {weak[c]['average']:.0f})" for c in targeted)
            )
        if my_spec and scenario.specialization_id == my_spec:
            score += 25
            reasons.append(f"Matches your specialization ({scenario.specialization.name})")
        best = best_by_scenario.get(scenario.id)
        offered = list(d.difficulties.keys())
        if best is None:
            score += 20
            reasons.append("You have not tried this scenario yet")
            difficulty = offered[0]
        else:
            best_score, best_diff = best
            idx = DIFFICULTY_ORDER.index(best_diff)
            if (
                best_score is not None
                and best_score >= STRONG_THRESHOLD
                and idx + 1 < len(DIFFICULTY_ORDER)
            ):
                nxt = DIFFICULTY_ORDER[idx + 1]
                difficulty = nxt if nxt in offered else best_diff
                reasons.append(f"You scored {best_score:.0f} at {best_diff}; try {difficulty} next")
                score += 10
            else:
                difficulty = best_diff
                if best_score is not None:
                    reasons.append(
                        f"Retry at {best_diff} to improve on your score of {best_score:.0f}"
                    )
                score -= 5
        mode = "training" if (targeted or best is None) else "assessment"
        candidates.append(
            {
                "scenario_slug": scenario.slug,
                "title": d.title,
                "specialization": scenario.specialization.name,
                "difficulty": difficulty,
                "mode": mode,
                "score": score,
                "reasons": reasons or ["Broadens your experience"],
            }
        )
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:limit]


def scenario_of_session(db: Session, session: SimulationSession) -> Scenario | None:
    return db.get(Scenario, session.scenario_version.scenario_id)
