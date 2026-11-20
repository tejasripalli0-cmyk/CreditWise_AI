"""Exported CSV loading and reconciliation with the original images / model."""
import pytest

from creditwise import analytics as a
from creditwise.model_store import ASSETS_DIR


def test_all_expected_assets_exist():
    for name in ["creditwise_model.pkl", "model_comparison.csv", "hyperparameter_tuning.csv", "final_model_metrics.csv",
                 "threshold_analysis.csv", "shap_feature_importance.csv", "confusion_matrix.png", "shap_summary.png"]:
        assert (ASSETS_DIR / name).is_file(), name


def test_model_comparison_loads_all_six_models():
    d = a.load_model_comparison()
    assert {r["model"] for r in d["rows"]} == {"Gradient Boosting", "SVM", "Logistic Regression", "Random Forest", "Bagging", "Decision Tree"}
    assert d["best_model"] == "Gradient Boosting"
    assert d["best_by_metric"]["Accuracy"] == "Bagging"  # honest: not hidden even though it is not the selected model


def test_tuning_parameters_are_parsed_as_data():
    gb = next(t for t in a.load_tuning() if t["model"] == "Gradient Boosting")
    assert gb["best_parameters"] == {"n_estimators": 100, "min_samples_leaf": 20, "max_depth": 3, "learning_rate": 0.1}


def test_final_metrics_match_the_saved_model_threshold(bundle):
    f = a.load_final_metrics()
    assert f["threshold"] == round(bundle.threshold, 4) == 0.15 and f["model"] == bundle.name


def test_confusion_counts_reproduce_csv_metrics():
    c, f = a.CONFUSION_FROM_IMAGE, a.load_final_metrics()
    assert (c["tp"] + c["tn"]) / sum(c.values()) == pytest.approx(f["accuracy"], abs=1e-9)
    assert c["tp"] / (c["tp"] + c["fp"]) == pytest.approx(f["precision"], abs=1e-9)
    assert c["tp"] / (c["tp"] + c["fn"]) == pytest.approx(f["recall"], abs=1e-9)


def test_threshold_curve_contains_saved_threshold():
    ts = [t["threshold"] for t in a.load_thresholds()]
    assert len(ts) == 81 and 0.15 in ts and min(ts) == 0.1 and max(ts) == 0.9


def test_shap_grouping_covers_every_encoded_column_and_original_feature(bundle):
    raw, grouped = a.load_shap_raw(), a.importance_by_original()
    assert len(raw) == len(bundle.transformed_names) == 247
    assert {r["feature"] for r in raw} == set(bundle.transformed_names)
    assert set(grouped) == set(bundle.feature_names)
    assert sum(grouped.values()) == pytest.approx(sum(r["importance"] for r in raw))
    assert a.top_features(3)[0]["feature"] == "EXT_SOURCE_3"


def test_dataset_counts_agree_with_model(bundle):
    d = a.build_analytics_payload()["dataset"]
    assert (d["n_original_features"], d["n_numeric_features"], d["n_categorical_features"], d["n_encoded_features"]) == \
           (125, len(bundle.numeric_cols), len(bundle.categorical_cols), len(bundle.transformed_names))
