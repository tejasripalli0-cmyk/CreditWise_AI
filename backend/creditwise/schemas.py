"""Typed request / response contracts for the API."""
from __future__ import annotations

from typing import Annotated, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, StrictStr

Scalar = Union[StrictBool, StrictInt, StrictFloat, StrictStr, None]
FieldName = Annotated[str, Field(max_length=64)]


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inputs: dict[FieldName, Scalar] = Field(
        description="Original model feature names mapped to values. Omit anything you do not know.",
        max_length=125)
    explain: bool = True
    top_n: int = Field(10, ge=3, le=25, description="How many features to list in the explanation.")


class RiskBand(BaseModel):
    key: str
    label: str
    description: str
    score_to_threshold_ratio: float


class PredictionOut(BaseModel):
    predicted_class: int
    label: str
    probability: float
    threshold: float
    above_threshold: bool
    risk_band: RiskBand
    probability_note: str


class CompletenessOut(BaseModel):
    total_features: int
    user_provided: int
    auto_derived: int
    assumed_default: int
    fraction_provided: float
    importance_coverage: float
    level: str
    user_fields: list[str]
    derived_fields: list[str]
    basis: str


class WarningOut(BaseModel):
    level: str
    code: str
    message: str


class ContributionOut(BaseModel):
    feature: str
    label: str
    value: Union[str, float]
    source: str  # entered | calculated | assumed
    contribution: float
    direction: str


class ExplanationOut(BaseModel):
    available: bool
    reason: Optional[str] = None
    method: Optional[str] = None
    base_value: Optional[float] = None
    base_probability: Optional[float] = None
    output_value: Optional[float] = None
    contributions: list[ContributionOut] = []
    other_contribution: Optional[float] = None
    other_count: Optional[int] = None
    from_provided_fields: Optional[float] = None
    from_assumed_defaults: Optional[float] = None
    additivity_error: Optional[float] = None
    reading_guide: Optional[str] = None


class ModelRef(BaseModel):
    name: str
    target_mapping: dict[str, str]


class PredictResponse(BaseModel):
    prediction: PredictionOut
    completeness: CompletenessOut
    warnings: list[WarningOut]
    explanation: ExplanationOut
    summary: list[str]
    model: ModelRef


class FieldError(BaseModel):
    field: str
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    errors: list[FieldError] = []


class ErrorResponse(BaseModel):
    detail: ErrorDetail
