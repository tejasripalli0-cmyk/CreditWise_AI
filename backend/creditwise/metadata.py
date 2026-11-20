"""Builds the /features and /model payloads from the LOADED pickle (categories come from the fitted encoder)."""
from __future__ import annotations

from . import analytics
from .catalog import CATALOG, CHOICE_LABELS, DERIVATIONS, GROUPS
from .model_store import EXPORT_ENVIRONMENT, ModelBundle, runtime_versions


def _typical(name: str, bundle: ModelBundle):
    if name in bundle.modes:
        value = bundle.modes[name]
        return {"value": value, "label": CHOICE_LABELS.get(name, {}).get(value, value)}
    spec = CATALOG[name]
    v = bundle.medians[name]
    v = -v if spec.sign == -1 else v
    return {"value": round(v, 4), "label": f"{round(v, 4):g}"}


def build_features_payload(bundle: ModelBundle) -> dict:
    weights = analytics.importance_by_original()
    total = sum(weights.values())
    rank = {f: i + 1 for i, (f, _) in enumerate(sorted(weights.items(), key=lambda kv: -kv[1]))}
    features = []
    for name in bundle.feature_names:  # order of the saved model
        s = CATALOG[name]
        item = {
            "name": name, "label": s.label, "description": s.description, "group": s.group, "kind": s.kind,
            "unit": s.unit, "min": s.min, "max": s.max, "step": s.step, "featured": s.featured,
            "derived": s.derived, "keywords": list(s.keywords),
            "importance_rank": rank[name], "importance_share": round(weights[name] / total, 5),
            "typical": _typical(name, bundle),
        }
        if s.kind == "category":
            labels = CHOICE_LABELS.get(name, {})
            item["choices"] = [{"value": c, "label": labels.get(c, c)} for c in bundle.categories[name]]
        elif s.kind == "flag":
            item["choices"] = [{"value": 1, "label": "Yes"}, {"value": 0, "label": "No"}]
        features.append(item)
    suggested = [f for f, _ in sorted(weights.items(), key=lambda kv: -kv[1]) if not CATALOG[f].featured][:8]
    return {"groups": GROUPS, "features": features, "derivations": DERIVATIONS, "suggested": suggested,
            "n_features": len(features),
            "missing_value_policy": ("Blank fields are not removed. The saved pipeline fills numeric gaps with the training "
                                     "median and categorical gaps with the most frequent training category.")}


def build_model_payload(bundle: ModelBundle) -> dict:
    est = bundle.model
    keep = ["n_estimators", "learning_rate", "max_depth", "min_samples_leaf", "subsample", "loss", "random_state"]
    params = {k: est.get_params()[k] for k in keep}
    runtime = runtime_versions()
    matches = all(runtime.get(k) == v for k, v in EXPORT_ENVIRONMENT.items() if k != "python")
    return {
        "name": bundle.name, "estimator": type(est).__name__, "parameters": params,
        "n_estimators_fitted": int(est.n_estimators_), "classes": [int(c) for c in est.classes_],
        "threshold": round(bundle.threshold, 4), "threshold_exact": bundle.threshold,
        "n_original_features": len(bundle.feature_names), "n_numeric_features": len(bundle.numeric_cols),
        "n_categorical_features": len(bundle.categorical_cols), "n_encoded_features": len(bundle.transformed_names),
        "target_mapping": {str(k): v for k, v in bundle.target_mapping.items()},
        "preprocessing": {
            "numeric": "SimpleImputer(median) then StandardScaler",
            "categorical": "SimpleImputer(most_frequent) then OneHotEncoder(handle_unknown='ignore')",
            "supports_missing_values": True,
            "unknown_categories": "Ignored by the encoder (all-zero encoding); the API additionally rejects unknown categories.",
        },
        "export_environment": EXPORT_ENVIRONMENT, "runtime_environment": runtime,
        "libraries_match_export": matches, "load_warnings": bundle.load_warnings,
        "model_sha256": bundle.sha256,
    }
