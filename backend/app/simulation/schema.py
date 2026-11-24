"""Scenario definition schema.

Scenario files (YAML in `scenarios/`) and professor edits are validated against these models
before they can be stored. Cross-references (ids used in conditions, effects, events, rubric) are
checked too, so a scenario that loads is internally consistent.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.simulation import conditions
from app.simulation.competencies import COMPETENCIES

Difficulty = Literal["beginner", "intermediate", "advanced", "professional"]
DIFFICULTY_ORDER: tuple[str, ...] = ("beginner", "intermediate", "advanced", "professional")
Id = Field(pattern=r"^[a-z][a-z0-9_]{1,59}$")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


def _check_condition(value: Any) -> Any:
    if value is not None:
        conditions.validate(value)
    return value


class Variable(_Model):
    label: str
    initial: float
    min: float | None = None
    max: float | None = None
    unit: str = ""
    visible: bool = True
    description: str = ""


class Effect(_Model):
    var: str
    op: Literal["add", "set"] = "add"
    value: float


class RestrictedFact(_Model):
    fact: str
    # The character may share this fact only once the condition holds (e.g. after negotiation).
    reveal_when: dict | None = None

    @field_validator("reveal_when")
    @classmethod
    def _validate_condition(cls, v: Any) -> Any:
        return _check_condition(v)


class FAQ(_Model):
    keywords: list[str] = Field(min_length=1)
    reply: str


class Character(_Model):
    id: str = Id
    name: str
    role: str
    kind: Literal[
        "manager", "customer", "supplier", "colleague", "journalist", "stakeholder", "client"
    ]
    organization: str
    personality: str
    communication_style: str
    objectives: list[str] = []
    knowledge: list[str] = []
    restricted: list[RestrictedFact] = []
    initial_mood: Literal["calm", "pleased", "neutral", "concerned", "frustrated", "angry"] = (
        "neutral"
    )
    faq: list[FAQ] = []
    fallback_replies: list[str] = Field(min_length=1)
    language: str = "en"
    min_difficulty: Difficulty = "beginner"


class Document(_Model):
    id: str = Id
    title: str
    kind: str = "document"
    body: str
    direction: Literal["ltr", "rtl"] = "ltr"
    initially_visible: bool = True
    min_difficulty: Difficulty = "beginner"


class Task(_Model):
    id: str = Id
    title: str
    description: str
    required: bool = True
    hints: list[str] = []
    initially_visible: bool = True


class InboxMessage(_Model):
    id: str = Id
    sender: str  # character id
    subject: str
    body: str
    min_difficulty: Difficulty = "beginner"


class Action(_Model):
    id: str = Id
    label: str
    description: str
    category: Literal["communication", "decision", "investigation"] = "decision"
    duration_minutes: int = Field(default=15, ge=0, le=24 * 60)
    available_when: dict | None = None
    repeatable: bool = False
    requires_justification: bool = False
    effects: list[Effect] = []
    reveals_documents: list[str] = []
    completes_tasks: list[str] = []
    triggers_events: list[str] = []
    consequence: str = Field(description="What visibly happens, shown to the student.")
    training_feedback: str = ""
    # Free-text interpretation: an action can also be performed by writing to this character.
    via_character: str | None = None
    intent_keywords: list[str] = []
    character_response: str = ""
    # Mutually exclusive decisions, e.g. choose exactly one transport option.
    exclusive_group: str | None = None

    @field_validator("available_when")
    @classmethod
    def _validate_condition(cls, v: Any) -> Any:
        return _check_condition(v)


class EventMessage(_Model):
    sender: str
    subject: str
    body: str


class Event(_Model):
    id: str = Id
    title: str
    at_minute: int | None = None
    when: dict | None = None
    min_difficulty: Difficulty = "beginner"
    message: EventMessage | None = None
    effects: list[Effect] = []
    reveals_documents: list[str] = []
    adds_tasks: list[str] = []
    notification: str = ""

    @field_validator("when")
    @classmethod
    def _validate_condition(cls, v: Any) -> Any:
        return _check_condition(v)


class SubmissionSpec(_Model):
    id: str = Id
    title: str
    prompt: str
    task_id: str | None = None
    min_words: int = Field(default=0, ge=0)
    direction: Literal["ltr", "rtl"] = "ltr"
    language: str = "en"
    template: str = ""


class Outcome(_Model):
    id: str = Id
    title: str
    description: str
    when: dict | None = None

    @field_validator("when")
    @classmethod
    def _validate_condition(cls, v: Any) -> Any:
        return _check_condition(v)


class RubricLevel(_Model):
    score: float = Field(ge=0, le=100)
    label: str
    descriptor: str


class ObjectiveSignal(_Model):
    when: dict
    points: float = Field(ge=-100, le=100)
    description: str

    @field_validator("when")
    @classmethod
    def _validate_condition(cls, v: Any) -> Any:
        return _check_condition(v)


class Criterion(_Model):
    id: str = Id
    name: str
    competency: str
    weight: float = Field(gt=0, le=100)
    description: str
    levels: list[RubricLevel] = Field(min_length=2)
    # Which student evidence is relevant: "actions", "messages", "submission:<id>", "messages:<char>"
    evidence_sources: list[str] = Field(min_length=1)
    # Share of the criterion score that comes from rule-based signals (0 = purely qualitative).
    objective_weight: float = Field(default=0.0, ge=0, le=1)
    objective_base: float = Field(default=50, ge=0, le=100)
    objective_signals: list[ObjectiveSignal] = []
    # Used by the mock assessor and to link weaknesses to concepts and resources.
    expected_concepts: list[str] = []
    concepts_to_revise: list[str] = []

    @field_validator("competency")
    @classmethod
    def _known_competency(cls, v: str) -> str:
        if v not in COMPETENCIES:
            raise ValueError(f"unknown competency {v!r}")
        return v


class Rubric(_Model):
    title: str
    criteria: list[Criterion] = Field(min_length=1)

    @model_validator(mode="after")
    def _weights(self) -> Rubric:
        total = sum(c.weight for c in self.criteria)
        if abs(total - 100) > 0.01:
            raise ValueError(f"rubric weights must sum to 100 (got {total})")
        ids = [c.id for c in self.criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate criterion ids")
        return self


class DifficultySettings(_Model):
    time_limit_minutes: int = Field(ge=30, le=24 * 60)
    hints_available: bool = True
    variable_overrides: dict[str, float] = {}
    description: str = ""


class ScenarioContext(_Model):
    organization: str
    student_role: str
    briefing: str
    fictional_notice: str = "All organisations, people and events in this simulation are fictional."


class ScenarioDefinition(_Model):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,99}$")
    specialization: str
    title: str
    summary: str
    estimated_minutes: int = Field(ge=5, le=600)
    learning_objectives: list[str] = Field(min_length=1)
    context: ScenarioContext
    difficulties: dict[Difficulty, DifficultySettings]
    variables: dict[str, Variable] = {}
    characters: list[Character] = Field(min_length=1)
    documents: list[Document] = []
    tasks: list[Task] = Field(min_length=1)
    initial_inbox: list[InboxMessage] = []
    actions: list[Action] = []
    events: list[Event] = []
    submissions: list[SubmissionSpec] = []
    outcomes: list[Outcome] = Field(min_length=1)
    rubric: Rubric
    alternative_approaches: list[str] = []
    review_status: str = "Draft: requires subject-specialist review before authoritative use."

    @model_validator(mode="after")
    def _cross_references(self) -> ScenarioDefinition:
        errors: list[str] = []

        def unique(kind: str, items: list) -> set[str]:
            ids = [i.id for i in items]
            if len(ids) != len(set(ids)):
                errors.append(f"duplicate {kind} ids")
            return set(ids)

        chars = unique("character", self.characters)
        docs = unique("document", self.documents)
        tasks = unique("task", self.tasks)
        actions = unique("action", self.actions)
        events = unique("event", self.events)
        subs = unique("submission", self.submissions)
        unique("outcome", self.outcomes)
        variables = set(self.variables)

        if self.outcomes[-1].when is not None:
            errors.append("the last outcome must have no condition (default outcome)")
        for d in self.difficulties.values():
            for v in d.variable_overrides:
                if v not in variables:
                    errors.append(f"difficulty override for unknown variable {v!r}")
        for m in self.initial_inbox:
            if m.sender not in chars:
                errors.append(f"inbox message {m.id}: unknown sender {m.sender!r}")

        def check_cond(owner: str, cond: dict | None) -> None:
            if cond is None:
                return
            refs = conditions.referenced_ids(cond)
            for kind, known in (
                ("var", variables),
                ("action_taken", actions),
                ("event_fired", events),
                ("task_done", tasks),
                ("submitted", subs),
            ):
                for ref in refs[kind] - known:
                    errors.append(f"{owner}: condition references unknown {kind} {ref!r}")

        def check_effects(owner: str, effects: list[Effect]) -> None:
            for e in effects:
                if e.var not in variables:
                    errors.append(f"{owner}: effect on unknown variable {e.var!r}")

        for a in self.actions:
            owner = f"action {a.id}"
            check_cond(owner, a.available_when)
            check_effects(owner, a.effects)
            for d in a.reveals_documents:
                if d not in docs:
                    errors.append(f"{owner}: unknown document {d!r}")
            for t in a.completes_tasks:
                if t not in tasks:
                    errors.append(f"{owner}: unknown task {t!r}")
            for ev in a.triggers_events:
                if ev not in events:
                    errors.append(f"{owner}: unknown event {ev!r}")
            if a.via_character and a.via_character not in chars:
                errors.append(f"{owner}: unknown character {a.via_character!r}")
            if a.via_character and not a.intent_keywords:
                errors.append(f"{owner}: via_character actions need intent_keywords")
        for ev in self.events:
            owner = f"event {ev.id}"
            if ev.at_minute is None and ev.when is None:
                errors.append(f"{owner}: needs at_minute or when (or be triggered by an action)")
            check_cond(owner, ev.when)
            check_effects(owner, ev.effects)
            if ev.message and ev.message.sender not in chars:
                errors.append(f"{owner}: unknown sender {ev.message.sender!r}")
            for d in ev.reveals_documents:
                if d not in docs:
                    errors.append(f"{owner}: unknown document {d!r}")
            for t in ev.adds_tasks:
                if t not in tasks:
                    errors.append(f"{owner}: unknown task {t!r}")
        for c in self.characters:
            for r in c.restricted:
                check_cond(f"character {c.id}", r.reveal_when)
        for s in self.submissions:
            if s.task_id and s.task_id not in tasks:
                errors.append(f"submission {s.id}: unknown task {s.task_id!r}")
        for o in self.outcomes:
            check_cond(f"outcome {o.id}", o.when)
        for cr in self.rubric.criteria:
            for sig in cr.objective_signals:
                check_cond(f"criterion {cr.id}", sig.when)
            for src in cr.evidence_sources:
                kind, _, ref = src.partition(":")
                if kind not in ("actions", "messages", "submission"):
                    errors.append(f"criterion {cr.id}: bad evidence source {src!r}")
                elif kind == "submission" and ref not in subs:
                    errors.append(f"criterion {cr.id}: unknown submission {ref!r}")
                elif kind == "messages" and ref and ref not in chars:
                    errors.append(f"criterion {cr.id}: unknown character {ref!r}")
            if cr.objective_weight > 0 and not cr.objective_signals:
                errors.append(f"criterion {cr.id}: objective_weight needs objective_signals")
        if errors:
            raise ValueError("; ".join(errors))
        return self

    # Convenience lookups -------------------------------------------------------------------
    def action(self, action_id: str) -> Action | None:
        return next((a for a in self.actions if a.id == action_id), None)

    def character(self, char_id: str) -> Character | None:
        return next((c for c in self.characters if c.id == char_id), None)

    def event(self, event_id: str) -> Event | None:
        return next((e for e in self.events if e.id == event_id), None)

    def submission(self, sub_id: str) -> SubmissionSpec | None:
        return next((s for s in self.submissions if s.id == sub_id), None)

    def task(self, task_id: str) -> Task | None:
        return next((t for t in self.tasks if t.id == task_id), None)


def difficulty_allows(min_difficulty: str, difficulty: str) -> bool:
    return DIFFICULTY_ORDER.index(difficulty) >= DIFFICULTY_ORDER.index(min_difficulty)
