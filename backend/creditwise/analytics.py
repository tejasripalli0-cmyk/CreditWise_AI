"""Reads the exported Colab CSVs. Nothing here is generated, simulated or estimated.

Uses only the standard library so the analytics endpoint stays light (no pandas/sklearn import).
"""
from __future__ import annotations

import ast
import csv
import functools
from pathlib import Path

from .catalog import CATALOG, CHOICE_LABELS
from .model_store import ASSETS_DIR

CSV_FILES = {
    "model_comparison": "model_comparison.csv",
    "hyperparameter_tuning": "hyperparameter_tuning.csv",
    "final_model_metrics": "final_model_metrics.csv",
    "threshold_analysis": "threshold_analysis.csv",
    "shap_feature_importance": "shap_feature_importance.csv",
}
IMAGE_FILES = ("confusion_matrix.png", "shap_summary.png")

# Counts transcribed from the exported confusion_matrix.png (rows = actual, columns = predicted).
# tests/test_analytics.py recomputes accuracy / precision / recall from these four numbers and checks
# they equal final_model_metrics.csv, so a transcription error cannot go unnoticed.
CONFUSION_FROM_IMAGE = {"tn": 16494, "fp": 1891, "fn": 990, "tp": 625}

COMPARISON_NOTE = (
    "The comparison table and the final-model table are different operating points: the comparison "
    "reports each model at its default setting, while the final model is evaluated at the saved 0.15 "
    "threshold. Accuracy, precision, recall and F1 therefore cannot be compared directly between the "
    "two tables. ROC-AUC and PR-AUC do not depend on a threshold."
)


def _read(name: str) -> list[dict]:
    path: Path = ASSETS_DIR / CSV_FILES[name]
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _num(v: str) -> float:
    return float(v)


@functools.lru_cache(maxsize=1)
def load_model_comparison() -> dict:
    metrics = ["Accuracy", "Precision", "Recall", "F1 Score", "ROC-AUC", "PR-AUC"]
    rows = []
    for r in _read("model_comparison"):
        rows.append({"model": r["Model"], **{m: _num(r[m]) for m in metrics},
                     "training_time_seconds": _num(r["Training Time (seconds)"])})
    best_by_metric = {m: max(rows, key=lambda r: r[m])["model"] for m in metrics}
    best = max(rows, key=lambda r: r["PR-AUC"])["model"]  # PR-AUC: the metric used to tune (imbalanced target)
    return {"metrics": metrics, "rows": rows, "best_model": best, "best_by_metric": best_by_metric,
            "best_basis": "PR-AUC (the metric used for cross-validated tuning on this imbalanced target)", "note": COMPARISON_NOTE}


@functools.lru_cache(maxsize=1)
def load_tuning() -> list[dict]:
    out = []
    for r in _read("hyperparameter_tuning"):
        out.append({"model": r["Model"], "best_cv_pr_auc": _num(r["Best CV PR-AUC"]),
                    "best_parameters": ast.literal_eval(r["Best Parameters"])})  # literal_eval: data only, no code
    return out


@functools.lru_cache(maxsize=1)
def load_final_metrics() -> dict:
    r = _read("final_model_metrics")[0]
    return {"model": r["Model"], "threshold": round(_num(r["Threshold"]), 4), "accuracy": _num(r["Accuracy"]),
            "precision": _num(r["Precision"]), "recall": _num(r["Recall"]), "f1": _num(r["F1-Score"]),
            "roc_auc": _num(r["ROC-AUC"]), "pr_auc": _num(r["PR-AUC"])}


@functools.lru_cache(maxsize=1)
def load_thresholds() -> list[dict]:
    return [{"threshold": round(_num(r["Threshold"]), 4), "precision": _num(r["Precision"]),
             "recall": _num(r["Recall"]), "f1": _num(r["F1-Score"])} for r in _read("threshold_analysis")]


def _strip_prefix(transformed: str) -> str:
    return transformed.split("__", 1)[1] if "__" in transformed else transformed


@functools.lru_cache(maxsize=1)
def load_shap_raw() -> list[dict]:
    return [{"feature": r["Feature"], "importance": _num(r["Mean_Absolute_SHAP"])} for r in _read("shap_feature_importance")]


@functools.lru_cache(maxsize=1)
def importance_by_original() -> dict:
    """Group transformed columns (num__X / cat__X_value) under their ORIGINAL input feature."""
    names = sorted(CATALOG, key=len, reverse=True)  # longest first so FLAG_OWN_CAR is not confused with a shorter prefix
    grouped: dict[str, float] = {}
    for row in load_shap_raw():
        base = _strip_prefix(row["feature"])
        if row["feature"].startswith("num__"):
            original = base
        else:
            original = next((n for n in names if base == n or base.startswith(n + "_")), None)
        if original is None or original not in CATALOG:
            raise ValueError("Unmapped SHAP column in the exported CSV.")
        grouped[original] = grouped.get(original, 0.0) + row["importance"]
    return grouped


def top_features(n: int = 20) -> list[dict]:
    total = sum(importance_by_original().values())
    ranked = sorted(importance_by_original().items(), key=lambda kv: -kv[1])[:n]
    return [{"feature": f, "label": CATALOG[f].label, "importance": v, "share": v / total} for f, v in ranked]


def top_encoded_columns(n: int = 20) -> list[dict]:
    return [{"feature": r["feature"], "importance": r["importance"]}
            for r in sorted(load_shap_raw(), key=lambda r: -r["importance"])[:n]]


def confusion_matrix_counts() -> dict:
    c = CONFUSION_FROM_IMAGE
    total = sum(c.values())
    return {**c, "total": total, "positives": c["tp"] + c["fn"], "negatives": c["tn"] + c["fp"],
            "positive_rate": (c["tp"] + c["fn"]) / total, "source": "confusion_matrix.png (reconciled with final_model_metrics.csv)"}


def build_analytics_payload(bundle_info: dict | None = None) -> dict:
    final = load_final_metrics()
    cm = confusion_matrix_counts()
    thresholds = load_thresholds()
    return {
        "model_comparison": load_model_comparison(),
        "tuning": load_tuning(),
        "final_metrics": final,
        "confusion_matrix": cm,
        "thresholds": thresholds,
        "saved_threshold": final["threshold"],
        "shap": {"top_original_features": top_features(25), "top_encoded_columns": top_encoded_columns(20),
                 "n_encoded_columns": len(load_shap_raw()), "n_original_features": len(importance_by_original()),
                 "grouping_note": "Each bar sums the mean absolute SHAP values of a feature's encoded columns "
                                  "(for example every one-hot column of Education level)."},
        "images": {"confusion_matrix": "/analytics/confusion_matrix.png", "shap_summary": "/analytics/shap_summary.png"},
        "dataset": {
            "name": "Home Credit Default Risk",
            "target": "TARGET: 1 = recorded payment difficulty, 0 = no recorded payment difficulty",
            "held_out_test_rows": cm["total"], "held_out_positive_rows": cm["positives"],
            "held_out_positive_rate": cm["positive_rate"],
            "n_original_features": 125, "n_numeric_features": 109, "n_categorical_features": 16, "n_encoded_features": 247,
            "preprocessing": ["Numeric: median imputation then standard scaling",
                              "Categorical: most-frequent imputation then one-hot encoding (unknown categories ignored)"],
            "not_in_export": ["Training-set size", "Cross-validation fold details", "Raw dataset"],
            "category_labels": {k: v for k, v in CHOICE_LABELS.items()},
        },
    }
