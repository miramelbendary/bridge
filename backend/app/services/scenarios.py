"""Scenario catalogue: syncing scenario files, immutable versions, publication."""

from __future__ import annotations

import uuid
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.scenario import Scenario, ScenarioVersion
from app.models.specialization import Specialization
from app.models.user import User
from app.simulation import loader
from app.simulation.schema import ScenarioDefinition


class ScenarioValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


@lru_cache(maxsize=256)
def _parse_cached(version_id: str, content_hash: str, payload: str) -> ScenarioDefinition:
    import json

    return loader.parse_definition(json.loads(payload))


def definition_of(version: ScenarioVersion) -> ScenarioDefinition:
    import json

    return _parse_cached(str(version.id), version.content_hash, json.dumps(version.definition))


def validate_definition(data: dict) -> ScenarioDefinition:
    try:
        return loader.parse_definition(data)
    except ValidationError as exc:
        errors = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"])
            errors.append(f"{loc}: {err['msg']}" if loc else err["msg"])
        raise ScenarioValidationError(errors) from None


def _specialization(db: Session, code: str) -> Specialization:
    spec = db.scalar(select(Specialization).where(Specialization.code == code))
    if spec is None:
        raise ScenarioValidationError([f"unknown specialization {code!r}"])
    return spec


def save_version(
    db: Session,
    definition: ScenarioDefinition,
    *,
    author: User | None,
    change_note: str = "",
    publish: bool | None = None,
) -> tuple[Scenario, ScenarioVersion, bool]:
    """Store `definition` as a new version if its content changed. Returns (scenario, version,
    created). Existing sessions keep the version they started on."""
    spec = _specialization(db, definition.specialization)
    data = definition.model_dump(mode="json")
    digest = loader.content_hash(data)
    scenario = db.scalar(select(Scenario).where(Scenario.slug == definition.slug))
    if scenario is None:
        scenario = Scenario(
            slug=definition.slug,
            specialization_id=spec.id,
            status="draft",
            created_by_id=author.id if author else None,
        )
        db.add(scenario)
        db.flush()
    elif scenario.specialization_id != spec.id:
        raise ScenarioValidationError(["the specialization of an existing scenario cannot change"])

    current = scenario.current_version
    if current is not None and current.content_hash == digest:
        if publish is not None:
            scenario.status = "published" if publish else scenario.status
        return scenario, current, False

    number = (
        db.scalar(
            select(func.max(ScenarioVersion.version)).where(
                ScenarioVersion.scenario_id == scenario.id
            )
        )
        or 0
    ) + 1
    version = ScenarioVersion(
        scenario_id=scenario.id,
        version=number,
        definition=data,
        content_hash=digest,
        change_note=change_note[:500],
        created_by_id=author.id if author else None,
    )
    db.add(version)
    db.flush()
    scenario.current_version_id = version.id
    scenario.current_version = version
    if publish:
        scenario.status = "published"
    return scenario, version, True


def sync_from_files(
    db: Session, directory: Path | None = None, *, publish: bool = True
) -> list[str]:
    """Load every scenario file; create new versions for changed files. Idempotent."""
    report = []
    for path, definition in loader.discover(directory):
        scenario, version, created = save_version(
            db, definition, author=None, change_note=f"Synced from {path.name}", publish=publish
        )
        report.append(f"{scenario.slug}: v{version.version} ({'new' if created else 'unchanged'})")
    return report


def list_scenarios(db: Session, *, include_unpublished: bool) -> list[Scenario]:
    query = select(Scenario).order_by(Scenario.slug)
    if not include_unpublished:
        query = query.where(Scenario.status == "published")
    return [s for s in db.scalars(query).unique() if s.current_version is not None]


def get_by_slug(db: Session, slug: str) -> Scenario | None:
    return db.scalar(select(Scenario).where(Scenario.slug == slug))


def summary(scenario: Scenario) -> dict:
    d = definition_of(scenario.current_version)  # type: ignore[arg-type]
    return {
        "id": str(scenario.id),
        "slug": scenario.slug,
        "status": scenario.status,
        "version": scenario.current_version.version,  # type: ignore[union-attr]
        "specialization": {
            "code": scenario.specialization.code,
            "name": scenario.specialization.name,
        },
        "title": d.title,
        "summary": d.summary,
        "estimated_minutes": d.estimated_minutes,
        "difficulties": list(d.difficulties.keys()),
        "competencies": sorted({c.competency for c in d.rubric.criteria}),
    }


def detail(scenario: Scenario) -> dict:
    d = definition_of(scenario.current_version)  # type: ignore[arg-type]
    base = summary(scenario)
    base.update(
        {
            "learning_objectives": d.learning_objectives,
            "context": d.context.model_dump(),
            "difficulty_settings": {
                k: {
                    "time_limit_minutes": v.time_limit_minutes,
                    "hints_available": v.hints_available,
                    "description": v.description,
                }
                for k, v in d.difficulties.items()
            },
            "characters": [
                {"name": c.name, "role": c.role, "organization": c.organization, "kind": c.kind}
                for c in d.characters
            ],
            "rubric": [
                {"name": c.name, "weight": c.weight, "competency": c.competency}
                for c in d.rubric.criteria
            ],
            "review_status": d.review_status,
        }
    )
    return base


def version_by_id(db: Session, version_id: uuid.UUID) -> ScenarioVersion | None:
    return db.get(ScenarioVersion, version_id)
