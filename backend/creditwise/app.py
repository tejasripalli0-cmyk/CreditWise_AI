"""FastAPI app. Stateless: no database, no files written, applicant data is never logged or stored."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import analytics
from .inputs import InputError
from .metadata import build_features_payload, build_model_payload
from .model_store import ModelLoadError, get_bundle
from .schemas import ErrorResponse, PredictRequest, PredictResponse

log = logging.getLogger("creditwise")
MAX_BODY_BYTES = 32_768  # a full 125-field request is well under 10 KB

app = FastAPI(title="CreditWise AI API", version="1.0.0", docs_url="/api/docs", redoc_url=None,
              openapi_url="/api/openapi.json")


def _error(status: int, code: str, message: str, errors: list | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": {"code": code, "message": message, "errors": errors or []}})


@app.middleware("http")
async def guard(request: Request, call_next):
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        return _error(413, "payload_too_large", "The request is too large.")
    response = await call_next(request)
    response.headers.update({
        "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
        "Cache-Control": response.headers.get("Cache-Control", "no-store"),
    })
    return response


@app.exception_handler(InputError)
async def input_error_handler(_: Request, exc: InputError):
    return _error(422, "invalid_input", exc.message, exc.errors)


@app.exception_handler(RequestValidationError)
async def schema_error_handler(_: Request, exc: RequestValidationError):
    # FastAPI's default response echoes the submitted values; build one that does not.
    errors = [{"field": str(e["loc"][-1]) if e.get("loc") else "request", "message": str(e.get("msg", "Invalid value."))[:160]}
              for e in exc.errors()[:20]]
    return _error(422, "invalid_request", "The request format is not valid.", errors)


@app.exception_handler(ModelLoadError)
async def model_error_handler(_: Request, exc: ModelLoadError):
    log.error("model load failed: %s", type(exc).__name__)
    return _error(503, "model_unavailable", "The prediction model is temporarily unavailable.")


@app.exception_handler(Exception)
async def unexpected_handler(_: Request, exc: Exception):
    log.error("unexpected error: %s", type(exc).__name__)  # type only: never the message, traceback or inputs
    return _error(500, "internal_error", "The service hit an unexpected problem. Please try again.")


@app.get("/api/health")
def health(deep: bool = False):
    """Light by default. `?deep=true` loads the model and runs one real prediction."""
    out = {"status": "ok", "service": "creditwise-api", "model_loaded": get_bundle.cache_info().currsize > 0}
    if deep:
        from .predictor import predict
        result = predict({"EXT_SOURCE_2": 0.5}, explain=False)
        out.update(model_loaded=True, model_ok=0.0 <= result["prediction"]["probability"] <= 1.0)
    return out


@app.get("/api/model")
def model_info():
    return build_model_payload(get_bundle())


@app.get("/api/features")
def features():
    return build_features_payload(get_bundle())


@app.get("/api/analytics")
def analytics_data():
    resp = JSONResponse(analytics.build_analytics_payload())
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@app.post("/api/predict", response_model=PredictResponse, responses={422: {"model": ErrorResponse}})
def predict_endpoint(body: PredictRequest):
    from .predictor import predict
    return predict(body.inputs, explain=body.explain, top_n=body.top_n)
