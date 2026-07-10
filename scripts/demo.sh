#!/usr/bin/env bash
#
# FailureForge end-to-end demo / dataset seeder.
#
# Runs every failure scenario through the orchestrator, runs AI diagnosis on each
# captured incident, then prints the benchmark evaluation. Use it to seed a
# dataset or to drive a live demo.
#
# Prerequisites: the stack is running (`make up`). For the diagnosis step, set
# GEMINI_API_KEY in your .env (otherwise diagnoses are skipped with a warning).
#
# Usage:
#   ./scripts/demo.sh            # one round of all four scenarios
#   ROUNDS=3 ./scripts/demo.sh   # three rounds (more support for metrics)
#   API=http://localhost:8000 ./scripts/demo.sh
set -euo pipefail

API="${API:-http://localhost:8000}"
ROUNDS="${ROUNDS:-1}"
SCENARIOS=(redis_outage database_deadlock memory_leak slow_database)

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!  %s\033[0m\n' "$*"; }

json_get() { python3 -c "import sys,json;print(json.load(sys.stdin)$1)"; }

say "Waiting for orchestrator at $API"
for i in $(seq 1 30); do
  if curl -sf "$API/health" >/dev/null 2>&1; then break; fi
  if [ "$i" = 30 ]; then echo "Orchestrator not reachable. Run 'make up' first." >&2; exit 1; fi
  sleep 2
done
echo "Orchestrator is up."

for r in $(seq 1 "$ROUNDS"); do
  say "Round $r of $ROUNDS"
  for s in "${SCENARIOS[@]}"; do
    echo "  • running scenario: $s"
    resp="$(curl -sf -X POST "$API/scenario/start" \
      -H 'content-type: application/json' \
      -d "{\"scenario\":\"$s\"}")"
    incident="$(printf '%s' "$resp" | json_get "['incident_id']")"
    echo "    captured $incident"

    echo "    diagnosing $incident ..."
    if dresp="$(curl -sf -X POST "$API/diagnose/$incident" 2>/dev/null)"; then
      pred="$(printf '%s' "$dresp" | json_get "['predicted_cause']")"
      conf="$(printf '%s' "$dresp" | json_get "['confidence']")"
      echo "    predicted: $pred (confidence $conf)"
    else
      warn "diagnosis skipped for $incident (is GEMINI_API_KEY set?)"
    fi
  done
done

say "Benchmark evaluation"
curl -sf "$API/evaluation" | python3 -m json.tool

say "Done. Open the dashboard at http://localhost:3000"
