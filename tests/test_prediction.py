"""Real predictions with the original model: full, partial, missing numeric/categorical, threshold, columns."""
import dataclasses

import numpy as np
import pandas as pd
import pytest

from conftest import CORE, EXT
from creditwise import predictor
from creditwise.inputs import InputError, build_row, prepare_input


def _full_input(bundle):
    """A value for ALL 125 features, built from the fitted medians / modes (no invented categories)."""
    from creditwise.inputs import to_user_units
    vals = {c: to_user_units(c, bundle.medians[c]) for c in bundle.numeric_cols}
    vals.update(bundle.modes)
    for c in ("FLAG_MOBIL", "FLAG_DOCUMENT_12"):   # constant-in-training columns sit at 0/1 already
        vals[c] = float(vals[c])
    return vals


def test_full_125_field_prediction(bundle):
    full = _full_input(bundle)
    assert len(full) == 125
    r = predictor.predict(full)
    assert 0 <= r["prediction"]["probability"] <= 1
    assert r["completeness"]["assumed_default"] == 0
    assert r["completeness"]["importance_coverage"] == pytest.approx(1.0)


@pytest.mark.parametrize("inputs", [
    CORE, {**CORE, **EXT}, {"EXT_SOURCE_2": 0.4}, {"CODE_GENDER": "F"}, {"AMT_INCOME_TOTAL": 90000, "AMT_CREDIT": 300000},
    {"NAME_EDUCATION_TYPE": "Higher education", "OCCUPATION_TYPE": "Managers", "AGE_YEARS": 50},
    {"EXT_SOURCE_3": 0.9, "FLAG_OWN_CAR": "Y", "CNT_CHILDREN": 2},
])
def test_partial_inputs_produce_valid_predictions(inputs):
    r = predictor.predict(inputs)
    p = r["prediction"]
    assert 0 <= p["probability"] <= 1 and p["predicted_class"] in (0, 1)
    assert r["explanation"]["available"] is True


def test_model_receives_all_125_original_columns(bundle, monkeypatch):
    """Spy on the saved preprocessor: it must get a 1x125 frame in original column order, never a reduced one."""
    seen = []
    real = bundle.preprocessor.transform

    def spy(frame):
        seen.append(frame.copy())
        return real(frame)

    monkeypatch.setattr(bundle.preprocessor, "transform", spy, raising=False)
    predictor.predict({"AMT_CREDIT": 500000, "CODE_GENDER": "M"}, explain=False)
    assert len(seen) == 1
    assert list(seen[0].columns) == bundle.feature_names and seen[0].shape == (1, 125)


def test_unprovided_cells_are_nan_never_none_or_zero(bundle):
    row = prepare_input({"AMT_CREDIT": 500000}, bundle).row
    for c in bundle.numeric_cols:
        if c != "AMT_CREDIT":
            assert np.isnan(row.at[0, c]), c
    for c in bundle.categorical_cols:
        v = row.at[0, c]
        assert isinstance(v, float) and np.isnan(v), c      # np.nan, not None


def test_blank_equals_explicit_median_and_mode_row(bundle):
    """Leaving everything blank must be identical to supplying the saved medians/modes explicitly."""
    blank = build_row({}, bundle)
    explicit = build_row({**bundle.medians, **bundle.modes}, bundle)
    p = lambda df: float(bundle.model.predict_proba(bundle.preprocessor.transform(df))[0, 1])
    assert p(blank) == pytest.approx(p(explicit), abs=1e-12)


def test_regression_none_in_categorical_would_be_wrong(bundle):
    """Documents the trap: None in an object column is not 'missing' for sklearn and gives a different answer."""
    good = build_row({}, bundle)
    bad = good.copy()
    for c in bundle.categorical_cols:
        bad[c] = None
    p = lambda df: float(bundle.model.predict_proba(bundle.preprocessor.transform(df))[0, 1])
    assert p(good) != pytest.approx(p(bad), abs=1e-6)


def test_missing_categorical_is_filled_with_training_mode(bundle):
    only_credit = predictor.predict({"AMT_CREDIT": 500000})
    gender_mode = predictor.predict({"AMT_CREDIT": 500000, "CODE_GENDER": bundle.modes["CODE_GENDER"]})
    assert only_credit["prediction"]["probability"] == pytest.approx(gender_mode["prediction"]["probability"], abs=1e-12)


def test_missing_numeric_is_filled_with_training_median(bundle):
    from creditwise.inputs import to_user_units
    a = predictor.predict({"CODE_GENDER": "M"})
    b = predictor.predict({"CODE_GENDER": "M", "EXT_SOURCE_2": bundle.medians["EXT_SOURCE_2"]})
    assert a["prediction"]["probability"] == pytest.approx(b["prediction"]["probability"], abs=1e-12)


def test_inputs_change_the_prediction_in_the_expected_direction():
    low = predictor.predict({**CORE, **EXT})["prediction"]["probability"]
    high = predictor.predict({**CORE, "EXT_SOURCE_1": 0.8, "EXT_SOURCE_2": 0.85, "EXT_SOURCE_3": 0.85})["prediction"]["probability"]
    assert low > high


