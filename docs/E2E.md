# End-to-end testing

FailureForge has two layers of E2E tests, both run locally and both use an
**offline stub diagnosis provider** so they're deterministic and need no Gemini
key.

## The stub diagnosis provider

Setting `DIAGNOSIS_PROVIDER=stub` swaps the Gemini call for a deterministic
heuristic that maps each scenario's distinct log signature to its cause label
(`deadlock detected` → `database_deadlock`, `Redis connection refused` →
`redis_outage`, `OOM warning` → `memory_leak`, `slow database query` →
`slow_database`). Production behaviour is unchanged — the default provider is
still `gemini`. The switch exists purely to make E2E reproducible.

## 1. Backend pipeline E2E

Exercises the real API against a live stack: **start scenario → incident
persisted in PostgreSQL → diagnose → evaluation**.

```bash
make e2e            # boots backend stack (stub provider), runs tests, tears down
KEEP=1 make e2e     # leave the stack running afterwards
```

- Test: `tests/e2e/test_pipeline_e2e.py`
- Runner: `scripts/e2e.sh`
- Requires Docker and `pip install pytest httpx` on the host.
- With the stub provider (`E2E_STUB=1`, set by the script) it asserts every
  prediction exactly matches ground truth and overall accuracy is 100%.

## 2. Frontend UI E2E (Playwright)

Drives the actual dashboard in a browser: click a scenario button, open the
incident, run diagnosis, assert the ✓ Correct result and confidence render.

```bash
make e2e-ui         # boots full stack (stub provider) + runs Playwright
```

- Test: `frontend/e2e/dashboard.spec.ts`
- Config: `frontend/playwright.config.ts`
- Runner: `scripts/e2e-ui.sh` (installs Chromium on first run)
- Requires Docker and Node 20+.

## Notes

- Both runners tear the stack down by default; pass `KEEP=1` to keep it.
- These are intentionally **local-only** (not in CI) because they need Docker and
  a browser. The unit tests in `tests/` (including the stub-provider tests) run
  in CI on every push.
