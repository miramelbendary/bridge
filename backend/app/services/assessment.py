"""Assessment engine.

Flow: collect student-authored evidence from the event log -> ask the (AI or mock) assessor for a
qualitative judgement per rubric criterion -> validate it (known criteria, allowed level scores,
evidence refs that exist and are relevant) -> blend with rule-based objective signals -> compute
the weighted overall score deterministically -> build the personalised report -> persist.

The assessor never produces the final number; this module does.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import service as ai
from app.ai.mock import MockProvider, matches_source
from app.ai.schemas import AssessmentRequest, CriterionJudgement, CriterionSpec, EvidenceItem
from app.core.config import Settings
from app.models.assessment import Assessment, AssessmentCriterionResult, AssessmentReview
from app.models.simulation import SimulationSession
from app.models.user import User
from app.services import knowledge
from app.services.sessions import engine_for, events_of
from app.simulation import conditions
from app.simulation.competencies import label as competency_label
from app.simulation.schema import Criterion, ScenarioDefinition

DISCLAIMER = (
    "BRIDGE is a formative learning tool. This assessment supports your learning and can be "
    "reviewed and corrected by your professor; it is not a high-stakes examination result."
)


def collect_evidence(
    db: Session, session: SimulationSession, d: ScenarioDefinition
) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    latest_submission_seq: dict[str, int] = {}
    events = events_of(db, session.id)
    for ev in events:
        if ev.kind == "submission":
            latest_submission_seq[ev.payload["submission_id"]] = ev.seq
    for ev in events:
        p = ev.payload
        if ev.kind == "action":
            text = f"{p.get('label', '')}. Justification: {p.get('justification') or '(none)'}"
            items.append(
                EvidenceItem(f"E{ev.seq}", "action", f"Decision at minute {ev.sim_minute}", text)
            )
        elif ev.kind == "student_message":
            char = d.character(p.get("to", ""))
            who = char.name if char else p.get("to", "")
            items.append(
                EvidenceItem(
                    f"E{ev.seq}",
                    "student_message",
                    f"Message to {who}",
                    p.get("text", ""),
                    p.get("to", ""),
                )
            )
        elif ev.kind == "submission" and latest_submission_seq.get(p["submission_id"]) == ev.seq:
            spec = d.submission(p["submission_id"])
            items.append(
                EvidenceItem(
                    f"E{ev.seq}",
                    "submission",
                    f"Final version of '{spec.title if spec else p['submission_id']}'",
                    p.get("text", ""),
                    p["submission_id"],
                )
            )
    return items


def objective_score(
    criterion: Criterion, state: dict, mode: str, difficulty: str
) -> tuple[float | None, list[str]]:
    if criterion.objective_weight <= 0:
        return None, []
    score = criterion.objective_base
    notes = []
    for sig in criterion.objective_signals:
        if conditions.evaluate(sig.when, state, mode=mode, difficulty=difficulty):
            score += sig.points
            notes.append(sig.description)
    return max(0.0, min(100.0, score)), notes


def _validate_judgement(
    j: CriterionJudgement | None, criterion: Criterion, evidence: list[EvidenceItem]
) -> tuple[CriterionJudgement | None, str | None]:
    """Return (judgement or None if unusable, problem description)."""
    if j is None:
        return None, "missing"
    allowed_scores = {lv.score for lv in criterion.levels}
    relevant_refs = {e.ref for e in evidence if matches_source(e, criterion.evidence_sources)}
    if j.insufficient_evidence:
        return j.model_copy(update={"level_score": None, "evidence_refs": []}), None
    if j.level_score is None or j.level_score not in allowed_scores:
        return None, "invalid_level"
    valid_refs = [r for r in j.evidence_refs if r in relevant_refs]
    if not valid_refs:
        return None, "unsupported_evidence"
    if len(valid_refs) != len(j.evidence_refs):
        return j.model_copy(update={"evidence_refs": valid_refs}), "removed_invalid_refs"
    return j, None


def assess_session(
    db: Session, settings: Settings, session: SimulationSession, student: User
) -> Assessment:
    existing = db.scalar(select(Assessment).where(Assessment.session_id == session.id))
    if existing is not None:
        return existing
    engine = engine_for(session)
    d = engine.d
    state = session.state
    evidence = collect_evidence(db, session, d)
    outcome = next((o for o in d.outcomes if o.id == session.outcome_id), d.outcomes[-1])

    criteria_specs = [
        CriterionSpec(
            id=c.id,
            name=c.name,
            description=c.description,
            levels=[lv.model_dump() for lv in c.levels],
            evidence_sources=c.evidence_sources,
            expected_concepts=c.expected_concepts,
            concepts_to_revise=c.concepts_to_revise,
        )
        for c in d.rubric.criteria
    ]
    spec_id = session.scenario_version.scenario_id
    from app.models.scenario import Scenario

    scenario = db.get(Scenario, spec_id)
    references = knowledge.search(
        db,
        " ".join(t for c in d.rubric.criteria for t in c.concepts_to_revise),
        specialization_id=scenario.specialization_id if scenario else None,
        limit=4,
    )
    req = AssessmentRequest(
        scenario_title=d.title,
        specialization=d.specialization,
        learning_objectives=d.learning_objectives,
        outcome_title=outcome.title,
        mode=session.mode,
        criteria=criteria_specs,
        evidence=evidence,
        references=references,
    )
    judgement, usage, used_fallback = ai.assess(
        db, settings, req, user_id=student.id, session_id=session.id
    )
    mock_judgement = None
    flags: list[str] = []
    if used_fallback:
        flags.append("ai_unavailable_used_mock_evaluator")
    if judgement.possible_manipulation_detected or any(
        ai.looks_like_injection(e.text) for e in evidence
    ):
        flags.append("possible_manipulation_attempt")

    by_id = {j.criterion_id: j for j in judgement.criteria}
    unknown = set(by_id) - {c.id for c in d.rubric.criteria}
    if unknown:
        flags.append("ignored_unknown_criteria")

    assessment = Assessment(
        session_id=session.id,
        provider=usage.provider,
        model=usage.model,
        is_mock=usage.is_mock,
        rubric_snapshot=d.rubric.model_dump(mode="json"),
        flags=flags,
    )
    weighted_sum = 0.0
    weight_total = 0.0
    for position, criterion in enumerate(d.rubric.criteria):
        j, problem = _validate_judgement(by_id.get(criterion.id), criterion, evidence)
        if j is None:
            # Unusable AI output for this criterion: use the transparent mock evaluation instead.
            if mock_judgement is None:
                mock_judgement, _ = MockProvider().assess(req)
            j = next(m for m in mock_judgement.criteria if m.criterion_id == criterion.id)
            flags.append(f"{criterion.id}:{problem}:used_rule_based_fallback")
        elif problem:
            flags.append(f"{criterion.id}:{problem}")

        obj, obj_notes = objective_score(criterion, state, session.mode, session.difficulty)
        qual = j.level_score
        if j.insufficient_evidence:
            # Missing evidence is not failure: only observed, rule-based signals can score it.
            score = obj if (obj is not None and obj_notes) else None
        elif obj is None:
            score = qual
        else:
            score = (1 - criterion.objective_weight) * qual + criterion.objective_weight * obj  # type: ignore[operator]
        if score is not None:
            score = round(score, 1)
            weighted_sum += criterion.weight * score
            weight_total += criterion.weight
        level_label = next(
            (lv.label for lv in criterion.levels if lv.score == qual), "Insufficient evidence"
        )
        evidence_detail = [
            {"ref": e.ref, "summary": e.summary, "excerpt": e.text[:240]}
            for e in evidence
            if e.ref in j.evidence_refs
        ]
        explanation = j.explanation
        if obj_notes:
            explanation = explanation.rstrip()
            explanation += (
                " Observed in the simulation: " + "; ".join(n.rstrip(".") for n in obj_notes) + "."
            )
        assessment.criteria.append(
            AssessmentCriterionResult(
                position=position,
                criterion_id=criterion.id,
                competency=criterion.competency,
                weight=criterion.weight,
                insufficient_evidence=score is None,
                qualitative_score=qual,
                objective_score=obj,
                original_score=score,
                final_score=score,
                level_label=level_label,
                explanation=explanation,
                evidence=evidence_detail,
                weaknesses=j.weaknesses,
                improvements=j.improvements,
                uncertainty="high" if score is None else j.uncertainty,
            )
        )
    overall = round(weighted_sum / weight_total, 1) if weight_total else None
    assessment.original_overall = overall
    assessment.final_overall = overall
    assessment.flags = flags
    assessment.status = (
        "needs_review" if "possible_manipulation_attempt" in flags else "ai_generated"
    )
    assessment.report = build_report(
        db,
        session,
        d,
        assessment,
        judgement.overall_feedback,
        judgement.strengths,
        outcome,
        scenario.specialization_id if scenario else None,
        weight_total,
    )
    db.add(assessment)
    db.flush()
    return assessment


def build_report(
    db,
    session,
    d,
    assessment,
    overall_feedback,
    strengths,
    outcome,
    specialization_id,
    weight_total,
) -> dict:
    criteria = assessment.criteria
    weak = [c for c in criteria if c.final_score is not None and c.final_score < 65]
    concepts = []
    for c in weak:
        crit = next(x for x in d.rubric.criteria if x.id == c.criterion_id)
        for concept in crit.concepts_to_revise:
            concepts.append(
                {
                    "concept": concept,
                    "criterion": crit.name,
                    "resources": [
                        {"title": r["title"], "heading": r["heading"], "excerpt": r["text"][:300]}
                        for r in knowledge.search(
                            db, concept, specialization_id=specialization_id, limit=2
                        )
                    ],
                }
            )
    decisions = []
    for ev in events_of(db, session.id):
        if ev.kind == "action":
            decisions.append(
                {
                    "minute": ev.sim_minute,
                    "label": ev.payload.get("label"),
                    "justification": ev.payload.get("justification"),
                    "consequence": ev.payload.get("consequence"),
                    "effects": [
                        {
                            "label": d.variables[e["var"]].label,
                            "before": e["before"],
                            "after": e["after"],
                            "unit": d.variables[e["var"]].unit,
                        }
                        for e in ev.payload.get("effects", [])
                        if e["var"] in d.variables and d.variables[e["var"]].visible
                    ],
                    "via": ev.payload.get("source"),
                }
            )
    total_weight = sum(c.weight for c in d.rubric.criteria)
    return {
        "scenario_title": d.title,
        "outcome": {"id": outcome.id, "title": outcome.title, "description": outcome.description},
        "overall_feedback": overall_feedback,
        # Strengths are derived from the FINAL scores so they can never contradict them. The mock
        # evaluator's own list is ignored; a real assessor's phrasing is kept only for strong criteria.
        "strengths": _strengths(d, criteria, strengths, assessment.is_mock),
        "areas_for_improvement": [
            {
                "criterion": next(x.name for x in d.rubric.criteria if x.id == c.criterion_id),
                "competency": competency_label(c.competency),
                "score": c.final_score,
                "weaknesses": c.weaknesses,
                "improvements": c.improvements,
            }
            for c in criteria
            if c.final_score is not None and c.final_score < 65
        ],
        "not_assessed": [
            next(x.name for x in d.rubric.criteria if x.id == c.criterion_id)
            for c in criteria
            if c.final_score is None
        ],
        "assessed_weight_percent": round(100 * weight_total / total_weight) if total_weight else 0,
        "key_decisions": decisions,
        "alternative_approaches": d.alternative_approaches,
        "concepts_to_revise": concepts,
        "final_variables": [
            {"label": v.label, "value": session.state["variables"][k], "unit": v.unit}
            for k, v in d.variables.items()
            if v.visible
        ],
        "disclaimer": DISCLAIMER,
        "review_status": d.review_status,
    }


def _strengths(d, criteria, ai_strengths: list[str], is_mock: bool) -> list[str]:
    strong = [c for c in criteria if c.final_score is not None and c.final_score >= 75]
    if not strong:
        return []
    if ai_strengths and not is_mock:
        return ai_strengths
    names = {x.id: x.name for x in d.rubric.criteria}
    return [f"{names[c.criterion_id]} ({c.final_score:.0f}): {c.level_label}" for c in strong]


def apply_review(
    db: Session,
    assessment: Assessment,
    reviewer: User,
    *,
    criterion_id: str | None,
    new_score: float | None,
    justification: str,
) -> Assessment:
    justification = justification.strip()
    if len(justification) < 10:
        raise ValueError("A justification of at least 10 characters is required.")
    previous = None
    if criterion_id is not None:
        result = next((c for c in assessment.criteria if c.criterion_id == criterion_id), None)
        if result is None:
            raise ValueError("Unknown criterion.")
        if new_score is not None and not (0 <= new_score <= 100):
            raise ValueError("Scores must be between 0 and 100.")
        previous = result.final_score
        result.final_score = new_score
        result.insufficient_evidence = new_score is None
    db.add(
        AssessmentReview(
            assessment_id=assessment.id,
            reviewer_id=reviewer.id,
            criterion_id=criterion_id,
            previous_score=previous,
            new_score=new_score,
            justification=justification,
        )
    )
    scored = [c for c in assessment.criteria if c.final_score is not None]
    total = sum(c.weight for c in scored)
    assessment.final_overall = (
        round(sum(c.weight * c.final_score for c in scored) / total, 1) if total else None  # type: ignore[operator]
    )
    assessment.status = "reviewed"
    db.flush()
    return assessment