def test_threshold_decides_the_class(bundle, monkeypatch):
    p = predictor.predict({**CORE, **EXT})["prediction"]["probability"]
    for thr, expected in ((p, 1), (p - 1e-9, 1), (p + 1e-9, 0), (0.5, 1 if p >= 0.5 else 0)):
        monkeypatch.setattr(predictor, "get_bundle", lambda t=thr: dataclasses.replace(bundle, threshold=t))
        assert predictor.predict({**CORE, **EXT}, explain=False)["prediction"]["predicted_class"] == expected


def test_saved_threshold_is_what_the_api_uses(client):
    r = client.post("/api/predict", json={"inputs": {**CORE, **EXT}}).json()["prediction"]
    assert r["threshold"] == 0.15
    assert r["predicted_class"] == int(r["probability"] >= 0.14999999999999997)


def test_derived_features_are_calculated_not_overwriting_manual_values(bundle):
    auto = prepare_input({"AMT_CREDIT": 600000, "AMT_INCOME_TOTAL": 200000, "AMT_GOODS_PRICE": 540000,
                          "AMT_ANNUITY": 30000, "AGE_YEARS": 40, "EMPLOYMENT_YEARS": 5}, bundle)
    v = auto.model_values
    assert v["CREDIT_INCOME_RATIO"] == pytest.approx(3.0) and v["ANNUITY_INCOME_RATIO"] == pytest.approx(0.15)
    assert v["GOODS_CREDIT_RATIO"] == pytest.approx(0.9)
    assert v["DAYS_BIRTH"] == pytest.approx(-40 * 365.25) and v["DAYS_EMPLOYED"] == pytest.approx(-5 * 365.25)
    manual = prepare_input({"AMT_CREDIT": 600000, "AMT_INCOME_TOTAL": 200000, "CREDIT_INCOME_RATIO": 9.99}, bundle)
    assert manual.model_values["CREDIT_INCOME_RATIO"] == 9.99 and "CREDIT_INCOME_RATIO" not in manual.derived_fields


def test_days_fields_use_friendly_positive_input(bundle):
    p = prepare_input({"DAYS_BIRTH": 15725}, bundle)
    assert p.model_values["DAYS_BIRTH"] == -15725 and p.model_values["AGE_YEARS"] == pytest.approx(43.0527, abs=1e-3)


def test_inconsistent_manual_age_is_flagged(bundle):
    p = prepare_input({"AGE_YEARS": 25, "DAYS_BIRTH": 20000}, bundle)
    assert any(w["code"] == "inconsistent_age" for w in p.warnings)


def test_importance_coverage_is_monotonic_and_limited_for_core_fields():
    core = predictor.predict(CORE)["completeness"]
    with_ext = predictor.predict({**CORE, **EXT})["completeness"]
    assert with_ext["importance_coverage"] > core["importance_coverage"]
    assert core["level"] == "limited" and with_ext["level"] == "good"
    assert core["user_provided"] == 6 and core["auto_derived"] == 5


def test_risk_band_is_relative_to_saved_threshold():
    assert predictor.risk_band(0.05, 0.15)["key"] == "low"
    assert predictor.risk_band(0.10, 0.15)["key"] == "moderate"
    assert predictor.risk_band(0.20, 0.15)["key"] == "elevated"
    assert predictor.risk_band(0.40, 0.15)["key"] == "high"


def test_shap_explanation_is_exact_and_grouped_by_original_feature(bundle):
    e = predictor.predict({**CORE, **EXT}, top_n=25)["explanation"]
    assert e["available"] and e["additivity_error"] < 1e-9
    names = {c["feature"] for c in e["contributions"]}
    assert names <= set(bundle.feature_names) and not any(n.startswith(("num__", "cat__")) for n in names)
    total = sum(c["contribution"] for c in e["contributions"]) + e["other_contribution"]
    assert e["base_value"] + total == pytest.approx(e["output_value"], abs=1e-5)
    assert e["from_provided_fields"] + e["from_assumed_defaults"] == pytest.approx(total, abs=1e-5)
    assert {c["source"] for c in e["contributions"]} <= {"entered", "calculated", "assumed"}


# ---- validation -------------------------------------------------------------------------------------
@pytest.mark.parametrize("bad", [
    {"HACK": 1}, {"CODE_GENDER": "Martian"}, {"AMT_CREDIT": "abc"}, {"AMT_CREDIT": float("inf")}, {"AMT_CREDIT": float("nan")},
    {"AMT_CREDIT": -5}, {"AMT_CREDIT": 5e12}, {"AGE_YEARS": 12}, {"EXT_SOURCE_2": 1.5}, {"CNT_CHILDREN": 1.5},
    {"FLAG_DOCUMENT_3": 2}, {"AMT_CREDIT": True}, {"OCCUPATION_TYPE": 7}, {"HOUR_APPR_PROCESS_START": 24}, {},
])
def test_invalid_inputs_are_rejected(bad, bundle):
    with pytest.raises(InputError):
        prepare_input(bad, bundle)


def test_blank_values_count_as_not_provided(bundle):
    p = prepare_input({"AMT_CREDIT": 500000, "CODE_GENDER": "", "EXT_SOURCE_1": None}, bundle)
    assert p.user_fields == ["AMT_CREDIT"]
