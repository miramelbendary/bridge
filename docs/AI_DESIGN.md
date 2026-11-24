# AI design

## Principle
Deterministic code owns scenario facts, rules, resources, permissions, events, completion and final
scores. AI produces **natural language and proposals** that are validated before use.

## Providers
| Provider | When | Behaviour |
|---|---|---|
| `mock` (default) | No key needed | Characters reply from authored FAQ lines and fallback lines; intents recognised by scenario `intent_keywords`; assessment = rubric concept coverage + evidence selection. Deterministic. Labelled "offline" in the UI and `is_mock` in data. |
| `anthropic` | `AI_PROVIDER=anthropic` + `ANTHROPIC_API_KEY`, selected by an admin | Claude via `client.messages.parse(..., output_format=<Pydantic model>)`; default model `claude-opus-5-5` (configurable `AI_MODEL`); effort `low` for character turns, `medium` for assessment; 2 SDK retries; timeout `AI_TIMEOUT_SECONDS`. |

## Characters
- Each character has its own persona, objectives, **knowledge** (facts it may state) and
  **restricted** facts with `reveal_when` conditions. Locked facts are never in the prompt.
- Conversation context is per character (last 10 turns), never shared between characters.
- Output schema: `reply`, `mood`, `student_intent_action_id`, `intent_confidence`.
- Backend checks: intent must be one of the currently available actions linked to that character and
  confidence ≥ 0.6; the engine re-validates availability; replies sharing a 5-word sequence with a
  locked fact are replaced by a scripted line (`blocked_restricted_fact`).
- When an accepted intent has an authored `character_response`, that authored text is shown (so
  authoritative facts come from the scenario, not the model).
- Assessment mode prompt forbids solving tasks or recommending options.

## Assessment
See ARCHITECTURE.md → Assessment pipeline. The assessor sees the rubric, evidence items (as data
inside `<evidence>`), and approved *student-visible* course passages. Students' text is never treated
as instructions; injection-like text sets a flag and routes the assessment to professor review.

## Reliability and cost controls
| Control | Default (env) — admin-editable |
|---|---|
| AI messages per session | 60 (`AI_MAX_MESSAGES_PER_SESSION`) |
| AI requests per user per day | 300 (`AI_DAILY_REQUESTS_PER_USER`) |
| Cost budget per session | USD 1.00 (`AI_SESSION_BUDGET_USD`) |
| Timeout | 45 s (`AI_TIMEOUT_SECONDS`) |

When a limit is reached, the session continues with labelled scripted replies. Any provider error,
refusal, truncated or malformed output → labelled fallback (characters) or the mock evaluator
(assessment, flagged). Every call is logged (`ai_usage_logs`) with tokens, latency, estimated cost
(from list prices in `anthropic_provider.PRICES`) and error codes — never prompts or student text.

## Privacy towards the provider
Prompts contain scenario content and the student's simulation text only: no names, emails or user
ids.

## Fictional vs verified content
All scenario organisations, people and figures are fictional (`fictional_notice`). Each scenario
carries a `review_status` stating that professional facts and rubrics need subject-specialist
review. Sample teaching notes are labelled as samples.
