# Phase 3 — Gemini diagnosis pipeline

**Deliverable:** the AI can generate root-cause analysis (RCA) reports from a
stored incident's telemetry.

## What's new

- **`diagnosis.py`** — a single, non-agentic pipeline: build a compact context
  from an incident's logs + metrics, call Gemini, parse a structured RCA.
- **`POST /diagnose/{incident_id}`** — runs the pipeline over a stored incident
  and persists the result.
- **Persistence** — a `diagnoses` table in PostgreSQL plus a `diagnosis.json`
  exported into the incident's dataset folder. `GET /incidents/{id}` now returns
  the latest diagnosis inline.

## Output shape

```json
{
  "incident_id": "incident_001",
  "predicted_cause": "redis_outage",
  "confidence": 0.92,
  "evidence": ["ERROR 'Redis connection refused' x6", "failure latency 16x baseline"],
  "recommended_fix": "Restart Redis; add a cache circuit breaker and DB fallback.",
  "model": "gemini-2.5-flash"
}
```

## Fair-benchmark design

The ground-truth label is **never** sent to the model — `build_context` renders
only severity-bucketed log samples and per-phase metric aggregates (baseline vs
failure). The model classifies into the known cause taxonomy
(`redis_outage`, `database_deadlock`, `memory_leak`, `slow_database`), which lets
Phase 4 score predictions against ground truth.

The pipeline is intentionally robust: it strips accidental code fences, clamps
confidence to `[0, 1]`, coerces `evidence` to a list, and flags
out-of-taxonomy guesses (counted as misses later) rather than crashing.

## Setup

1. Get a Gemini API key at <https://aistudio.google.com/apikey>.
2. Put it in a `.env` file at the repo root (read by Docker Compose):

   ```
   GEMINI_API_KEY=your_key_here
   GEMINI_MODEL=gemini-2.5-flash   # optional override
   ```

## Run it

```bash
make up
make redis-outage                 # produce an incident (e.g. incident_001)
make diagnose ID=incident_001     # run the AI RCA
curl localhost:8000/incidents/incident_001 | python3 -m json.tool   # see diagnosis inline
cat datasets/incident_001/diagnosis.json
```

## Testing

`tests/test_diagnosis.py` covers context construction, JSON parsing, confidence
clamping, and error handling with **no network or API key required**. The live
model call is exercised by running `make diagnose` against a real key.

## Roadmap (next)

- **Phase 4** — evaluation engine: accuracy / precision / recall per scenario,
  comparing `predicted_cause` to `ground_truth` across incidents.
- **Phase 5** — Next.js dashboard + docs + demo.
