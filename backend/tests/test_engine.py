"""Deterministic simulation engine: rules, consequences, branching and safety properties."""

from __future__ import annotations

import copy
import random

import pytest

from app.simulation.engine import Engine, EngineError
from app.simulation.loader import DEFAULT_SCENARIO_DIR, discover, load_file

TRADE = load_file(DEFAULT_SCENARIO_DIR / "international_trade" / "delayed-shipment.yaml")
J = "Under CIF the seller missed the shipment date through its own error; Clause 7 applies."


def play(steps, *, difficulty="beginner", mode="training", d=TRADE):
    engine = Engine(d, mode=mode, difficulty=difficulty)
    state, _ = engine.start()
    for action_id, justification in steps:
        engine.perform_action(state, action_id, justification=justification)
    return engine, state


GOOD_PATH = [
    ("review_shipment_documents", ""),
    ("inform_customer_promptly", ""),
    ("ask_supplier_cause", ""),
    ("conclude_supplier_responsible", J),
    ("request_transport_quotes", ""),
    ("negotiate_cost_share", ""),
    ("choose_partial_air", J),
]


def test_good_path_reaches_best_outcome():
    engine, state = play(GOOD_PATH)
    assert state["variables"]["days_late"] == 0
    assert state["variables"]["budget"] == 6000 - 4200 + 2100
    assert engine.outcome(state) == "excellent_resolution"


def test_waiting_path_reaches_late_outcome_and_customer_complains():
    engine, state = play([("request_transport_quotes", ""), ("choose_wait_next_vessel", J)])
    engine._advance(state, 120, [])
    assert "customer_complaint" in state["events_fired"]
    assert engine.outcome(state) == "late_relationship_damaged"


def test_full_air_goes_over_budget():
    engine, state = play([("request_transport_quotes", ""), ("choose_full_air", J)])
    assert state["variables"]["budget"] < 0
    assert engine.outcome(state) == "on_time_over_budget"


def test_informing_customer_prevents_complaint():
    engine, state = play([("inform_customer_promptly", "")])
    engine._advance(state, 300, [])
    assert "customer_complaint" not in state["events_fired"]


def test_decision_requires_justification():
    engine, state = play([("request_transport_quotes", "")])
    with pytest.raises(EngineError) as exc:
        engine.perform_action(state, "choose_partial_air", justification="ok")
    assert exc.value.code == "justification_required"


def test_exclusive_choices_and_preconditions():
    engine, state = play([])
    with pytest.raises(EngineError) as exc:  # quotes not requested yet
        engine.perform_action(state, "choose_partial_air", justification=J)
    assert exc.value.code == "action_unavailable"
    engine.perform_action(state, "request_transport_quotes")
    engine.perform_action(state, "choose_partial_air", justification=J)
    with pytest.raises(EngineError):  # only one transport option
        engine.perform_action(state, "choose_full_air", justification=J)


def test_actions_are_not_repeatable_and_unknown_ids_rejected():
    engine, state = play([("review_shipment_documents", "")])
    with pytest.raises(EngineError):
        engine.perform_action(state, "review_shipment_documents")
    with pytest.raises(EngineError) as exc:
        engine.perform_action(state, "set_budget_to_million")
    assert exc.value.code == "unknown_action"


def test_negotiation_locked_until_responsibility_established():
    engine, state = play([("ask_supplier_cause", "")])
    assert "negotiate_cost_share" not in [a.id for a in engine.available_actions(state)]


def test_variables_are_clamped():
    engine, state = play([])
    state["variables"]["customer_trust"] = 99
    engine.perform_action(state, "inform_customer_promptly")
    assert state["variables"]["customer_trust"] == 100


def test_hints_only_in_training_mode():
    engine, state = play([], mode="training")
    hint, events = engine.take_hint(state)
    assert hint and events[0].kind == "hint"
    engine, state = play([], mode="assessment")
    with pytest.raises(EngineError) as exc:
        engine.take_hint(state)
    assert exc.value.code == "hints_disabled"


def test_training_feedback_hidden_in_assessment_view():
    engine, state = play([("review_shipment_documents", "")], mode="assessment")
    assert engine.view(state)["feedback"] == []
    engine, state = play([("review_shipment_documents", "")], mode="training")
    assert engine.view(state)["feedback"]


