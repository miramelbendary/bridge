#!/usr/bin/env bash
# Run every check CI runs (except the PostgreSQL job, unless TEST_DATABASE_URL is set).
# Usage: scripts/check.sh   (from the repository root; works in Git Bash on Windows)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Backend: lint"
cd "$ROOT/backend"
ruff check .
ruff format --check .

echo "==> Backend: tests (${TEST_DATABASE_URL:-SQLite})"
pytest

echo "==> Frontend: lint, typecheck, build"
cd "$ROOT/frontend"
npm run lint
npm run typecheck
npm run build

echo "All checks passed."
