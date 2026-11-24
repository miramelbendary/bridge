"""A tiny, safe condition language for scenario rules (no `eval`, no code from scenario files).

A condition is a JSON object with exactly one of these keys:

    {"all": [cond, ...]}            every condition holds
    {"any": [cond, ...]}            at least one holds
    {"not": cond}                   negation
    {"var": "budget", "op": ">=", "value": 1000}
    {"action_taken": "inform_customer"}
    {"event_fired": "complaint"}
    {"task_done": "review_documents"}
    {"submitted": "resolution_plan"}
    {"minute_gte": 120}             simulated clock >= 120 minutes
    {"difficulty_in": ["advanced", "professional"]}
    {"mode": "training"}
"""

from __future__ import annotations

from typing import Any

OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
}

LEAF_KEYS = {
    "var",
    "action_taken",
    "event_fired",
    "task_done",
    "submitted",
    "minute_gte",
    "difficulty_in",
    "mode",
}
COMPOSITE_KEYS = {"all", "any", "not"}


class ConditionError(ValueError):
    pass


def validate(cond: Any, *, path: str = "condition") -> None:
    """Raise ConditionError if `cond` is not a well-formed condition."""
    if not isinstance(cond, dict):
        raise ConditionError(f"{path}: must be an object")
    keys = set(cond)
    head = keys & (LEAF_KEYS | COMPOSITE_KEYS)
    if len(head) != 1:
        raise ConditionError(f"{path}: needs exactly one of {sorted(LEAF_KEYS | COMPOSITE_KEYS)}")
    (key,) = head
    if key in ("all", "any"):
        if keys != {key} or not isinstance(cond[key], list) or not cond[key]:
            raise ConditionError(f"{path}.{key}: must be a non-empty list")
        for i, sub in enumerate(cond[key]):
            validate(sub, path=f"{path}.{key}[{i}]")
    elif key == "not":
        if keys != {"not"}:
            raise ConditionError(f"{path}: 'not' takes no siblings")
        validate(cond["not"], path=f"{path}.not")
    elif key == "var":
        if keys != {"var", "op", "value"} or cond["op"] not in OPS:
            raise ConditionError(f"{path}: var conditions need 'op' in {list(OPS)} and 'value'")
        if not isinstance(cond["value"], int | float):
            raise ConditionError(f"{path}: var value must be a number")
    elif key == "minute_gte":
        if keys != {key} or not isinstance(cond[key], int):
            raise ConditionError(f"{path}: minute_gte must be an integer")
    elif key == "difficulty_in":
        if keys != {key} or not isinstance(cond[key], list):
            raise ConditionError(f"{path}: difficulty_in must be a list")
    elif keys != {key} or not isinstance(cond[key], str):
        raise ConditionError(f"{path}: {key} must be a string id")


def referenced_ids(cond: Any) -> dict[str, set[str]]:
    """Collect ids referenced by a condition (used to validate scenario cross-references)."""
    out: dict[str, set[str]] = {
        "var": set(),
        "action_taken": set(),
        "event_fired": set(),
        "task_done": set(),
        "submitted": set(),
    }

    def walk(c: Any) -> None:
        if not isinstance(c, dict):
            return
        for k in ("all", "any"):
            for sub in c.get(k, []):
                walk(sub)
        if "not" in c:
            walk(c["not"])
        for k in out:
            if k in c and isinstance(c[k], str):
                out[k].add(c[k])

    walk(cond)
    return out


def evaluate(cond: Any | None, state: dict, *, mode: str, difficulty: str) -> bool:
    """Evaluate a validated condition against session state. `None` means "always true"."""
    if cond is None:
        return True
    if "all" in cond:
        return all(evaluate(c, state, mode=mode, difficulty=difficulty) for c in cond["all"])
    if "any" in cond:
        return any(evaluate(c, state, mode=mode, difficulty=difficulty) for c in cond["any"])
    if "not" in cond:
        return not evaluate(cond["not"], state, mode=mode, difficulty=difficulty)
    if "var" in cond:
        value = state["variables"].get(cond["var"])
        return value is not None and OPS[cond["op"]](value, cond["value"])
    if "action_taken" in cond:
        return cond["action_taken"] in state["actions_taken"]
    if "event_fired" in cond:
        return cond["event_fired"] in state["events_fired"]
    if "task_done" in cond:
        return state["tasks"].get(cond["task_done"]) == "done"
    if "submitted" in cond:
        return cond["submitted"] in state["submissions"]
    if "minute_gte" in cond:
        return state["clock"] >= cond["minute_gte"]
    if "difficulty_in" in cond:
        return difficulty in cond["difficulty_in"]
    if "mode" in cond:
        return mode == cond["mode"]
    raise ConditionError(f"unknown condition: {cond!r}")
