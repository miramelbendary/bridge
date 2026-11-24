"""Load and validate scenario files from the `scenarios/` directory."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import yaml

from app.simulation.schema import ScenarioDefinition

DEFAULT_SCENARIO_DIR = Path(
    os.environ.get("BRIDGE_SCENARIO_DIR") or Path(__file__).resolve().parents[3] / "scenarios"
)


def parse_definition(data: dict) -> ScenarioDefinition:
    return ScenarioDefinition.model_validate(data)


def load_file(path: Path) -> ScenarioDefinition:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)  # safe_load: scenario files can never execute code
    return parse_definition(data)


def discover(directory: Path | None = None) -> list[tuple[Path, ScenarioDefinition]]:
    directory = directory or DEFAULT_SCENARIO_DIR
    return [(p, load_file(p)) for p in sorted(directory.glob("*/*.yaml"))]


def content_hash(definition: ScenarioDefinition | dict) -> str:
    data = (
        definition.model_dump(mode="json")
        if isinstance(definition, ScenarioDefinition)
        else definition
    )
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
