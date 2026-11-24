# Running BRIDGE and sharing it with others

## What your friends need

- **Python 3.12 or newer** — <https://www.python.org/downloads/> (on Windows tick *Add python.exe to PATH*)
- **Node.js 20.9 or newer (LTS)** — <https://nodejs.org/>
- About 1.5 GB of free disk space for dependencies.

No database server, Docker or API key is required for the default setup.

## Option 1 — GitHub (recommended)

You (once):

```bash
git remote add origin https://github.com/<your-account>/bridge.git
git push -u origin main
```

Make the repository private and invite your friends as collaborators, or make it public.
Pushing also runs the CI checks (backend tests on PostgreSQL, frontend build, end-to-end tests).

Your friends:

```bash
git clone https://github.com/<your-account>/bridge.git C:\bridge
```

then double-click `C:\bridge\start.cmd` (Windows) or run `./start.sh` (macOS/Linux).

## Option 2 — a zip file

Create a clean zip of the committed project (no installed dependencies, no database, no secrets):

```bash
git archive --format=zip -o bridge.zip HEAD
```

Send `bridge.zip`. Your friends unzip it to a **short path** (for example `C:\bridge`) and run
`start.cmd` / `./start.sh`. Do not zip the folder by hand: it would include `node_modules`,
`.venv`, your local database and your `backend/.env` secrets.

## Option 3 — Docker (runs PostgreSQL too)

Requires Docker Desktop.

```bash
cp .env.example .env        # set POSTGRES_PASSWORD and LOCAL_JWT_SECRET
docker compose up --build
```

Open <http://localhost:3000>. Demo accounts are created automatically in development mode.
*Note: the Docker files are provided but were not run during development (Docker was not available
on the build machine) — see LIMITATIONS.md.*

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Student | `demo.student@example.com` | `bridge-demo-2026` |
| Second student (has one finished attempt) | `demo.student2@example.com` | `bridge-demo-2026` |
| Professor | `demo.professor@example.com` | `bridge-demo-2026` |
| Administrator | `demo.admin@example.com` | `bridge-demo-2026` |

These are fictional, local-only accounts. Anyone can also register a new student account.

## Using the real Claude API (optional)

Edit `backend/.env`:

```
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=<your key>
```

Restart, then in **Admin → AI and platform settings** choose *Anthropic Claude API* and set limits.
Never commit or send your `backend/.env` file — each person should use their own key.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Python 3.12 or newer is required" | Install Python and tick *Add to PATH*, then open a new terminal. |
| `DLL load failed … filename or extension is too long` (Windows) | Move the folder to a short path like `C:\bridge`, delete `backend\.venv`, run again. |
| Port 3000 or 8000 already in use | Close the other program, or stop a previous BRIDGE window. |
| Start over with a fresh database | Stop BRIDGE, delete `backend/bridge_local.db`, start again. |
| Changed the code and want a rebuild | The script rebuilds the frontend automatically when files in `frontend/src` change. |
