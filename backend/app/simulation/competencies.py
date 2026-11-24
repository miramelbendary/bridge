"""Competency registry. Rubric criteria must map to one of these ids."""

from __future__ import annotations

GENERAL = {
    "knowledge_application": "Academic knowledge application",
    "communication": "Communication",
    "critical_thinking": "Critical thinking",
    "decision_making": "Decision-making",
    "problem_solving": "Problem-solving",
    "time_management": "Time management",
    "negotiation": "Negotiation",
    "professional_ethics": "Professional ethics",
    "professionalism": "Professionalism",
}

SPECIALIZATION = {
    # International Trade
    "commercial_knowledge": "Commercial knowledge",
    "contractual_understanding": "Contractual understanding",
    "financial_awareness": "Financial awareness",
    "risk_management": "Risk management",
    # Translation
    "translation_accuracy": "Translation accuracy",
    "terminology": "Terminology",
    "cultural_adaptation": "Cultural adaptation",
    "language_quality": "Grammar and language quality",
    # INFOCOM
    "crisis_management": "Crisis management",
    "information_verification": "Information verification",
    "media_literacy": "Media literacy",
    "public_communication": "Public communication",
    "reputation_management": "Reputation management",
}

COMPETENCIES: dict[str, str] = {**GENERAL, **SPECIALIZATION}


def label(competency_id: str) -> str:
    return COMPETENCIES.get(competency_id, competency_id.replace("_", " ").capitalize())
