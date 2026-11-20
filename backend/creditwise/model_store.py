"""Loads the ORIGINAL exported Colab model package exactly as saved (never retrained or modified)."""
from __future__ import annotations

import functools
import hashlib
import platform
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from .catalog import CATALOG

ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = ROOT / "model_assets"
MODEL_PATH = ASSETS_DIR / "creditwise_model.pkl"

# Environment the model was exported from, as stated by the project owner (not stored in the pickle).
EXPORT_ENVIRONMENT = {
    "python": "3.13.18", "scikit-learn": "1.6.1", "numpy": "2.4.6",
    "pandas": "2.2.3", "scipy": "1.16.3", "joblib": "1.6.0",
}
REQUIRED_KEYS = ("model", "preprocessor", "threshold", "model_name", "feature_names",
                 "transformed_feature_names", "target_mapping")


class ModelLoadError(RuntimeError):
    """Raised when the saved model package is missing or structurally unexpected."""


@dataclass
class ModelBundle:
    model: object
    preprocessor: object
    threshold: float
    name: str
    feature_names: list
    transformed_names: list
    target_mapping: dict
    numeric_cols: list
    categorical_cols: list
    categories: dict               # categorical feature -> categories seen when fitting
    medians: dict                  # numeric feature -> median used for imputation
    modes: dict                    # categorical feature -> most-frequent value used for imputation
    sha256: str
    load_warnings: list = field(default_factory=list)


def _library_versions() -> dict:
    import joblib, numpy, pandas, scipy, sklearn
    return {"python": platform.python_version(), "scikit-learn": sklearn.__version__, "numpy": numpy.__version__,
            "pandas": pandas.__version__, "scipy": scipy.__version__, "joblib": joblib.__version__}


@functools.lru_cache(maxsize=1)
def get_bundle() -> ModelBundle:
    """Load once per process; Vercel reuses warm instances so later requests skip this cost."""
    import joblib
    import numpy as np  # noqa: F401  (ensures numpy is importable before unpickling)

    if not MODEL_PATH.is_file():
        raise ModelLoadError("Model file is missing from the deployment.")
    digest = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pkg = joblib.load(MODEL_PATH)
    load_warnings = [f"{w.category.__name__}: {w.message}" for w in caught]

    if not isinstance(pkg, dict) or any(k not in pkg for k in REQUIRED_KEYS):
        raise ModelLoadError("Model package does not have the expected structure.")

    pre, model = pkg["preprocessor"], pkg["model"]
    feature_names = [str(f) for f in pkg["feature_names"]]
    transformed = [str(f) for f in pkg["transformed_feature_names"]]

    if list(getattr(pre, "feature_names_in_", [])) != feature_names:
        raise ModelLoadError("Preprocessor input columns do not match the saved feature list.")
    if model.n_features_in_ != len(transformed) or list(pre.get_feature_names_out()) != transformed:
        raise ModelLoadError("Transformed feature names do not match the model input width.")
    if set(feature_names) != set(CATALOG):
        raise ModelLoadError("Feature catalog is out of sync with the saved model.")

    if [t[0] for t in pre.transformers_[:2]] != ["num", "cat"]:
        raise ModelLoadError("Preprocessor layout is not the expected numeric + categorical pipeline.")
    num_cols = [str(c) for c in pre.transformers_[0][2]]
    cat_cols = [str(c) for c in pre.transformers_[1][2]]
    num_imputer = pre.named_transformers_["num"].named_steps["imputer"]
    cat_pipe = pre.named_transformers_["cat"]
    cat_imputer = cat_pipe.named_steps["imputer"]
    encoder = cat_pipe.steps[-1][1]

    return ModelBundle(
        model=model, preprocessor=pre, threshold=float(pkg["threshold"]), name=str(pkg["model_name"]),
        feature_names=feature_names, transformed_names=transformed,
        target_mapping={int(k): str(v) for k, v in pkg["target_mapping"].items()},
        numeric_cols=num_cols, categorical_cols=cat_cols,
        categories={c: [str(x) for x in cats] for c, cats in zip(cat_cols, encoder.categories_)},
        medians={c: float(v) for c, v in zip(num_cols, num_imputer.statistics_)},
        modes={c: str(v) for c, v in zip(cat_cols, cat_imputer.statistics_)},
        sha256=digest, load_warnings=load_warnings,
    )


def runtime_versions() -> dict:
    return _library_versions()
