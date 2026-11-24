#!/usr/bin/env bash
# BRIDGE one-command local start (macOS / Linux).   Run:  ./start.sh
# First run creates a virtual environment, installs dependencies, creates a local SQLite database
# with demo data and builds the frontend. Requires Python 3.12+ and Node.js 20.9+.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
step() { printf '\n==> %s\n' "$1"; }
fail() { printf '\nERROR: %s\n' "$1" >&2; exit 1; }

PY=""
for c in python3.14 python3.13 python3.12 python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
[ -n "$PY" ] || fail "Python 3.12 or newer is required (https://www.python.org/downloads/)."
command -v node >/dev/null 2>&1 || fail "Node.js 20.9+ is required (https://nodejs.org/)."
[ "$(node -p 'process.versions.node.split(".")[0]')" -ge 20 ] || fail "Node.js 20.9+ is required."

VENV="$BACKEND/.venv"
VPY="$VENV/bin/python"
if [ ! -x "$VPY" ]; then
  step "Creating Python virtual environment"
  "$PY" -m venv "$VENV"
fi
if [ ! -f "$VENV/.bridge-installed" ] || [ "$BACKEND/requirements.lock" -nt "$VENV/.bridge-installed" ]; then
  step "Installing backend dependencies (first run takes a minute)"
  "$VPY" -m pip install --quiet --upgrade pip
  "$VPY" -m pip install --quiet -r "$BACKEND/requirements.lock"
  "$VPY" -m pip install --quiet --no-deps -e "$BACKEND"
  touch "$VENV/.bridge-installed"
fi

if [ ! -f "$BACKEND/.env" ]; then
  step "Creating backend/.env (local SQLite database, offline mock AI)"
  SECRET="$("$VPY" -c 'import secrets; print(secrets.token_urlsafe(48))')"
  cat > "$BACKEND/.env" <<EOF
ENVIRONMENT=development
DATABASE_URL=sqlite:///./bridge_local.db
AUTH_PROVIDER=local
LOCAL_JWT_SECRET=$SECRET
CORS_ORIGINS=http://localhost:3000
# AI: "mock" works offline for free. To use Claude, set AI_PROVIDER=anthropic and add your key:
AI_PROVIDER=mock
ANTHROPIC_API_KEY=
EOF
fi

step "Preparing the database and scenarios"
(cd "$BACKEND" && "$VPY" -m app.cli setup)

cd "$FRONTEND"
if [ ! -d node_modules ]; then
  step "Installing frontend dependencies (first run takes a minute)"
  npm ci --no-audit --no-fund
fi
[ -f .env.local ] || printf 'BRIDGE_API_URL=http://127.0.0.1:8000\nBRIDGE_DEMO_MODE=1\n' > .env.local
if [ ! -f .next/BUILD_ID ] || [ -n "$(find src -newer .next/BUILD_ID -type f -print -quit)" ]; then
  step "Building the frontend"
  NEXT_TELEMETRY_DISABLED=1 npm run build
fi

step "Starting BRIDGE"
(cd "$BACKEND" && exec "$VPY" -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000) &
API_PID=$!
trap 'kill $API_PID 2>/dev/null; echo "BRIDGE stopped."' EXIT INT TERM
sleep 3
echo
echo "  BRIDGE is running:  http://localhost:3000"
echo "  Demo logins (password bridge-demo-2026):"
echo "    demo.student@example.com · demo.professor@example.com · demo.admin@example.com"
echo "  Press Ctrl+C to stop."
if [ -z "${BRIDGE_NO_BROWSER:-}" ]; then
  (command -v open >/dev/null && open http://localhost:3000) || (command -v xdg-open >/dev/null && xdg-open http://localhost:3000) || true
fi
NEXT_TELEMETRY_DISABLED=1 npm run start -- -p 3000
