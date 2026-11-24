"""Scenario validation rejects inconsistent or unsafe definitions."""

from __future__ import annotations

import copy

import pytest
import yaml

from app.services.scenarios import ScenarioValidationError, validate_definition
from app.simulation import conditions
from app.simulation.loader import DEFAULT_SCENARIO_DIR

BASE = yaml.safe_load(
    (DEFAULT_SCENARIO_DIR / "international_trade" / "delayed-shipment.yaml").read_text(
        encoding="utf-8"
    )
)


def broken(mutator) -> list[str]:
    data = copy.deepcopy(BASE)
    mutator(data)
    with pytest.raises(ScenarioValidationError) as exc:
        validate_definition(data)
    return exc.value.errors


def test_valid_base():
    assert validate_definition(copy.deepcopy(BASE)).slug == "delayed-shipment"


def test_rubric_weights_must_sum_to_100():
    errs = broken(lambda d: d["rubric"]["criteria"][0].update(weight=5))
    assert any("sum to 100" in e for e in errs)


def test_unknown_variable_in_effect():
    errs = broken(lambda d: d["actions"][0].update(effects=[{"var": "money", "value": 1}]))
    assert any("unknown variable" in e for e in errs)


def test_unknown_reference_in_condition():
    errs = broken(lambda d: d["actions"][0].update(available_when={"action_taken": "nope"}))
    assert any("unknown action_taken" in e for e in errs)


def test_malformed_condition_rejected():
    errs = broken(lambda d: d["actions"][0].update(available_when={"var": "budget", "op": "~"}))
    assert errs


def test_extra_fields_rejected():
    errs = broken(lambda d: d.update(execute="rm -rf /"))
    assert errs


def test_unknown_competency_rejected():
    errs = broken(lambda d: d["rubric"]["criteria"][0].update(competency="telepathy"))
    assert any("competency" in e for e in errs)


def test_last_outcome_must_be_default():
    errs = broken(lambda d: d["outcomes"][-1].update(when={"minute_gte": 1}))
    assert any("default outcome" in e for e in errs)


def test_condition_language_has_no_code_execution():
    with pytest.raises(conditions.ConditionError):
        conditions.validate({"python": "__import__('os')"})
    state = {
        "variables": {"x": 5},
        "actions_taken": [],
        "events_fired": [],
        "tasks": {},
        "submissions": {},
        "clock": 0,
    }
    assert conditions.evaluate(
        {"all": [{"var": "x", "op": ">=", "value": 5}, {"not": {"action_taken": "a"}}]},
        state,
        mode="training",
        difficulty="beginner",
    )
