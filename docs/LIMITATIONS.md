# Limitations and open issues

## Not verified on this build machine
- **PostgreSQL**: tests ran on SQLite; PostgreSQL DDL was rendered offline; CI runs the suite on
  PostgreSQL once the repository is pushed.
- **Docker** (`docker-compose.yml`, both Dockerfiles): written, never built.
- **Claude API**: the provider is implemented per the official SDK and tested with stubs. Real-model
  role adherence, assessment quality, latency and cost have not been measured.
- **`start.sh`** on macOS/Linux (the Windows `start.ps1` was verified from a clean copy).
- **Supabase** sign-in: backend verification only; the frontend supports email/password (local).

## The mock evaluator is a demonstration tool
It scores by rubric *concept coverage* in the student's text and by rule-based signals. It can
over-credit text that mentions concepts without applying them, and it cannot judge Arabic
translation quality. Every mock assessment is labelled as such and can be corrected by a professor.
Use the Claude provider plus professor review for anything beyond demonstrations.

## Educational content
- Six scenarios are drafts written for demonstration. Commercial, legal, linguistic and media facts
  and all rubrics **require subject-specialist review** before authoritative use.
- Sample teaching notes are placeholders to be replaced with approved course material.
- No pilot has been run; no educational-effectiveness claim can be made (see EVALUATION.md).

## Product gaps
- Retrieval is lexical (TF-IDF), not embedding-based (pgvector not used yet).
- Timed events use a *simulated* clock advanced by actions, not wall-clock time.
- Characters cannot be given new knowledge mid-scenario except through `reveal_when` rules.
- No in-app notifications/email, no LMS integration, no account deletion/export endpoints.
- Report PDF export is via the browser's print-to-PDF.
- Frontend has no Content-Security-Policy header yet.

## Before a real university pilot
Privacy impact assessment and ethics approval; data retention and deletion controls; SSO or Supabase
sign-in with email verification; independent security review; subject-specialist content review;
measured AI-vs-human grading agreement on real student work.

## Windows path length
Very long folder paths break loading compiled Python/Node modules on Windows. Keep the project at
a short path (e.g. `C:\bridge`).
