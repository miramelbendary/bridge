# User guide

## Students

1. **Register** (or use a demo account) and choose your **specialization** on the dashboard.
2. **Dashboard** shows assignments from your professors, recommended scenarios *with the reasons*,
   simulations in progress and your recent results.
3. **Scenarios** → pick one → read your role, objectives and how you will be assessed → choose:
   - **Training mode**: hints and coaching feedback during the task.
   - **Assessment mode**: no hints; feedback only at the end.
   - **Difficulty** (beginner → professional): less time, smaller budgets, extra events, fewer hints.
4. **The workplace**
   - *Inbox*: emails from colleagues and clients; new ones arrive as events happen.
   - *Messages*: write to any character in your own words. A message can count as a workplace action
     (for example, informing the customer) — the activity feed tells you when it does. Replies are
     labelled when they are offline/scripted.
   - *Documents*: contracts, invoices, briefs, reports. New documents appear when you investigate.
   - *Deliverables*: written work (Arabic deliverables are right-to-left). You can revise until you
     finish; the last version counts.
   - *Decisions*: actions with consequences. Some require your written reasoning — it is assessed.
   - *Situation* meters show budget, trust, risk and other variables; the clock shows simulated time.
5. **Finish & get feedback** creates your report: outcome, overall score, each criterion with the
   evidence from your work, strengths, how to improve, your key decisions and their consequences,
   alternative approaches and course material to revise. Use **Print / save as PDF** to keep it.
6. **Competencies** shows your profile across attempts. One attempt = *low confidence*.

## Professors

- **Teaching → Create a course**, add students by their registered email, and **assign** scenarios
  with a fixed mode and difficulty (and optional due date).
- **Course page**: each student's attempts and averages, the course's **common weaknesses**, CSV
  export.
- **Assessments to review**: open one, read the evidence, then **Correct this score** (a
  justification is required) or **Mark as reviewed**. The original AI assessment is always kept;
  students see the corrected score and your comments. Flagged items (possible manipulation attempts)
  appear with a red badge.
- **Scenarios & rubrics**: edit criterion names, weights (must total 100%) and level descriptors,
  or the full scenario definition (JSON) with server-side validation. Every save is a new version;
  attempts in progress keep their original version. Administrators publish.
- **Course resources**: upload approved `.txt`/`.md` notes. Students see citations in feedback;
  *professors only* material (e.g. answer keys) is never shown to students.

## Administrators

- **AI and platform settings**: mock or Claude provider, messages per session, daily requests per
  user, cost budget per session, open/close registration.
- **Last 7 days**: sessions, completion rate, AI calls, cost, latency, failures and fallbacks.
- **Users**: change roles, deactivate/reactivate accounts (you cannot demote or deactivate yourself).
- **Scenario publication** (draft / published / archived) and **specializations**.
- **Security and audit log**: sign-ins, denied access, role changes, reviews, uploads.
- Command line (from `backend/`): `python -m app.cli create-user --role admin …`,
  `python -m app.cli sync-scenarios`, `python -m app.cli evaluation-report`.
