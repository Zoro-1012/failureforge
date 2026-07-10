"""Evaluation engine (Phase 4) — the core differentiator.

Compares each incident's AI-predicted cause against its known ground truth and
computes diagnostic-quality metrics, both overall and per scenario type:

    overall:      accuracy, macro precision / recall / F1
    per_scenario: support, accuracy (= recall for that class), precision, recall, F1
    confusion_matrix: actual -> predicted counts

The metric math lives in `compute()` as a pure function (no DB), which keeps it
fully unit-testable; `evaluate()` wires it to the stored incidents + diagnoses.
"""
from . import db_store

# The known cause taxonomy (kept in sync with scenarios / diagnosis).
LABELS = [
    "redis_outage",
    "database_deadlock",
    "memory_leak",
    "slow_database",
]


def _safe_div(num: int, den: int) -> float:
    return round(num / den, 4) if den else 0.0


def _f1(precision: float, recall: float) -> float:
    return round(2 * precision * recall / (precision + recall), 4) if (precision + recall) else 0.0


def compute(records: list, labels: list | None = None) -> dict:
    """Compute evaluation metrics from (actual, predicted) records.

    `records` is a list of dicts each with "actual" and "predicted" keys.
    Records are assumed to already be diagnosed (predicted is non-empty).
    """
    labels = list(labels) if labels is not None else list(LABELS)
    # Include any unexpected predicted labels so the confusion matrix is honest.
    seen = {r["predicted"] for r in records if r.get("predicted")}
    extra = [l for l in sorted(seen) if l not in labels]
    all_labels = labels + extra

    evaluated = len(records)
    correct = sum(1 for r in records if r["actual"] == r["predicted"])

    # Confusion matrix: actual -> predicted -> count
    confusion = {a: {p: 0 for p in all_labels} for a in labels}
    for r in records:
        a, p = r["actual"], r.get("predicted", "")
        if a not in confusion:
            confusion[a] = {pp: 0 for pp in all_labels}
        if p not in confusion[a]:
            confusion[a][p] = 0
        confusion[a][p] += 1

    per_scenario = {}
    precisions, recalls, f1s = [], [], []
    for label in labels:
        tp = sum(1 for r in records if r["actual"] == label and r["predicted"] == label)
        fp = sum(1 for r in records if r["actual"] != label and r["predicted"] == label)
        fn = sum(1 for r in records if r["actual"] == label and r["predicted"] != label)
        support = sum(1 for r in records if r["actual"] == label)

        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _f1(precision, recall)

        per_scenario[label] = {
            "support": support,
            "correct": tp,
            "accuracy": recall,        # fraction of this scenario diagnosed correctly
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
        # Macro averages only over classes that actually appear in the data.
        if support > 0 or (tp + fp) > 0:
            precisions.append(precision)
            recalls.append(recall)
            f1s.append(f1)

    macro = lambda xs: round(sum(xs) / len(xs), 4) if xs else 0.0
    overall = {
        "accuracy": _safe_div(correct, evaluated),
        "macro_precision": macro(precisions),
        "macro_recall": macro(recalls),
        "macro_f1": macro(f1s),
    }

    return {
        "evaluated": evaluated,
        "correct": correct,
        "overall": overall,
        "per_scenario": per_scenario,
        "confusion_matrix": confusion,
    }


def evaluate() -> dict:
    """Pull diagnosed incidents from storage and compute the benchmark metrics."""
    pairs = db_store.get_eval_pairs()
    diagnosed = [p for p in pairs if p.get("predicted_cause")]
    records = [
        {"actual": p["ground_truth"], "predicted": p["predicted_cause"]}
        for p in diagnosed
    ]
    result = compute(records)
    result["total_incidents"] = len(pairs)
    result["undiagnosed"] = len(pairs) - len(diagnosed)
    return result
