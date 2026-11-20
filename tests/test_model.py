"""Model loading, metadata and the original-file integrity guard."""
import hashlib

from creditwise.model_store import MODEL_PATH

# SHA-256 of creditwise_model.pkl exactly as exported from Colab. If this fails, the model was changed.
ORIGINAL_SHA256 = "2c876bc25782ee945018a995e887b69eb745e8c19a50df0fd43f41511282a1c1"


def test_original_model_file_is_unmodified():
    assert hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest() == ORIGINAL_SHA256


def test_model_loads_and_is_gradient_boosting(bundle):
    assert type(bundle.model).__name__ == "GradientBoostingClassifier"
    assert bundle.name == "Gradient Boosting"
    assert bundle.model.n_estimators_ == 100 and bundle.model.max_depth == 3
    assert list(bundle.model.classes_) == [0, 1]


def test_saved_threshold_is_015_not_05(bundle):
    assert abs(bundle.threshold - 0.15) < 1e-12 and bundle.threshold != 0.5


def test_schema_dimensions(bundle):
    assert len(bundle.feature_names) == 125 and len(set(bundle.feature_names)) == 125
    assert len(bundle.transformed_names) == bundle.model.n_features_in_ == 247
    assert len(bundle.numeric_cols) == 109 and len(bundle.categorical_cols) == 16


def test_target_mapping(bundle):
    assert bundle.target_mapping == {0: "No recorded payment difficulty", 1: "Recorded payment difficulty"}


def test_missing_value_handling_is_median_and_most_frequent(bundle):
    pre = bundle.preprocessor
    assert pre.named_transformers_["num"].named_steps["imputer"].strategy == "median"
    assert pre.named_transformers_["cat"].named_steps["imputer"].strategy == "most_frequent"
    assert pre.named_transformers_["cat"].steps[-1][1].handle_unknown == "ignore"


def test_catalog_matches_model_exactly(bundle):
    from creditwise.catalog import CATALOG
    assert set(CATALOG) == set(bundle.feature_names)


def test_library_versions_match_export_environment(bundle):
    from creditwise.metadata import build_model_payload
    info = build_model_payload(bundle)
    assert info["libraries_match_export"] is True, info["load_warnings"]
    assert info["load_warnings"] == []  # no InconsistentVersionWarning when unpickling
