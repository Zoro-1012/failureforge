#!/usr/bin/env bash
#
# Frontend (Playwright) end-to-end test runner.
#
# Boots the FULL stack — including the Next.js frontend — with the offline stub
# diagnosis provider, then runs the Playwright UI tests against it.
#
# Usage:
#   ./scripts/e2e-ui.sh           # build, test, tear down
#   KEEP=1 ./scripts/e2e-ui.sh    # leave the stack running afterwards
#
# Requires: Docker, Node 20+ (for Playwright). The script installs the Chromium
# browser on first run.
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE="docker compose -f docker/docker-compose.yml"
API="${ORCHESTRATOR_URL:-http://localhost:8000}"
WEB="${E2E_BASE_URL:-http://localhost:3000}"
export DIAGNOSIS_PROVIDER=stub

cleanup() {
  if [ "${KEEP:-0}" != "1" ]; then
    echo "==> Tearing down stack"
    $COMPOSE down -v
  fi
}
trap cleanup EXIT

echo "==> Building & starting full stack (stub diagnosis provider)"
$COMPOSE up --build -d

echo "==> Waiting for orchestrator ($API) and frontend ($WEB)"
for i in $(seq 1 40); do
  if curl -sf "$API/health" >/dev/null 2>&1; then break; fi
  [ "$i" = 40 ] && { echo "Orchestrator not healthy" >&2; exit 1; }
  sleep 2
done
for i in $(seq 1 40); do
  if curl -sf "$WEB" >/dev/null 2>&1; then break; fi
  [ "$i" = 40 ] && { echo "Frontend not reachable" >&2; exit 1; }
  sleep 2
done
echo "Stack is up."

echo "==> Installing frontend deps + Chromium"
cd frontend
npm install
npx playwright install --with-deps chromium

echo "==> Running Playwright UI E2E"
E2E_BASE_URL="$WEB" npm run test:e2e
