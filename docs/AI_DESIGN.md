# AI design

> **Status:** design principles only. No AI code exists yet; integration is Phase 4, assessment
> Phase 5, retrieval Phase 8. This document will be extended as those phases are implemented.

## Principle: hybrid, with deterministic authority
| Deterministic backend code controls | AI may assist with |
|---|---|
| Scenario rules, facts, state transitions, event triggers | Natural conversation in character |
| Resources (budget, time, trust…) and their calculations | Interpreting a free-text action into a *proposed* structured action |
| Permissions, completion conditions | Qualitative feedback against an approved rubric |
| Final and weighted score calculation | Explanations and recommendations |

The AI produces **proposals**; the backend validates and decides. The model never receives
database access, tool execution, or the ability to write authoritative state.

## Planned components (Phase 4)
- `app/ai/providers/`: a provider interface (`generate_structured(prompt, schema, limits)`) with
  implementations for an external API (Anthropic, OpenAI or Gemini; configured server-side) and a
  **deterministic mock provider** for tests and demos without credentials. Mock and fallback
  output will be visibly labelled.
- Character contexts: each character gets only its own persona, knowledge and permitted facts.
  No shared conversation across characters; restricted information is never placed in its prompt.
- Structured output validated with Pydantic; malformed or out-of-policy output is rejected and a
  scripted fallback is used.
- Timeouts, bounded retries, per-user and per-session budgets, token/latency/cost logging
  (`ai_usage_logs` table, added in Phase 4).

## Prompt-injection stance
Student messages, submissions and uploaded documents are **untrusted data**. They are delimited as
data in prompts, never concatenated into instructions, and never able to change scores, state or
permissions, because those are not under the model's control in the first place.

## Assessment (Phase 5)
A separate assessment service, independent of the characters, scores each rubric criterion with an
explanation, evidence references that must point to real recorded actions/submissions (validated by
the backend), weaknesses, improvements and uncertainty. "Insufficient evidence" is distinct from a
low score. Weighted totals are computed by backend code. Professors can override with justification;
the original AI assessment is retained.

## Privacy towards providers
Only the minimum context is sent: no names, emails or student identifiers; pseudonymous session ids.
