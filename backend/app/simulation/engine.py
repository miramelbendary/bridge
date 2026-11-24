"""Deterministic simulation engine.

The engine is a pure state machine: given a scenario definition, a session's state and a student
step, it validates the step, mutates the state and returns the events that happened. It has no
database, network or AI access, which makes every rule testable and every outcome reproducible.

Only this module changes authoritative state (variables, tasks, clock, outcome). AI output can at
most *propose* an action id, which still goes through `perform_action` validation.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from app.simulation import conditions
from app.simulation.schema import (
    Action,
    Effect,
    ScenarioDefinition,
    difficulty_allows,
)

MAX_MESSAGE_CHARS = 2000
MAX_SUBMISSION_CHARS = 20000
MAX_JUSTIFICATION_CHARS = 2000
MIN_JUSTIFICATION_CHARS = 15
MAX_EVENT_CASCADE = 100


class EngineError(Exception):
    """A step the rules do not allow. `code` is stable for API clients and tests."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class EventRecord:
    seq: int
    kind: str
    actor: str
    minute: int
    payload: dict[str, Any] = field(default_factory=dict)


def word_count(text: str) -> int:
    return len([w for w in text.split() if w.strip()])


class Engine:
    def __init__(self, definition: ScenarioDefinition, *, mode: str, difficulty: str) -> None:
        if difficulty not in definition.difficulties:
            raise EngineError("difficulty_unavailable", f"{difficulty} is not offered here")
        self.d = definition
        self.mode = mode
        self.difficulty = difficulty
        self.settings = definition.difficulties[difficulty]  # type: ignore[index]

    # ------------------------------------------------------------------ helpers
    def _eval(self, cond: dict | None, state: dict) -> bool:
        return conditions.evaluate(cond, state, mode=self.mode, difficulty=self.difficulty)

    def _emit(self, state: dict, out: list[EventRecord], kind: str, actor: str, **payload) -> int:
        state["seq"] += 1
        out.append(EventRecord(state["seq"], kind, actor, state["clock"], payload))
        return state["seq"]

    def _log(self, state: dict, kind: str, text: str) -> None:
        state["log"].append({"minute": state["clock"], "kind": kind, "text": text})

    def _apply_effects(self, state: dict, effects: list[Effect]) -> list[dict]:
        applied = []
        for e in effects:
            spec = self.d.variables[e.var]
            before = state["variables"][e.var]
            after = before + e.value if e.op == "add" else e.value
            if spec.min is not None:
                after = max(spec.min, after)
            if spec.max is not None:
                after = min(spec.max, after)
            state["variables"][e.var] = after
            applied.append({"var": e.var, "before": before, "after": after})
        return applied

    def _reveal(self, state: dict, doc_ids: list[str]) -> list[str]:
        new = []
        for doc_id in doc_ids:
            doc = next(d for d in self.d.documents if d.id == doc_id)
            if not difficulty_allows(doc.min_difficulty, self.difficulty):
                continue
            if doc_id not in state["visible_documents"]:
                state["visible_documents"].append(doc_id)
                new.append(doc_id)
        return new

    def _character_present(self, char_id: str) -> bool:
        char = self.d.character(char_id)
        return char is not None and difficulty_allows(char.min_difficulty, self.difficulty)

    def _add_inbox(self, state: dict, msg_id: str, sender: str, subject: str, body: str) -> None:
        state["inbox"].append(
            {
                "id": msg_id,
                "sender": sender,
                "subject": subject,
                "body": body,
                "minute": state["clock"],
            }
        )

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> tuple[dict, list[EventRecord]]:
        """Build the initial state and the events that happen at minute 0."""
        variables = {k: v.initial for k, v in self.d.variables.items()}
        variables.update(self.settings.variable_overrides)
        state: dict[str, Any] = {
            "seq": 0,
            "clock": 0,
            "time_limit": self.settings.time_limit_minutes,
            "time_up": False,
            "finished": False,
            "variables": variables,
            "actions_taken": [],
            "exclusive_choices": {},
            "events_fired": [],
            "tasks": {t.id: "open" for t in self.d.tasks if t.initially_visible},
            "visible_documents": [],
            "inbox": [],
            "conversations": {},
            "moods": {c.id: c.initial_mood for c in self.d.characters},
            "submissions": {},
            "hints_used": [],
            "feedback": [],
            "log": [],
            "ai_messages": 0,
        }
        self._reveal(state, [d.id for d in self.d.documents if d.initially_visible])
        for m in self.d.initial_inbox:
            if difficulty_allows(m.min_difficulty, self.difficulty):
                self._add_inbox(state, m.id, m.sender, m.subject, m.body)
        out: list[EventRecord] = []
        self._emit(
            state, out, "session_started", "system", mode=self.mode, difficulty=self.difficulty
        )
        self._fire_due_events(state, out)
        return state, out

    def _ensure_active(self, state: dict) -> None:
        if state["finished"]:
            raise EngineError("session_finished", "This simulation has already been completed.")

    def _advance(self, state: dict, minutes: int, out: list[EventRecord]) -> None:
        state["clock"] += minutes
        self._fire_due_events(state, out)
        if state["clock"] >= state["time_limit"] and not state["time_up"]:
            state["time_up"] = True
            self._log(state, "time", "Simulated working time is over. Submit your work and finish.")
            self._emit(state, out, "time_up", "system")

    def _fire_due_events(self, state: dict, out: list[EventRecord]) -> None:
        for _ in range(MAX_EVENT_CASCADE):
            fired = False
            for ev in self.d.events:
                if ev.id in state["events_fired"]:
                    continue
                if not difficulty_allows(ev.min_difficulty, self.difficulty):
                    continue
                if ev.at_minute is None and ev.when is None:
                    continue  # only fired explicitly by an action
                if ev.at_minute is not None and state["clock"] < ev.at_minute:
                    continue
                if not self._eval(ev.when, state):
                    continue
                self._fire_event(state, ev.id, out)
                fired = True
            if not fired:
                return
        raise EngineError("event_cascade", "Scenario events trigger each other endlessly.")

    def _fire_event(self, state: dict, event_id: str, out: list[EventRecord]) -> None:
        ev = self.d.event(event_id)
        if ev is None or event_id in state["events_fired"]:
            return
        if not difficulty_allows(ev.min_difficulty, self.difficulty):
            return
        state["events_fired"].append(event_id)
        applied = self._apply_effects(state, ev.effects)
        revealed = self._reveal(state, ev.reveals_documents)
        for t in ev.adds_tasks:
            state["tasks"].setdefault(t, "open")
        if ev.message and self._character_present(ev.message.sender):
            self._add_inbox(
                state, f"ev_{ev.id}", ev.message.sender, ev.message.subject, ev.message.body
            )
        if ev.notification:
            self._log(state, "event", ev.notification)
        self._emit(
            state,
            out,
            "scenario_event",
            "system",
            event_id=ev.id,
            title=ev.title,
            effects=applied,
            revealed_documents=revealed,
            added_tasks=list(ev.adds_tasks),
        )

    # ------------------------------------------------------------------ actions
    def action_available(self, state: dict, action: Action) -> bool:
        if state["finished"] or state["time_up"]:
            return False
        if not action.repeatable and action.id in state["actions_taken"]:
            return False
        if action.exclusive_group and action.exclusive_group in state["exclusive_choices"]:
            return False
        if action.via_character and not self._character_present(action.via_character):
            return False
        return self._eval(action.available_when, state)

    def available_actions(self, state: dict) -> list[Action]:
        return [a for a in self.d.actions if self.action_available(state, a)]

    def perform_action(
        self,
        state: dict,
        action_id: str,
        *,
        justification: str = "",
        source: str = "decision_panel",
    ) -> list[EventRecord]:
        self._ensure_active(state)
        action = self.d.action(action_id)
        if action is None:
            raise EngineError("unknown_action", "That action does not exist in this scenario.")
        if not self.action_available(state, action):
            raise EngineError("action_unavailable", "That action is not available right now.")
        justification = (justification or "").strip()
        if len(justification) > MAX_JUSTIFICATION_CHARS:
            raise EngineError("too_long", "Justification is too long.")
        if action.requires_justification and len(justification) < MIN_JUSTIFICATION_CHARS:
            raise EngineError(
                "justification_required", "Explain the reasoning behind this decision first."
            )

        out: list[EventRecord] = []
        state["actions_taken"].append(action.id)
        if action.exclusive_group:
            state["exclusive_choices"][action.exclusive_group] = action.id
        applied = self._apply_effects(state, action.effects)
        revealed = self._reveal(state, action.reveals_documents)
        for t in action.completes_tasks:
            if t in state["tasks"]:
                state["tasks"][t] = "done"
        self._log(state, "decision", f"{action.label}: {action.consequence}")
        if self.mode == "training" and action.training_feedback:
            state["feedback"].append({"minute": state["clock"], "text": action.training_feedback})
        self._emit(
            state,
            out,
            "action",
            "student",
            action_id=action.id,
            label=action.label,
            justification=justification,
            consequence=action.consequence,
            effects=applied,
            revealed_documents=revealed,
            completed_tasks=list(action.completes_tasks),
            source=source,
        )
        if action.via_character and action.character_response:
            conv = state["conversations"].setdefault(action.via_character, [])
            seq = self._emit(
                state,
                out,
                "character_message",
                action.via_character,
                text=action.character_response,
                scripted=True,
            )
            conv.append(
                {
                    "role": "character",
                    "text": action.character_response,
                    "minute": state["clock"],
                    "seq": seq,
                    "label": "scripted",
                }
            )
        for ev_id in action.triggers_events:
            self._fire_event(state, ev_id, out)
        self._advance(state, action.duration_minutes, out)
        return out

    # ------------------------------------------------------------------ conversation
    def record_student_message(self, state: dict, char_id: str, text: str) -> list[EventRecord]:
        self._ensure_active(state)
        if not self._character_present(char_id):
            raise EngineError("unknown_character", "That person is not part of this scenario.")
        text = (text or "").strip()
        if not text:
            raise EngineError("empty", "Write a message first.")
        if len(text) > MAX_MESSAGE_CHARS:
            raise EngineError(
                "too_long", f"Messages are limited to {MAX_MESSAGE_CHARS} characters."
            )
        out: list[EventRecord] = []
        seq = self._emit(state, out, "student_message", "student", to=char_id, text=text)
        state["conversations"].setdefault(char_id, []).append(
            {"role": "student", "text": text, "minute": state["clock"], "seq": seq}
        )
        return out

    def record_character_message(
        self, state: dict, char_id: str, text: str, *, label: str, mood: str | None = None
    ) -> list[EventRecord]:
        out: list[EventRecord] = []
        seq = self._emit(state, out, "character_message", char_id, text=text, label=label)
        state["conversations"].setdefault(char_id, []).append(
            {
                "role": "character",
                "text": text,
                "minute": state["clock"],
                "seq": seq,
                "label": label,
            }
        )
        if mood:
            state["moods"][char_id] = mood
        return out

    def finish_conversation_turn(self, state: dict) -> list[EventRecord]:
        """Each exchange costs simulated time (5 minutes)."""
        out: list[EventRecord] = []
        self._advance(state, 5, out)
        return out

    def character_context(self, state: dict, char_id: str) -> dict:
        """What a character is allowed to know right now. Locked restricted facts are excluded,
        so they can never reach the AI model's prompt."""
        char = self.d.character(char_id)
        if char is None:
            raise EngineError("unknown_character", "Unknown character.")
        unlocked = [
            r.fact for r in char.restricted if r.reveal_when and self._eval(r.reveal_when, state)
        ]
        return {
            "knowledge": list(char.knowledge) + unlocked,
            "mood": state["moods"].get(char_id, char.initial_mood),
            "history": state["conversations"].get(char_id, [])[-12:],
        }

    def interpretable_actions(self, state: dict, char_id: str) -> list[Action]:
        return [a for a in self.available_actions(state) if a.via_character == char_id]

    # ------------------------------------------------------------------ submissions & hints
    def submit(self, state: dict, submission_id: str, text: str) -> list[EventRecord]:
        self._ensure_active(state)
        spec = self.d.submission(submission_id)
        if spec is None:
            raise EngineError("unknown_submission", "That deliverable does not exist.")
        text = (text or "").strip()
        if not text:
            raise EngineError("empty", "The submission is empty.")
        if len(text) > MAX_SUBMISSION_CHARS:
            raise EngineError("too_long", "The submission is too long.")
        words = word_count(text)
        previous = state["submissions"].get(submission_id)
        revision = (previous["revision"] + 1) if previous else 1
        out: list[EventRecord] = []
        seq = self._emit(
            state,
            out,
            "submission",
            "student",
            submission_id=submission_id,
            text=text,
            words=words,
            revision=revision,
        )
        state["submissions"][submission_id] = {
            "text": text,
            "words": words,
            "revision": revision,
            "minute": state["clock"],
            "seq": seq,
        }
        meets_length = words >= spec.min_words
        if spec.task_id and spec.task_id in state["tasks"] and meets_length:
            state["tasks"][spec.task_id] = "done"
        if not meets_length:
            self._log(
                state,
                "notice",
                f"'{spec.title}' saved, but it is shorter than the expected {spec.min_words} words.",
            )
        else:
            self._log(state, "submission", f"Submitted '{spec.title}' (revision {revision}).")
        self._advance(state, 10, out)
        return out

    def hints_allowed(self) -> bool:
        return self.mode == "training" and self.settings.hints_available

    def take_hint(self, state: dict) -> tuple[str, list[EventRecord]]:
        self._ensure_active(state)
        if not self.hints_allowed():
            raise EngineError("hints_disabled", "Hints are not available in this mode.")
        for task in self.d.tasks:
            if state["tasks"].get(task.id) != "open":
                continue
            for i, hint in enumerate(task.hints):
                key = f"{task.id}:{i}"
                if key not in state["hints_used"]:
                    state["hints_used"].append(key)
                    out: list[EventRecord] = []
                    self._emit(state, out, "hint", "system", task_id=task.id, text=hint)
                    state["feedback"].append({"minute": state["clock"], "text": f"Hint: {hint}"})
                    return hint, out
        raise EngineError("no_hints", "No more hints are available for your open tasks.")

    # ------------------------------------------------------------------ completion
    def outcome(self, state: dict) -> str:
        for o in self.d.outcomes:
            if self._eval(o.when, state):
                return o.id
        return self.d.outcomes[-1].id  # pragma: no cover - schema guarantees a default

    def finish(self, state: dict) -> tuple[str, list[EventRecord]]:
        self._ensure_active(state)
        outcome_id = self.outcome(state)
        state["finished"] = True
        out: list[EventRecord] = []
        open_required = [
            t.id for t in self.d.tasks if t.required and state["tasks"].get(t.id) == "open"
        ]
        self._emit(
            state, out, "finished", "student", outcome=outcome_id, open_required_tasks=open_required
        )
        return outcome_id, out

    # ------------------------------------------------------------------ student view
    def view(self, state: dict) -> dict:
        d = self.d
        chars = [c for c in d.characters if self._character_present(c.id)]
        return {
            "title": d.title,
            "summary": d.summary,
            "context": d.context.model_dump(),
            "learning_objectives": d.learning_objectives,
            "mode": self.mode,
            "difficulty": self.difficulty,
            "clock": state["clock"],
            "time_limit": state["time_limit"],
            "time_up": state["time_up"],
            "finished": state["finished"],
            "variables": [
                {
                    "id": k,
                    "label": v.label,
                    "value": state["variables"][k],
                    "unit": v.unit,
                    "min": v.min,
                    "max": v.max,
                    "description": v.description,
                }
                for k, v in d.variables.items()
                if v.visible
            ],
            "characters": [
                {
                    "id": c.id,
                    "name": c.name,
                    "role": c.role,
                    "kind": c.kind,
                    "organization": c.organization,
                    "mood": state["moods"].get(c.id, c.initial_mood),
                    "language": c.language,
                }
                for c in chars
            ],
            "inbox": list(reversed(state["inbox"])),
            "conversations": state["conversations"],
            "documents": [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "kind": doc.kind,
                    "body": doc.body,
                    "direction": doc.direction,
                }
                for doc in d.documents
                if doc.id in state["visible_documents"]
            ],
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "required": t.required,
                    "status": state["tasks"][t.id],
                }
                for t in d.tasks
                if t.id in state["tasks"]
            ],
            "actions": [
                {
                    "id": a.id,
                    "label": a.label,
                    "description": a.description,
                    "category": a.category,
                    "requires_justification": a.requires_justification,
                    "duration_minutes": a.duration_minutes,
                    "via_character": a.via_character,
                }
                for a in self.available_actions(state)
            ],
            "submissions": [
                {
                    "id": s.id,
                    "title": s.title,
                    "prompt": s.prompt,
                    "min_words": s.min_words,
                    "direction": s.direction,
                    "language": s.language,
                    "template": s.template,
                    "current": state["submissions"].get(s.id),
                }
                for s in d.submissions
            ],
            "log": list(reversed(state["log"])),
            "feedback": list(reversed(state["feedback"])) if self.mode == "training" else [],
            "hints_available": self.hints_allowed(),
            "fictional_notice": d.context.fictional_notice,
        }


def clone(state: dict) -> dict:
    return copy.deepcopy(state)
