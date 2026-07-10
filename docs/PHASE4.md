# Phase 4 — Evaluation engine

**Deliverable:** accuracy, precision, and recall — overall and per scenario type.

This is the project's core differentiator: it turns AI root-cause analyses into a
measurable benchmark by scoring each prediction against known ground truth.

## What's new

- **`evaluation.py`** — `compute()` is a pure function over `(actual, predicted)`
  records (fully unit-tested); `evaluate()` pulls diagnosed incidents from storage
  and returns the metrics.
- **`GET /evaluation`** — benchmark metrics on demand.
- **`db_store.get_eval_pairs()`** — joins each incident with its latest diagnosis.

## Metrics

For each incident, `actual_cause = ground_truth` and
`predicted_cause = latest diagnosis`. From these:

- **Overall:** accuracy (= correct / evaluated), plus macro-averaged precision,
  recall, and F1.
- **Per scenario** (one row per cause label):
  - `support` — incidents whose actual cause is this label
  - `accuracy` / `recall` — fraction of this scenario diagnosed correctly
  - `precision` — of everything predicted as this label, how much was right
  - `f1` — harmonic mean of precision and recall
- **Confusion matrix** — actual → predicted counts (out-of-taxonomy guesses are
  shown and counted as misses).

## Example response

```json
{
  "total_incidents": 12,
  "evaluated": 12,
  "undiagnosed": 0,
  "correct": 10,
  "overall": {"accuracy": 0.833, "macro_precision": 0.85, "macro_recall": 0.83, "macro_f1": 0.84},
  "per_scenario": {
    "redis_outage":      {"support": 3, "correct": 3, "accuracy": 1.0,  "precision": 1.0,  "recall": 1.0,  "f1": 1.0},
    "memory_leak":       {"support": 3, "correct": 2, "accuracy": 0.667, "precision": 1.0, "recall": 0.667, "f1": 0.8},
    "database_deadlock": {"support": 3, "correct": 3, "accuracy": 1.0,  "precision": 0.75, "recall": 1.0,  "f1": 0.857},
    "slow_database":     {"support": 3, "correct": 2, "accuracy": 0.667, "precision": 1.0, "recall": 0.667, "f1": 0.8}
  },
  "confusion_matrix": { "memory_leak": {"memory_leak": 2, "slow_database": 1, ...}, ... }
}
```

## Run it

```bash
make up
make all-scenarios            # generate incidents
for i in 001 002 003 004; do make diagnose ID=incident_$i; done   # diagnose them
make evaluation               # accuracy / precision / recall, overall + per scenario
```

Run several rounds of scenarios + diagnoses to build enough support for stable
per-scenario numbers.

## Testing

`tests/test_evaluation.py` verifies the metric math against hand-computed
confusion cases, out-of-taxonomy handling, empty input, and the storage wiring —
all with **no DB or API key**.

## Roadmap (next)

- **Phase 5** — Next.js dashboard (totals, accuracy, scenario breakdown, incident
  view) + documentation + demo.
