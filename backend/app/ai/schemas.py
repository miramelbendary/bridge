"""Structured AI inputs and outputs. AI output is validated against these before use, and the
backend applies further policy checks (allowed intents, evidence references, score levels)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

Mood = Literal["calm", "pleased", "neutral", "concerned", "frustrated", "angry"]
Uncertainty = Literal["low", "medium", "high"]


# ---------------------------------------------------------------- character conversation
class CharacterReply(BaseModel):
    reply: str = Field(min_length=1, max_length=1500)
    mood: Mood = "neutral"
    # The id of ONE allowed action the student's message clearly performs, or null.
    student_intent_action_id: str | None = None
    intent_confidence: float = Field(default=0.0, ge=0, le=1)


@dataclass
class IntentOption:
    action_id: str
    label: str
    description: str
    keywords: list[str]


@dataclass
class CharacterTurnRequest:
    scenario_title: str
    scenario_context: str
    student_role: str
    character_id: str
    character_name: str
    character_role: str
    organization: str
    personality: str
    communication_style: str
    objectives: list[str]
    knowledge: list[str]
    language: str
    mood: str
    mode: str
    history: list[dict]  # [{role: student|character, text}]
    student_message: str
    intent_options: list[IntentOption]
    faq: list[dict] = field(default_factory=list)
    fallback_replies: list[str] = field(default_factory=list)
    turn_index: int = 0


# ---------------------------------------------------------------- assessment
class CriterionJudgement(BaseModel):
    criterion_id: str
    level_score: float | None = Field(
        default=None, description="One of the rubric level scores, or null if insufficient evidence"
    )
    insufficient_evidence: bool = False
    explanation: str = Field(max_length=2000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=8)
    weaknesses: list[str] = Field(default_factory=list, max_length=6)
    improvements: list[str] = Field(default_factory=list, max_length=6)
    uncertainty: Uncertainty = "medium"


class AssessmentJudgement(BaseModel):
    criteria: list[CriterionJudgement]
    overall_feedback: str = Field(max_length=3000)
    strengths: list[str] = Field(default_factory=list, max_length=6)
    possible_manipulation_detected: bool = False


@dataclass
class EvidenceItem:
    ref: str  # "E<seq>"
    kind: str  # action | student_message | submission
    summary: str
    text: str
    target: str = ""  # character id for messages, submission id for submissions


@dataclass
class CriterionSpec:
    id: str
    name: str
    description: str
    levels: list[dict]
    evidence_sources: list[str]
    expected_concepts: list[str]
    concepts_to_revise: list[str]


@dataclass
class AssessmentRequest:
    scenario_title: str
    specialization: str
    learning_objectives: list[str]
    outcome_title: str
    mode: str
    criteria: list[CriterionSpec]
    evidence: list[EvidenceItem]
    references: list[dict] = field(default_factory=list)  # approved resource passages


@dataclass
class Usage:
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    is_mock: bool = False


class AIProviderError(Exception):
    """Timeout, refusal, malformed output or any provider failure. Callers fall back."""
