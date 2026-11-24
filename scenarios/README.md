# Scenarios

Each YAML file is one scenario, validated against `backend/app/simulation/schema.py` and loaded into
the database as an immutable version (`python -m app.cli sync-scenarios`, also run by `setup` and the
start scripts). Validate with `python -m app.cli check-scenarios`.

| File | Specialization | Title |
|---|---|---|
| `international_trade/delayed-shipment.yaml` | International Trade | Delayed International Shipment |
| `international_trade/freight-cost-increase.yaml` | International Trade | Unexpected Freight Cost Increase |
| `translation/demanding-client.yaml` | Translation | Demanding International Client |
| `translation/conflicting-requirements.yaml` | Translation | Conflicting Translation Requirements |
| `infocom/media-crisis.yaml` | INFOCOM | Corporate Media Crisis |
| `infocom/misinformation-response.yaml` | INFOCOM | Misinformation and Public Response |

## Anatomy
- `context`, `learning_objectives`, `difficulties` (time limit, hints, variable overrides)
- `variables` (budget, trust, risk…; `visible: false` hides one from students)
- `characters` (persona, objectives, `knowledge`, `restricted` facts with `reveal_when`, `faq`,
  `fallback_replies`) — the AI only ever sees knowledge and unlocked facts
- `documents`, `tasks` (with `hints`), `initial_inbox`
- `actions`: effects, documents revealed, tasks completed, `available_when`, `exclusive_group`,
  `requires_justification`, `consequence`, `training_feedback`, and optional `via_character` +
  `intent_keywords` + `character_response` so the action can be performed by writing to someone
- `events`: `at_minute` and/or `when` conditions, messages, effects, notifications
- `submissions` (`direction: rtl` for Arabic), `outcomes` (first match wins; last is the default)
- `rubric`: criteria with weights summing to 100, levels, evidence sources, objective signals,
  concepts to revise

Conditions use a small JSON language (`all`, `any`, `not`, `var`/`op`/`value`, `action_taken`,
`event_fired`, `task_done`, `submitted`, `minute_gte`, `difficulty_in`, `mode`) — no code.

All organisations and people must be fictional, and professional facts must be reviewed by a subject
specialist before use. In YAML inline maps (`{ … }`), quote any text containing commas or colons.
