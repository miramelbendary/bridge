# Requirements and project boundaries

The full product brief is the "BRIDGE — Master Software Development Instructions". This file
records the condensed requirements, the boundaries we hold to, and their status.

## Product goal
A formative learning platform where university students practise professional work in simulated
workplaces and receive rubric-based, evidence-backed assessments. **Not** a high-stakes exam system.

## Users and roles
| Role | Phase 1 capability | Full capability (later phases) |
|---|---|---|
| Student | Register, sign in, view/update own profile, choose specialization, list specializations | Simulations, submissions, reports, competency profile, recommendations |
| Professor | Same as student (no extra permissions yet) | Scenarios, rubrics, materials, review/override assessments for *authorized* students only |
| Administrator | List users, change roles, read audit log | Specializations, publication, AI provider config, usage and security monitoring |

## Functional requirements (by phase)
- **FR-1 Authentication** (P1 ✔): email/password (local) or Supabase; server-side verification.
- **FR-2 Authorization** (P1 ✔): RBAC enforced in the backend; ownership checks per resource (from P3).
- **FR-3 Specializations** (P1 ✔): data-driven list; three seeded.
- **FR-4 Simulation engine** (P3): state machine, events, consequences, recovery, audit trail, idempotency.
- **FR-5 AI characters** (P4): isolated contexts, validated structured output, fallbacks, no state writes.
- **FR-6 Assessment** (P5): versioned rubrics, evidence-linked criteria, deterministic weighting, professor review.
- **FR-7 Scenarios** (P6–7): International Trade first; then Translation (with RTL Arabic) and INFOCOM.
- **FR-8 Adaptive learning** (P8): competency profiles with uncertainty, explainable rule-based recommendations, RAG.
- **FR-9 Dashboards** (P9): professor and administrator tools, report export.

## Non-functional requirements
- Security and privacy from the start (see `SECURITY.md`); minimal personal data.
- Accessibility: semantic HTML, labelled inputs, sufficient contrast, keyboard use.
- Responsive desktop/tablet/mobile layouts.
- Reproducible builds (pinned dependencies), CI on every push.
- AI cost controls and a deterministic mock provider (from P4).

## Boundaries (what we will not do)
- No microservices, voice, multiplayer or advanced integrations before the demo definition of done.
- No fabricated research data or effectiveness claims; targets in the brief are targets, not results.
- No real companies, people or student data in scenarios or demos.
- The AI never computes final scores, changes resources, or receives database access.
