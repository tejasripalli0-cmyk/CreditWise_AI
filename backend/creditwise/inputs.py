"""Turns a partial, user-supplied dict into the full 125-column row the saved pipeline expects.

Design rules (all verified against the real pickle, see tests/):
* Every expected original column is present in the DataFrame; nothing is dropped at inference time.
* Unprovided numeric cells are float NaN and unprovided categorical cells are np.nan. The saved
  SimpleImputers (median / most_frequent) then fill them. ``None`` must NOT be used for categoricals:
  scikit-learn does not treat None in object columns as missing, which would one-hot encode every
  categorical group as all-zeros (an impossible state the model never saw during training).
* Nothing is replaced with arbitrary values such as zero.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .catalog import CATALOG, DAYS_PER_YEAR
from .model_store import ModelBundle

MAX_FIELDS = 125


class InputError(ValueError):
    """Validation failure. ``errors`` is a list of {field, message}; values are never echoed back."""

    def __init__(self, message: str, errors: list[dict] | None = None):
        super().__init__(message)
        self.message = message
        self.errors = errors or []


@dataclass
class PreparedInput:
    row: pd.DataFrame                                   # 1 x 125, original column order
    model_values: dict                                  # feature -> value in MODEL units (user + derived)
    user_fields: list = field(default_factory=list)     # entered by the user
    derived_fields: list = field(default_factory=list)  # auto-calculated from entered values
    warnings: list = field(default_factory=list)


def _parse_number(name: str, value: Any, integer: bool) -> float:
    if isinstance(value, bool):
        raise InputError("Enter a number.", [{"field": name, "message": "Enter a number."}])
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise InputError("Enter a number.", [{"field": name, "message": "Enter a valid number."}]) from None
    if not math.isfinite(num):
        raise InputError("Enter a finite number.", [{"field": name, "message": "Enter a finite number."}])
    if integer and num != int(num):
        raise InputError("Enter a whole number.", [{"field": name, "message": "Enter a whole number."}])
    return num


def _validate_one(name: str, value: Any, bundle: ModelBundle) -> Any:
    """Validate a single field and return its value in MODEL units."""
    spec = CATALOG[name]
    if spec.kind == "category":
        if not isinstance(value, str) or value not in bundle.categories[name]:
            options = bundle.categories[name]
            shown = ", ".join(options[:6]) + (", ..." if len(options) > 6 else "")
            raise InputError("Invalid choice.", [{"field": name, "message": f"Choose one of the listed options ({shown})."}])
        return value
    if spec.kind == "flag":
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        num = _parse_number(name, value, integer=True)
        if num not in (0.0, 1.0):
            raise InputError("Invalid flag.", [{"field": name, "message": "Choose Yes (1) or No (0)."}])
        return num
    num = _parse_number(name, value, integer=spec.kind == "integer")
    if spec.min is not None and num < spec.min or spec.max is not None and num > spec.max:
        lo = f"{spec.min:g}" if spec.min is not None else "-inf"
        hi = f"{spec.max:g}" if spec.max is not None else "inf"
        raise InputError("Out of range.", [{"field": name, "message": f"Must be between {lo} and {hi}."}])
    return num * spec.sign if spec.sign != 1 else num


def prepare_input(raw: dict, bundle: ModelBundle) -> PreparedInput:
    if not isinstance(raw, dict):
        raise InputError("Inputs must be an object of feature names and values.")
    if len(raw) > MAX_FIELDS:
        raise InputError("Too many fields submitted.")

    unknown = [k for k in raw if k not in CATALOG]
    if unknown:
        # Only echo back safe, short, printable names so no arbitrary text is reflected.
        safe = [str(k)[:40] for k in unknown[:5]]
        raise InputError("Unknown field(s) submitted.",
                         [{"field": k, "message": "This field is not an input of the saved model."} for k in safe])

    values, errors = {}, []
    for name, value in raw.items():
        if value is None or (isinstance(value, str) and value.strip() == ""):
            continue  # blank = "not provided"; the saved imputers handle it
        try:
            values[name] = _validate_one(name, value.strip() if isinstance(value, str) else value, bundle)
        except InputError as exc:
            errors.extend(exc.errors)
    if errors:
        raise InputError("Some values are invalid.", errors)
    if not values:
        raise InputError("Enter at least one applicant detail to get a prediction.")

    user_fields = list(values)
    derived_fields: list[str] = []
    warnings: list[dict] = []

    def derive(target, compute, *needs):
        if target in values or any(n not in values for n in needs):
            return  # never overwrite a manually entered value; skip if inputs are missing
        values[target] = compute(*(values[n] for n in needs))
        derived_fields.append(target)

    derive("DAYS_BIRTH", lambda a: -a * DAYS_PER_YEAR, "AGE_YEARS")
    derive("AGE_YEARS", lambda d: -d / DAYS_PER_YEAR, "DAYS_BIRTH")
    derive("DAYS_EMPLOYED", lambda y: -y * DAYS_PER_YEAR, "EMPLOYMENT_YEARS")
    derive("EMPLOYMENT_YEARS", lambda d: -d / DAYS_PER_YEAR, "DAYS_EMPLOYED")
    derive("CREDIT_INCOME_RATIO", lambda c, i: c / i, "AMT_CREDIT", "AMT_INCOME_TOTAL")
    derive("ANNUITY_INCOME_RATIO", lambda a, i: a / i, "AMT_ANNUITY", "AMT_INCOME_TOTAL")
    derive("GOODS_CREDIT_RATIO", lambda g, c: g / c, "AMT_GOODS_PRICE", "AMT_CREDIT")

    for name in derived_fields:
        spec = CATALOG[name]
        if spec.unit == "ratio" and spec.max is not None and values[name] > spec.max:
            warnings.append({"level": "warning", "code": "unusual_ratio",
                             "message": f"The calculated {spec.label.lower()} is unusually high; please double-check the amounts."})

    # Manual values that contradict each other are respected, but flagged.
    if {"AGE_YEARS", "DAYS_BIRTH"} <= set(user_fields) and abs(values["AGE_YEARS"] + values["DAYS_BIRTH"] / DAYS_PER_YEAR) > 1:
        warnings.append({"level": "warning", "code": "inconsistent_age",
                         "message": "Age and 'Days since birth' disagree by more than a year. Both were used as entered."})
    if {"EMPLOYMENT_YEARS", "DAYS_EMPLOYED"} <= set(user_fields) and abs(values["EMPLOYMENT_YEARS"] + values["DAYS_EMPLOYED"] / DAYS_PER_YEAR) > 1:
        warnings.append({"level": "warning", "code": "inconsistent_employment",
                         "message": "Employment years and 'Days employed' disagree by more than a year. Both were used as entered."})

    return PreparedInput(row=build_row(values, bundle), model_values=values, user_fields=user_fields,
                         derived_fields=derived_fields, warnings=warnings)


def build_row(values: dict, bundle: ModelBundle) -> pd.DataFrame:
    """Create the full-width row. Missing numeric -> float NaN; missing categorical -> np.nan (NOT None)."""
    data = {name: np.nan for name in bundle.feature_names}
    row = pd.DataFrame([data], columns=bundle.feature_names)
    row[bundle.numeric_cols] = row[bundle.numeric_cols].astype("float64")
    row[bundle.categorical_cols] = row[bundle.categorical_cols].astype("object")
    for name, value in values.items():
        row.at[0, name] = value
    if list(row.columns) != list(bundle.feature_names) or row.shape != (1, len(bundle.feature_names)):
        raise RuntimeError("Input row does not match the model schema.")
    return row


def to_user_units(name: str, value: Any) -> Any:
    """Model value -> the unit a person would type (undo the days-before sign flip)."""
    spec = CATALOG[name]
    if isinstance(value, str):
        return value
    return -value if spec.sign == -1 else value
