# Requirements and status

Source: "BRIDGE — Master Software Development Instructions". ✔ = implemented and tested;
◐ = implemented with a documented limitation (see LIMITATIONS.md).

## Functional
| Requirement | Status |
|---|---|
| Accounts, sign-in, roles (student/professor/admin), backend-enforced permissions | ✔ (Supabase sign-in: backend only ◐) |
| Specializations as data; three seeded; admins can add more | ✔ |
| Scenario library, introduction, mode and difficulty selection | ✔ |
| Virtual workplace: inbox, messaging, AI characters, documents, tasks, events, submissions, decisions, resources, timer | ✔ (simulated clock) |
| Reusable state-machine engine: sessions, versions, state, actions, events, consequences, completion, recovery, audit log, idempotency, transactions | ✔ |
| Free-text actions interpreted by AI and validated by the backend | ✔ |
| AI characters with separate contexts, restricted knowledge, structured validated output, fallbacks, timeouts, retries, limits | ✔ (real model not measured ◐) |
| Independent rubric-based assessment with evidence, uncertainty, insufficient-evidence handling, deterministic weighting, injection resistance | ✔ |
| Professor review with retained original and audit history | ✔ |
| Personalised printable report (outcome, scores, strengths, improvements, evidence, decisions & consequences, alternatives, concepts, recommendations) | ✔ (PDF via print ◐) |
| Training vs assessment mode enforced by backend | ✔ |
| International Trade (2), Translation with RTL (2), INFOCOM with simulated reactions (2) | ✔ (content needs specialist review ◐) |
| Competency profiles, 4 difficulty levels, explainable rule-based recommendations | ✔ |
| Approved resources: upload, validation, chunking, retrieval, citations, visibility, versions | ✔ (lexical, not embeddings ◐) |
| Professor: courses, assignments, progress, weaknesses, scenario & rubric editing, resources, export | ✔ |
| Admin: users, specializations, publication, AI provider & limits, usage & cost, audit log, settings | ✔ |
| Evaluation tools for the validation plan | ✔ (pilot not run) |

## Non-functional
| Requirement | Status |
|---|---|
| Security from the start (see SECURITY.md) | ✔ with documented gaps |
| Accessibility | ✔ automated axe scan; manual screen-reader testing not done ◐ |
| Responsive layouts, dark mode | ✔ |
| Mock AI provider for tests/demos, clearly labelled | ✔ |
| Reproducible builds, CI, documentation | ✔ |
| Deployment | ◐ local verified; Docker/cloud prepared, not executed |
