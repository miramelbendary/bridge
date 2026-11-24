"""Deterministic mock AI provider.

Runs BRIDGE end to end without any API key: characters answer from authored FAQ entries and
fallback lines, intent is recognised by keywords, and assessments use transparent keyword and
evidence heuristics. Every output it produces is labelled as mock in the UI and the database.
It is a demonstration and testing tool, not a substitute for a real evaluator.
"""

from __future__ import annotations

import re

from app.ai.schemas import (
    AssessmentJudgement,
    AssessmentRequest,
    CharacterReply,
    CharacterTurnRequest,
    CriterionJudgement,
    Usage,
)

PROVIDER = "mock"
MODEL = "bridge-mock-1"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def _hits(text: str, keywords: list[str]) -> list[str]:
    t = _norm(text)
    return [k for k in keywords if k.lower() in t]


class MockProvider:
    name = PROVIDER
    model = MODEL
    is_mock = True

    def character_turn(self, req: CharacterTurnRequest) -> tuple[CharacterReply, Usage]:
        best, best_hits = None, 0
        for opt in req.intent_options:
            n = len(_hits(req.student_message, opt.keywords))
            if n > best_hits:
                best, best_hits = opt, n
        text = None
        for entry in req.faq:
            if _hits(req.student_message, entry["keywords"]):
                text = entry["reply"]
                break
        if text is None:
            lines = req.fallback_replies or ["Noted."]
            text = lines[req.turn_index % len(lines)]
        reply = CharacterReply(
            reply=text,
            mood=req.mood,  # type: ignore[arg-type]
            student_intent_action_id=best.action_id if best else None,
            intent_confidence=min(1.0, 0.45 + 0.25 * best_hits) if best else 0.0,
        )
        return reply, Usage(PROVIDER, MODEL, is_mock=True)

    def assess(self, req: AssessmentRequest) -> tuple[AssessmentJudgement, Usage]:
        results: list[CriterionJudgement] = []
        strengths: list[str] = []
        for c in req.criteria:
            relevant = [e for e in req.evidence if _matches_source(e, c.evidence_sources)]
            if not relevant:
                results.append(
                    CriterionJudgement(
                        criterion_id=c.id,
                        insufficient_evidence=True,
                        explanation=(
                            "No student work relevant to this criterion was recorded, so it "
                            "could not be assessed. This is not the same as a weak performance."
                        ),
                        uncertainty="high",
                    )
                )
                continue
            corpus = " ".join(e.text for e in relevant)
            concepts = c.expected_concepts or []
            covered = _hits(corpus, concepts)
            coverage = len(covered) / len(concepts) if concepts else 0.5
            levels = sorted(c.levels, key=lambda lv: lv["score"])
            if coverage >= 0.6:
                level = levels[-1]
            elif coverage >= 0.35:
                level = levels[min(2, len(levels) - 1)]
            elif coverage >= 0.15:
                level = levels[min(1, len(levels) - 1)]
            else:
                level = levels[0]
            cited = [e for e in relevant if _hits(e.text, concepts)] or relevant
            missing = [k for k in concepts if k not in covered]
            explanation = (
                f"Level '{level['label']}': your work addressed {len(covered)} of "
                f"{len(concepts)} key ideas for this criterion"
                + (f" ({', '.join(covered[:6])})." if covered else ".")
            )
            if level["score"] >= 75:
                strengths.append(f"{c.name}: {level['descriptor']}")
            results.append(
                CriterionJudgement(
                    criterion_id=c.id,
                    level_score=level["score"],
                    explanation=explanation,
                    evidence_refs=[e.ref for e in cited[:4]],
                    weaknesses=(
                        [f"Did not clearly address: {', '.join(missing[:5])}."] if missing else []
                    ),
                    improvements=[f"Revise: {t}" for t in c.concepts_to_revise[:3]],
                    uncertainty="medium" if len(relevant) >= 2 else "high",
                )
            )
        judgement = AssessmentJudgement(
            criteria=results,
            overall_feedback=(
                "This assessment was produced by BRIDGE's offline mock evaluator, which checks "
                "your recorded actions and the key ideas in your writing against the rubric. "
                "A professor can review and correct it."
            ),
            strengths=strengths[:5],
        )
        return judgement, Usage(PROVIDER, MODEL, is_mock=True)


def _matches_source(item, sources: list[str]) -> bool:
    for src in sources:
        kind, _, ref = src.partition(":")
        if kind == "actions" and item.kind == "action":
            return True
        if (
            kind == "messages"
            and item.kind == "student_message"
            and (not ref or ref == item.target)
        ):
            return True
        if kind == "submission" and item.kind == "submission" and ref == item.target:
            return True
    return False


matches_source = _matches_source
