"""Inference with the original saved pipeline + model + saved threshold. Stateless; nothing is stored or logged."""
from __future__ import annotations

import functools
import math

import numpy as np

from . import analytics
from .catalog import CATALOG, CHOICE_LABELS
from .inputs import PreparedInput, prepare_input, to_user_units
from .model_store import ModelBundle, get_bundle

ADDITIVITY_TOLERANCE = 1e-6

# Score bands are expressed relative to the SAVED threshold; they are descriptive buckets of the model
# score, not calibrated probabilities or a lending policy.
RISK_BANDS = [
    (0.5, "low", "Low", "Well below the model's decision threshold."),
    (1.0, "moderate", "Moderate", "Below the model's decision threshold, but not far below it."),
    (2.0, "elevated", "Elevated", "At or above the decision threshold: the model flags recorded payment difficulty."),
    (math.inf, "high", "High", "At least twice the decision threshold."),
]


def risk_band(probability: float, threshold: float) -> dict:
    ratio = probability / threshold
    for upper, key, label, text in RISK_BANDS:
        if ratio < upper:
            return {"key": key, "label": label, "description": text, "score_to_threshold_ratio": round(ratio, 4)}
    raise AssertionError("unreachable")


def _display_value(name: str, value) -> str | float:
    spec = CATALOG[name]
    if isinstance(value, str):
        return CHOICE_LABELS.get(name, {}).get(value, value)
    v = to_user_units(name, value)
    if spec.kind == "flag":
        return "Yes" if v == 1 else "No"
    return round(float(v), 4)


def _completeness(prepared: PreparedInput) -> dict:
    total = len(CATALOG)
    provided = set(prepared.user_fields) | set(prepared.derived_fields)
    weights = analytics.importance_by_original()
    coverage = sum(w for f, w in weights.items() if f in provided) / sum(weights.values())
    level = "good" if coverage >= 0.60 else "moderate" if coverage >= 0.30 else "limited"
    return {
        "total_features": total,
        "user_provided": len(prepared.user_fields),
        "auto_derived": len(prepared.derived_fields),
        "assumed_default": total - len(provided),
        "fraction_provided": round(len(provided) / total, 4),
        "importance_coverage": round(coverage, 4),
        "level": level,
        "user_fields": sorted(prepared.user_fields),
        "derived_fields": sorted(prepared.derived_fields),
        "basis": ("Importance coverage is the share of the model's total global SHAP importance (from the exported "
                  "analysis) carried by the fields you supplied or that were calculated from them."),
    }


def _warnings(prepared: PreparedInput, completeness: dict) -> list[dict]:
    out = list(prepared.warnings)
    provided = set(prepared.user_fields) | set(prepared.derived_fields)
    if completeness["level"] == "limited":
        out.append({"level": "warning", "code": "limited_information",
                    "message": "Only a small part of the model's most informative inputs was provided, so this result "
                               "is likely to be less reliable. Missing details are filled with typical training-data "
                               "values; they are not recovered or known."})
    elif completeness["level"] == "moderate":
        out.append({"level": "info", "code": "partial_information",
                    "message": "Some informative inputs are missing. Missing details are filled with typical "
                               "training-data values, so treat this result with caution."})
    if not {"EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3"} & provided:
        out.append({"level": "info", "code": "no_external_scores",
                    "message": "None of the three external source scores were entered. They are the model's three "
                               "strongest signals, so adding them usually changes the result the most."})
    return out


@functools.lru_cache(maxsize=1)
def _explainer():
    import shap  # imported lazily: only needed when an explanation is requested
    return shap.TreeExplainer(get_bundle().model)


@functools.lru_cache(maxsize=1)
def _column_owner() -> dict:
    """Map each transformed column to its original input feature (exactly, via the fitted encoder categories)."""
    b = get_bundle()
    owner = {f"num__{c}": c for c in b.numeric_cols}
    for col, cats in b.categories.items():
        for cat in cats:
            owner[f"cat__{col}_{cat}"] = col
    if set(owner) != set(b.transformed_names):
        raise RuntimeError("Could not map every transformed column to an original feature.")
    return owner


