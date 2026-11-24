"""AI orchestration: provider selection, usage limits, logging, validation and fallbacks.

Nothing in here writes scenario state. Character turns return a *proposal* (reply text, mood,
optional intent) that the session service validates and applies through the engine.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.anthropic_provider import AnthropicProvider, estimate_cost
from app.ai.mock import MockProvider
from app.ai.schemas import (
    AIProviderError,
    AssessmentJudgement,
    AssessmentRequest,
    CharacterReply,
    CharacterTurnRequest,
    Usage,
)
from app.core.config import Settings
from app.models.platform import AIUsageLog
from app.services import platform

MIN_INTENT_CONFIDENCE = 0.6

_INJECTION_PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above) (instructions|prompts?)",
    r"disregard (the |all )?(previous|prior|above)",
    r"you are now",
    r"system prompt",
    r"(give|assign|award) (me |this )?(a |the )?(full|perfect|maximum|100)",
    r"score (of )?100",
    r"as (the|an) (grader|assessor|evaluator)",
    r"\bjailbreak\b",
    r"</?(evidence|student_message|system)>",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def looks_like_injection(text: str) -> bool:
    return bool(_INJECTION_RE.search(text or ""))


def get_provider(db: Session, settings: Settings):
    choice = platform.get(db, settings, "ai_provider")
    if choice == "anthropic" and settings.anthropic_api_key:
        return AnthropicProvider(
            settings.anthropic_api_key, settings.ai_model, settings.ai_timeout_seconds
        )
    return MockProvider()


def _log(
    db: Session,
    *,
    usage: Usage | None,
    provider,
    purpose: str,
    user_id: uuid.UUID | None,
    session_id: uuid.UUID | None,
    success: bool,
    used_fallback: bool,
    error: str | None = None,
) -> None:
    model = usage.model if usage else provider.model
    db.add(
        AIUsageLog(
            user_id=user_id,
            session_id=session_id,
            purpose=purpose,
            provider=usage.provider if usage else provider.name,
            model=model,
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
            latency_ms=usage.latency_ms if usage else 0,
            estimated_cost_usd=(
                0.0
                if (usage is None or usage.is_mock)
                else estimate_cost(model, usage.input_tokens, usage.output_tokens)
            ),
            success=success,
            used_fallback=used_fallback,
            error=(error or None) and error[:300],
        )
    )


@dataclass
class LimitStatus:
    allowed: bool
    reason: str = ""


def check_limits(
    db: Session,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    session_messages: int,
) -> LimitStatus:
    values = platform.get_all(db, settings)
    if session_messages >= values["ai_max_messages_per_session"]:
        return LimitStatus(False, "session_message_limit")
    since = datetime.now(UTC) - timedelta(days=1)
    daily = db.scalar(
        select(func.count())
        .select_from(AIUsageLog)
        .where(AIUsageLog.user_id == user_id, AIUsageLog.created_at >= since)
    )
    if (daily or 0) >= values["ai_daily_requests_per_user"]:
        return LimitStatus(False, "daily_limit")
    spent = db.scalar(
        select(func.coalesce(func.sum(AIUsageLog.estimated_cost_usd), 0.0)).where(
            AIUsageLog.session_id == session_id
        )
    )
    if (spent or 0) >= values["ai_session_budget_usd"]:
        return LimitStatus(False, "session_budget")
    return LimitStatus(True)


def _shingles(text: str, n: int = 5) -> set[str]:
    words = re.findall(r"\w+", text.lower())
    return {" ".join(words[i : i + n]) for i in range(max(0, len(words) - n + 1))}


def leaks_restricted(reply: str, locked_facts: list[str]) -> bool:
    reply_shingles = _shingles(reply)
    return any(_shingles(fact) & reply_shingles for fact in locked_facts)


@dataclass
class CharacterOutcome:
    reply: CharacterReply
    label: str  # ai | mock | fallback | limit
    accepted_intent: str | None


def character_turn(
    db: Session,
    settings: Settings,
    req: CharacterTurnRequest,
    *,
    locked_facts: list[str],
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    session_messages: int,
) -> CharacterOutcome:
    provider = get_provider(db, settings)
    fallback_text = (req.fallback_replies or ["I'll get back to you."])[
        req.turn_index % max(1, len(req.fallback_replies))
    ]
    limits = check_limits(
        db, settings, user_id=user_id, session_id=session_id, session_messages=session_messages
    )
    if not limits.allowed:
        provider = MockProvider()  # free, deterministic replies once limits are reached
        label_if_ok = "limit"
    else:
        label_if_ok = "mock" if provider.is_mock else "ai"

    try:
        reply, usage = provider.character_turn(req)
    except AIProviderError as exc:
        _log(
            db,
            usage=None,
            provider=provider,
            purpose="character",
            user_id=user_id,
            session_id=session_id,
            success=False,
            used_fallback=True,
            error=str(exc),
        )
        return CharacterOutcome(
            CharacterReply(reply=fallback_text, mood=req.mood), "fallback", None
        )  # type: ignore[arg-type]

    allowed_ids = {o.action_id for o in req.intent_options}
    intent = reply.student_intent_action_id
    accepted = (
        intent
        if intent in allowed_ids and reply.intent_confidence >= MIN_INTENT_CONFIDENCE
        else None
    )
    error = None
    if intent and intent not in allowed_ids:
        error = f"rejected_intent:{intent[:60]}"
    if leaks_restricted(reply.reply, locked_facts):
        reply = CharacterReply(reply=fallback_text, mood=reply.mood)
        error = "blocked_restricted_fact"
        label_if_ok = "fallback"
    _log(
        db,
        usage=usage,
        provider=provider,
        purpose="character",
        user_id=user_id,
        session_id=session_id,
        success=True,
        used_fallback=label_if_ok == "fallback",
        error=error,
    )
    return CharacterOutcome(reply, label_if_ok, accepted)


def assess(
    db: Session,
    settings: Settings,
    req: AssessmentRequest,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> tuple[AssessmentJudgement, Usage, bool]:
    """Returns (judgement, usage, used_fallback). Falls back to the mock evaluator on failure."""
    provider = get_provider(db, settings)
    try:
        judgement, usage = provider.assess(req)
        _log(
            db,
            usage=usage,
            provider=provider,
            purpose="assessment",
            user_id=user_id,
            session_id=session_id,
            success=True,
            used_fallback=False,
        )
        return judgement, usage, False
    except AIProviderError as exc:
        _log(
            db,
            usage=None,
            provider=provider,
            purpose="assessment",
            user_id=user_id,
            session_id=session_id,
            success=False,
            used_fallback=True,
            error=str(exc),
        )
        mock = MockProvider()
        judgement, usage = mock.assess(req)
        return judgement, usage, True