def test_hidden_variables_not_exposed_in_view():
    engine, state = play([])
    ids = [v["id"] for v in engine.view(state)["variables"]]
    assert "penalty_risk" not in ids and "budget" in ids


def test_difficulty_changes_budget_and_events():
    _, beginner = play([], difficulty="beginner")
    engine, advanced = play([], difficulty="advanced")
    assert beginner["variables"]["budget"] == 6000
    assert advanced["variables"]["budget"] == 5000
    engine._advance(advanced, 60, [])
    assert "port_strike_warning" in advanced["events_fired"]
    assert "strike_notice" in advanced["visible_documents"]


def test_time_limit_blocks_actions():
    engine, state = play([])
    engine._advance(state, 10_000, [])
    assert state["time_up"]
    assert engine.available_actions(state) == []


def test_finish_is_final():
    engine, state = play([])
    engine.finish(state)
    with pytest.raises(EngineError) as exc:
        engine.perform_action(state, "review_shipment_documents")
    assert exc.value.code == "session_finished"


def test_submission_word_minimum_controls_task_completion():
    engine, state = play([])
    engine.submit(state, "resolution_plan", "too short")
    assert state["tasks"]["submit_plan"] == "open"
    engine.submit(state, "resolution_plan", "word " * 130)
    assert state["tasks"]["submit_plan"] == "done"
    assert state["submissions"]["resolution_plan"]["revision"] == 2


def test_engine_is_deterministic():
    _, a = play(GOOD_PATH)
    _, b = play(GOOD_PATH)
    assert a == b


def test_event_sequence_numbers_are_strictly_increasing():
    engine = Engine(TRADE, mode="training", difficulty="intermediate")
    state, events = engine.start()
    seqs = [e.seq for e in events]
    for step, j in GOOD_PATH:
        seqs += [e.seq for e in engine.perform_action(state, step, justification=j)]
    assert seqs == sorted(seqs) and len(seqs) == len(set(seqs))


def test_locked_character_facts_are_not_in_context_until_unlocked():
    engine, state = play([])
    secret = "submitted the export documents after the carrier's cut-off"
    assert not any(secret in k for k in engine.character_context(state, "jonas")["knowledge"])
    engine.perform_action(state, "ask_supplier_cause")
    assert any(secret in k for k in engine.character_context(state, "jonas")["knowledge"])


@pytest.mark.parametrize("path,definition", discover(), ids=lambda x: getattr(x, "name", ""))
def test_random_playthroughs_never_break_invariants(path, definition):
    """Scenario branching test: random legal play at every difficulty and mode must never raise
    unexpected errors, must keep variables in bounds and must always end in a defined outcome."""
    rng = random.Random(path.name)
    outcome_ids = {o.id for o in definition.outcomes}
    for difficulty in definition.difficulties:
        for mode in ("training", "assessment"):
            for _ in range(15):
                engine = Engine(definition, mode=mode, difficulty=difficulty)
                state, _ = engine.start()
                for _ in range(rng.randint(0, 12)):
                    options = engine.available_actions(state)
                    if not options:
                        break
                    action = rng.choice(options)
                    engine.perform_action(state, action.id, justification=J)
                    if rng.random() < 0.3 and definition.submissions:
                        spec = rng.choice(definition.submissions)
                        engine.submit(state, spec.id, "word " * (spec.min_words + 1))
                for var_id, spec in definition.variables.items():
                    value = state["variables"][var_id]
                    assert spec.min is None or value >= spec.min
                    assert spec.max is None or value <= spec.max
                before = copy.deepcopy(state)
                outcome, _ = engine.finish(state)
                assert outcome in outcome_ids
                assert before["variables"] == state["variables"]


def test_every_specialization_has_scenarios_with_reachable_alternative_outcomes():
    by_spec: dict[str, list] = {}
    for _, d in discover():
        by_spec.setdefault(d.specialization, []).append(d)
    assert set(by_spec) == {"international_trade", "translation", "infocom"}
    for d in (x for items in by_spec.values() for x in items):
        assert len(d.outcomes) >= 3, d.slug
        assert sum(c.weight for c in d.rubric.criteria) == 100