def _explain(bundle: ModelBundle, X_dense: np.ndarray, prepared: PreparedInput, top_n: int) -> dict:
    try:
        explainer = _explainer()
        sv = np.asarray(explainer.shap_values(X_dense))
        if sv.ndim == 3:                       # some SHAP versions return (classes, rows, features) or (rows, features, classes)
            sv = sv[1] if sv.shape[0] == 2 else sv[..., 1]
        sv = sv[0]
        base = float(np.ravel(explainer.expected_value)[-1])
        raw = float(bundle.model.decision_function(X_dense)[0])
        error = abs(base + float(sv.sum()) - raw)
        if sv.shape[0] != len(bundle.transformed_names) or error > ADDITIVITY_TOLERANCE:
            return {"available": False, "reason": "The explanation failed an internal consistency check and was withheld."}
    except Exception:  # never surface internals; do not log applicant data
        return {"available": False, "reason": "An applicant-specific explanation could not be calculated for this request."}

    owner = _column_owner()
    grouped: dict[str, float] = {}
    for name, value in zip(bundle.transformed_names, sv):
        grouped[owner[name]] = grouped.get(owner[name], 0.0) + float(value)

    user, derived = set(prepared.user_fields), set(prepared.derived_fields)

    def entry(feat: str, contrib: float) -> dict:
        spec = CATALOG[feat]
        if feat in user:
            source, shown = "entered", _display_value(feat, prepared.model_values[feat])
        elif feat in derived:
            source, shown = "calculated", _display_value(feat, prepared.model_values[feat])
        else:
            source = "assumed"  # imputed by the saved pipeline
            typical = bundle.modes[feat] if feat in bundle.modes else bundle.medians[feat]
            shown = _display_value(feat, typical)
        return {"feature": feat, "label": spec.label, "value": shown, "source": source,
                "contribution": round(contrib, 6), "direction": "increases" if contrib > 0 else "decreases"}

    ranked = sorted(grouped.items(), key=lambda kv: -abs(kv[1]))
    top, rest = ranked[:top_n], ranked[top_n:]
    assumed_total = sum(v for f, v in grouped.items() if f not in user and f not in derived)
    return {
        "available": True,
        "method": "SHAP TreeExplainer (exact tree SHAP) on the saved model; contributions are in log-odds",
        "base_value": round(base, 6),
        "base_probability": round(1 / (1 + math.exp(-base)), 6),
        "output_value": round(raw, 6),
        "contributions": [entry(f, v) for f, v in top],
        "other_contribution": round(sum(v for _, v in rest), 6),
        "other_count": len(rest),
        "from_provided_fields": round(sum(v for f, v in grouped.items() if f in user or f in derived), 6),
        "from_assumed_defaults": round(assumed_total, 6),
        "additivity_error": error,
        "reading_guide": ("Positive bars push the score toward recorded payment difficulty; negative bars push it away. "
                          "Bars are summed over each field's encoded columns. 'Assumed' fields were not provided: the "
                          "saved pipeline filled them with typical training values, and they still influence the score."),
    }


def _summary(label: str, probability: float, threshold: float, predicted: int, explanation: dict) -> list[str]:
    side = "at or above" if predicted == 1 else "below"
    lines = [f"The model score is {probability:.1%}, which is {side} the saved decision threshold of {threshold:.0%}, "
             f"so the predicted class is: {label}."]
    if explanation.get("available") and explanation["contributions"]:
        ups = [c for c in explanation["contributions"] if c["contribution"] > 0][:2]
        downs = [c for c in explanation["contributions"] if c["contribution"] < 0][:2]
        if ups:
            lines.append("Pushing the score up the most: " + ", ".join(c["label"] for c in ups) + ".")
        if downs:
            lines.append("Pushing the score down the most: " + ", ".join(c["label"] for c in downs) + ".")
    lines.append("This is a statistical score from a model trained on the Home Credit dataset. It is not a credit "
                 "score, not a CIBIL score and not a lending decision.")
    return lines


def predict(raw_inputs: dict, explain: bool = True, top_n: int = 10) -> dict:
    bundle = get_bundle()
    prepared = prepare_input(raw_inputs, bundle)

    X = bundle.preprocessor.transform(prepared.row)          # EXACT saved preprocessing pipeline
    X_dense = X.toarray() if hasattr(X, "toarray") else np.asarray(X)
    probability = float(bundle.model.predict_proba(X_dense)[0, 1])
    predicted = int(probability >= bundle.threshold)          # SAVED threshold, not 0.5
    label = bundle.target_mapping[predicted]

    completeness = _completeness(prepared)
    explanation = _explain(bundle, X_dense, prepared, top_n) if explain else {"available": False, "reason": "Not requested."}
    return {
        "prediction": {
            "predicted_class": predicted, "label": label, "probability": probability,
            "threshold": round(bundle.threshold, 4), "above_threshold": bool(predicted),
            "risk_band": risk_band(probability, bundle.threshold),
            "probability_note": ("The score comes straight from the saved model. Probability calibration was not part of "
                                 "the exported work, so do not read it as a guaranteed real-world probability."),
        },
        "completeness": completeness,
        "warnings": _warnings(prepared, completeness),
        "explanation": explanation,
        "summary": _summary(label, probability, bundle.threshold, predicted, explanation),
        "model": {"name": bundle.name, "target_mapping": {str(k): v for k, v in bundle.target_mapping.items()}},
    }
