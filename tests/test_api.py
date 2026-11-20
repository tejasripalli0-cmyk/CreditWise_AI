"""HTTP-level tests of every endpoint, including privacy and error behaviour."""
from conftest import CORE, EXT


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_health_deep_runs_a_real_prediction(client):
    assert client.get("/api/health?deep=true").json()["model_ok"] is True


def test_model_info(client):
    d = client.get("/api/model").json()
    assert d["estimator"] == "GradientBoostingClassifier" and d["threshold"] == 0.15 and d["n_original_features"] == 125
    text = client.get("/api/model").text
    assert "/home" not in text and "model_assets" not in text and "Traceback" not in text   # no filesystem leakage


def test_features_metadata_uses_real_categories(client, bundle):
    d = client.get("/api/features").json()
    by = {f["name"]: f for f in d["features"]}
    assert len(by) == 125 and set(by) == set(bundle.feature_names)
    assert [c["value"] for c in by["CODE_GENDER"]["choices"]] == ["F", "M"]
    assert len(by["ORGANIZATION_TYPE"]["choices"]) == 58
    assert sum(1 for f in d["features"] if f["featured"]) == 6
    assert set(d["groups"]) >= {f["group"] for f in d["features"]}


def test_analytics_endpoint(client):
    d = client.get("/api/analytics").json()
    assert d["saved_threshold"] == 0.15 and len(d["model_comparison"]["rows"]) == 6 and len(d["thresholds"]) == 81


def test_predict_endpoint_full_response_shape(client):
    r = client.post("/api/predict", json={"inputs": {**CORE, **EXT}})
    assert r.status_code == 200
    d = r.json()
    assert set(d) == {"prediction", "completeness", "warnings", "explanation", "summary", "model"}
    assert d["prediction"]["label"] in ("No recorded payment difficulty", "Recorded payment difficulty")
    assert d["explanation"]["available"] is True and len(d["explanation"]["contributions"]) == 10


def test_predict_without_explanation(client):
    d = client.post("/api/predict", json={"inputs": CORE, "explain": False}).json()
    assert d["explanation"]["available"] is False


def test_invalid_input_returns_422_without_echoing_values(client):
    r = client.post("/api/predict", json={"inputs": {"AMT_CREDIT": "SECRET-VALUE-123"}})
    assert r.status_code == 422 and "SECRET-VALUE-123" not in r.text and r.json()["detail"]["code"] == "invalid_input"


def test_schema_error_does_not_echo_values(client):
    r = client.post("/api/predict", json={"inputs": {"AGE_YEARS": 30}, "top_n": "SECRET-VALUE-456"})
    assert r.status_code == 422 and "SECRET-VALUE-456" not in r.text


def test_unknown_field_and_empty_inputs(client):
    assert client.post("/api/predict", json={"inputs": {"EVIL": 1}}).status_code == 422
    assert client.post("/api/predict", json={"inputs": {}}).status_code == 422


def test_oversized_body_rejected(client):
    assert client.post("/api/predict", content=b"x" * 40000, headers={"content-type": "application/json"}).status_code == 413


def test_security_headers_and_no_store_on_predictions(client):
    r = client.post("/api/predict", json={"inputs": CORE})
    assert r.headers["cache-control"] == "no-store" and r.headers["x-content-type-options"] == "nosniff"


def test_get_on_predict_is_not_allowed(client):
    assert client.get("/api/predict").status_code == 405


def test_unexpected_errors_are_generic(client, monkeypatch):
    from creditwise import predictor
    monkeypatch.setattr(predictor, "predict", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("/secret/path boom")))
    r = client.post("/api/predict", json={"inputs": CORE})
    assert r.status_code == 500 and "secret" not in r.text and "boom" not in r.text
