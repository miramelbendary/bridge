# Architecture

BRIDGE is a **modular monolith**: one FastAPI backend, one Next.js frontend, one relational database
(PostgreSQL in production, SQLite for local runs and tests).

```mermaid
flowchart LR
  B[Browser] -->|pages, Server Actions| N[Next.js server<br/>frontend/]
  N -->|JSON + Bearer token<br/>server-to-server| A[FastAPI API<br/>backend/]
  A --> D[(PostgreSQL / SQLite)]
  A -->|optional, structured output| C[Claude API]
  A -->|default| M[Mock AI provider]
```

The browser never sees the API URL or the access token: it lives in an httpOnly cookie and only the
Next.js server forwards it.

## Backend modules

| Package | Responsibility |
|---|---|
| `app/api/` | HTTP routes only (auth, users, simulation, progress, teach, admin, admin_platform) |
| `app/simulation/` | **Authoritative rules**: scenario schema, condition language, deterministic engine, loader, competency registry |
| `app/ai/` | Provider abstraction (mock, Claude), structured schemas, orchestration: limits, validation, fallbacks, usage logs |
| `app/services/` | Business logic: sessions, scenarios (versions), assessment, progress/recommendations, knowledge (retrieval), access rules, platform settings, demo data, evaluation |
| `app/security/` | Tokens, passwords, role permissions, rate limiting, security headers, auth dependencies |
| `app/models/` | SQLAlchemy models (see DATABASE.md) |

## The core rule: AI proposes, code decides

```mermaid
sequenceDiagram
  participant S as Student
  participant API as Session service
  participant E as Engine (deterministic)
  participant AI as AI provider
  S->>API: message to "Karim": "the shipment is delayed..."
  API->>E: record student message (event E12)
  API->>AI: persona + permitted knowledge + allowed intents + message
  AI-->>API: {reply, mood, student_intent_action_id, confidence}
  API->>API: validate: intent in allowed list? confidence ≥ 0.6? no restricted-fact leak?
  API->>E: perform_action(inform_customer_promptly)  — availability re-checked by the engine
  E-->>API: effects applied (trust +12), events, authored reply
  API->>API: commit state with optimistic lock + idempotency key
```

Budgets, trust, deadlines, outcomes and scores are never written by the AI. A character's
*restricted* facts are not placed in its prompt until the scenario's `reveal_when` condition holds.

## Assessment pipeline

1. Collect evidence from the event log: decisions with justifications, messages, final submissions,
   each with a stable reference (`E<seq>`).
2. Ask the assessor (Claude or mock) for one judgement per rubric criterion.
3. Validate: unknown criteria ignored; level score must be one of the rubric's levels; cited evidence
   must exist and be relevant to the criterion; otherwise the transparent rule-based evaluation is
   used for that criterion and the substitution is flagged.
4. Blend qualitative level with **objective signals** (rule conditions on final state), per the
   criterion's `objective_weight`.
5. Criteria with no evidence are marked *insufficient evidence* and excluded from the weighted total.
6. Weighted overall score computed in Python; report built; prompt-injection patterns flagged for
   professor review.

## Scenarios

YAML files in `scenarios/<specialization>/` are validated by `ScenarioDefinition` (types, ids,
cross-references, rubric weights) and synced into immutable `scenario_versions`. Professors can edit
in the UI; each save is a new version. Sessions reference the exact version they started with.

## Key decisions

| Decision | Rationale |
|---|---|
| Pure engine with no I/O | Every rule unit-testable and reproducible; AI cannot bypass it |
| JSON condition language instead of code | Scenario authors cannot execute code; conditions are validated |
| One append-only event log (instead of separate messages/tasks/submissions tables) | A single ordered evidence source for assessment and audit; state JSON is a derived snapshot |
| Optimistic locking + idempotency keys | Safe retries and concurrent tabs without database-specific locks |
| Mock provider as default | Runs anywhere for free; deterministic tests and demos |
| Structured outputs + server-side validation | AI output is data that must pass checks, never instructions |
| Lexical TF-IDF retrieval | Portable, explainable, no embedding service; pgvector is a later upgrade |
| Code-defined permissions + course membership | Reviewable RBAC; professors see only their students |
| Next.js server actions as backend-for-frontend | Token never in the browser; no CORS from browsers |
