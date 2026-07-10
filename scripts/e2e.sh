#!/usr/bin/env bash
#
# Backend pipeline end-to-end test runner.
#
# Boots the stack with the offline stub diagnosis provider (no Gemini key needed),
# waits for health, runs the live-stack pytest suite, then tears the stack down.
#
# Usage:
#   ./scripts/e2e.sh           # build, test, tear down
#   KEEP=1 ./scripts/e2e.sh    # leave the stack running afterwards
#
# Requires: Docker, and `pip install pytest httpx` on the host.
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE="docker compose -f docker/docker-compose.yml"
API="${ORCHESTRATOR_URL:-http://localhost:8000}"
export DIAGNOSIS_PROVIDER=stub

cleanup() {
  if [ "${KEEP:-0}" != "1" ]; then
    echo "==> Tearing down stack"
    $COMPOSE down -v
  else
    echo "==> KEEP=1 set; leaving stack running"
  fi
}
trap cleanup EXIT

echo "==> Building & starting stack (stub diagnosis provider)"
# Backend services only; the frontend isn't needed for API-level E2E.
$COMPOSE up --build -d postgres redis app orchestrator

echo "==> Waiting for orchestrator at $API"
for i in $(seq 1 40); do
  if curl -sf "$API/health" >/dev/null 2>&1; then break; fi
  if [ "$i" = 40 ]; then echo "Orchestrator did not become healthy" >&2; exit 1; fi
  sleep 2
done
echo "Orchestrator is up."

echo "==> Running backend pipeline E2E"
E2E_STUB=1 ORCHESTRATOR_URL="$API" python3 -m pytest tests/e2e -v
