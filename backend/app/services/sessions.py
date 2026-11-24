"""Simulation sessions: the bridge between the pure engine, the database and the AI layer.

Every state change goes through `_commit_step`, which
  * rejects stale writes with optimistic concurrency control (`state_version`),
  * stores the engine's events in the append-only `session_events` log,
  * records an optional client idempotency key so retried requests are not applied twice.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai import service as ai
from app.ai.schemas import CharacterTurnRequest, IntentOption
from app.core.config import Settings
from app.models.scenario import Scenario
from app.models.simulation import SessionEvent, SimulationSession
from app.models.user import User
from app.services.scenarios import definition_of
from app.simulation.engine import Engine, EngineError, EventRecord, clone

VALID_MODES = ("training", "assessment")


class ConflictError(Exception):
    """Another request changed the session first. The client should reload and retry."""


class NotFoundError(Exception):
    pass


def engine_for(session: SimulationSession) -> Engine:
    return Engine(
        definition_of(session.scenario_version), mode=session.mode, difficulty=session.difficulty
    )


def start_session(
    db: Session,
    user: User,
    scenario: Scenario,
    *,
    mode: str,
    difficulty: str,
    assignment_id: uuid.UUID | None = None,
) -> SimulationSession:
    if mode not in VALID_MODES:
        raise EngineError("bad_mode", "Mode must be training or assessment.")
    if scenario.current_version is None:
        raise EngineError("no_version", "This scenario has no content yet.")
    engine = Engine(definition_of(scenario.current_version), mode=mode, difficulty=difficulty)
    state, events = engine.start()
    session = SimulationSession(
        user_id=user.id,
        scenario_version_id=scenario.current_version.id,
        assignment_id=assignment_id,
        mode=mode,
        difficulty=difficulty,
        status="active",
        state=state,
        state_version=0,
    )
    db.add(session)
    db.flush()
    _add_events(db, session.id, events, None)
    return session


def _add_events(
    db: Session, session_id: uuid.UUID, events: list[EventRecord], idempotency_key: str | None
) -> None:
    for i, ev in enumerate(events):
        db.add(
            SessionEvent(
                session_id=session_id,
                seq=ev.seq,
                kind=ev.kind,
                actor=ev.actor,
                sim_minute=ev.minute,
                payload=ev.payload,
                idempotency_key=idempotency_key if i == 0 else None,
            )
        )


def already_applied(db: Session, session: SimulationSession, key: str | None) -> bool:
    if not key:
        return False
    return (
        db.scalar(
            select(SessionEvent.id).where(
                SessionEvent.session_id == session.id, SessionEvent.idempotency_key == key
            )
        )
        is not None
    )


def _commit_step(
    db: Session,
    session: SimulationSession,
    new_state: dict,
    events: list[EventRecord],
    *,
    idempotency_key: str | None,
    status: str | None = None,
    outcome_id: str | None = None,
) -> None:
    values: dict = {"state": new_state, "state_version": session.state_version + 1}
    if status:
        values["status"] = status
        if status == "completed":
            values["completed_at"] = datetime.now(UTC)
    if outcome_id:
        values["outcome_id"] = outcome_id
    result = db.execute(
        update(SimulationSession)
        .where(
            SimulationSession.id == session.id,
            SimulationSession.state_version == session.state_version,
        )
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        raise ConflictError("The session changed in the meantime. Please retry.")
    if events:
        _add_events(db, session.id, events, idempotency_key)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Duplicate request.") from None
    db.refresh(session)


def _guard(session: SimulationSession) -> None:
    if session.status != "active":
        raise EngineError("session_finished", "This simulation has already been completed.")


def perform_action(
    db: Session, session: SimulationSession, action_id: str, justification: str, key: str | None
) -> dict:
    if already_applied(db, session, key):
        return {"replayed": True}
    _guard(session)
    engine = engine_for(session)
    state = clone(session.state)
    events = engine.perform_action(state, action_id, justification=justification)
    _commit_step(db, session, state, events, idempotency_key=key)
    return {"replayed": False}


def submit_work(
    db: Session, session: SimulationSession, submission_id: str, text: str, key: str | None
) -> dict:
    if already_applied(db, session, key):
        return {"replayed": True}
    _guard(session)
    engine = engine_for(session)
    state = clone(session.state)
    events = engine.submit(state, submission_id, text)
    _commit_step(db, session, state, events, idempotency_key=key)
    return {"replayed": False}


def take_hint(db: Session, session: SimulationSession, key: str | None) -> dict:
    if already_applied(db, session, key):
        return {"replayed": True, "hint": None}
    _guard(session)
    engine = engine_for(session)
    state = clone(session.state)
    hint, events = engine.take_hint(state)
    _commit_step(db, session, state, events, idempotency_key=key)
    return {"replayed": False, "hint": hint}


def send_message(
    db: Session,
    settings: Settings,
    session: SimulationSession,
    user: User,
    character_id: str,
    text: str,
    key: str | None,
) -> dict:
    if already_applied(db, session, key):
        return {"replayed": True}
    _guard(session)
    engine = engine_for(session)
    d = engine.d
    state = clone(session.state)
    events = engine.record_student_message(state, character_id, text)
    char = d.character(character_id)
    if char is None:  # already validated by record_student_message; defensive
        raise EngineError("unknown_character", "That person is not part of this scenario.")
    ctx = engine.character_context(state, character_id)
    options = [
        IntentOption(a.id, a.label, a.description, a.intent_keywords)
        for a in engine.interpretable_actions(state, character_id)
    ]
    locked = [
        r.fact
        for r in char.restricted
        if not (r.reveal_when and engine._eval(r.reveal_when, state))
    ]
    req = CharacterTurnRequest(
        scenario_title=d.title,
        scenario_context=d.context.briefing,
        student_role=d.context.student_role,
        character_id=char.id,
        character_name=char.name,
        character_role=char.role,
        organization=char.organization,
        personality=char.personality,
        communication_style=char.communication_style,
        objectives=char.objectives,
        knowledge=ctx["knowledge"],
        language=char.language,
        mood=ctx["mood"],
        mode=session.mode,
        history=[{"role": h["role"], "text": h["text"]} for h in ctx["history"][:-1]],
        student_message=text.strip(),
        intent_options=options,
        faq=[f.model_dump() for f in char.faq],
        fallback_replies=char.fallback_replies,
        turn_index=state.get("ai_messages", 0),
    )
    outcome = ai.character_turn(
        db,
        settings,
        req,
        locked_facts=locked,
        user_id=user.id,
        session_id=session.id,
        session_messages=state.get("ai_messages", 0),
    )
    state["ai_messages"] = state.get("ai_messages", 0) + 1
    performed = None
    authored_reply = False
    if outcome.accepted_intent:
        action = d.action(outcome.accepted_intent)
        try:
            # The engine validates availability and applies the deterministic consequences.
            events += engine.perform_action(state, outcome.accepted_intent, source="conversation")
            performed = outcome.accepted_intent
            # Authored responses carry the scenario's authoritative facts; prefer them.
            authored_reply = bool(action and action.character_response)
        except EngineError:
            performed = None  # e.g. the action needs a written justification in the panel
    if not authored_reply:
        events += engine.record_character_message(
            state, character_id, outcome.reply.reply, label=outcome.label, mood=outcome.reply.mood
        )
    if not state["finished"]:
        events += engine.finish_conversation_turn(state)
    _commit_step(db, session, state, events, idempotency_key=key)
    return {"replayed": False, "performed_action": performed, "reply_label": outcome.label}


def finish(db: Session, session: SimulationSession, key: str | None) -> str:
    if already_applied(db, session, key):
        return session.outcome_id or ""
    _guard(session)
    engine = engine_for(session)
    state = clone(session.state)
    outcome_id, events = engine.finish(state)
    _commit_step(
        db, session, state, events, idempotency_key=key, status="completed", outcome_id=outcome_id
    )
    return outcome_id


def abandon(db: Session, session: SimulationSession) -> None:
    _guard(session)
    _commit_step(db, session, clone(session.state), [], idempotency_key=None, status="abandoned")


def view(session: SimulationSession) -> dict:
    engine = engine_for(session)
    data = engine.view(session.state)
    data.update(
        {
            "session_id": str(session.id),
            "status": session.status,
            "state_version": session.state_version,
            "scenario_slug": None,
            "outcome_id": session.outcome_id,
        }
    )
    return data


def events_of(db: Session, session_id: uuid.UUID) -> list[SessionEvent]:
    return list(
        db.scalars(
            select(SessionEvent)
            .where(SessionEvent.session_id == session_id)
            .order_by(SessionEvent.seq)
        )
    )
