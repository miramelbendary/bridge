# Roadmap

Status legend: **Done** = implemented and verified by automated tests and/or a recorded manual run.
"Not verified" items are listed explicitly — see `docs/LIMITATIONS.md`.

| # | Phase | Status | Verification |
|---|---|---|---|
| 1 | Project foundations | Done | 42 tests at the time; live API + browser check |
| 2 | Application interface | Done | Next.js build (20 routes), Playwright journeys, axe scan |
| 3 | Core simulation engine | Done | Engine unit tests + random branch exploration of all 6 scenarios |
| 4 | AI integration | Done (mock verified; Claude provider tested with stubs only) | AI tests incl. invalid intents, leaks, failures, limits |
| 5 | Assessment engine | Done | Evidence validation, weighting, injection, review tests |
| 6 | International Trade MVP | Done | Full journey in browser and Playwright |
| 7 | Translation and INFOCOM | Done | RTL test, branch exploration, schema validation |
| 8 | Adaptive learning (+ retrieval) | Done (lexical retrieval, not pgvector) | Competency/recommendation/resource tests |
| 9 | Professor and admin dashboards | Done | API tests + Playwright review/admin journeys + manual browser run |
| 10 | Testing, security and optimization | Done for the defined suite | 121 backend + 6 e2e tests; see TESTING.md |
| 11 | Deployment and final delivery | Partly | One-command local start verified from a clean copy; Docker and cloud hosting written but not run |

## Definition of done for a university demonstration

| Requirement | Status |
|---|---|
| Authentication and authorization work | ✔ |
| All three specializations available | ✔ (2 scenarios each) |
| At least one complete scenario per specialization | ✔ |
| Students complete meaningful professional tasks | ✔ |
| AI characters respect scenario constraints | ✔ enforced structurally; real-model behaviour not yet evaluated with a key |
| Decisions produce valid consequences | ✔ deterministic engine |
| Reports contain verifiable evidence | ✔ evidence refs validated against the event log |
| Student progress saved | ✔ |
| Recommendations explainable | ✔ reasons shown |
| Professors can review assessments | ✔ with audit trail |
| Critical workflows have automated tests | ✔ |
| Security limitations documented | ✔ SECURITY.md, LIMITATIONS.md |
| Reproducible run instructions | ✔ start scripts verified from a clean copy |

## Before a real pilot (not started)

1. Subject-specialist review of all six scenarios and rubrics.
2. Evaluate the Claude provider with real keys: character role adherence, assessment agreement with
   human graders (see EVALUATION.md), latency and cost.
3. Run the backend test suite on PostgreSQL in CI (configured) and test the Docker stack.
4. Supabase (or university SSO) sign-in on the frontend; email verification and password reset.
5. Data retention/deletion controls and a privacy review; ethics approval for the pilot study.

## Possible later work
Embedding-based retrieval with pgvector; more scenarios; voice; multiplayer; LMS integration.
