"""Human-friendly metadata for the model's ORIGINAL input features.

This file only describes features (labels, groups, units, sane ranges). It never
decides which features exist: `model_store` validates this catalog against the
saved pickle, so a feature that is not in the model cannot be shown, and every
model feature must have an entry here (enforced by the test-suite).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

DAYS_PER_YEAR = 365.25  # reproduces the exported AGE_YEARS / EMPLOYMENT_YEARS medians

G_PERSONAL = "Personal information"
G_WORK = "Employment and income"
G_CREDIT = "Credit and loan information"
G_FAMILY = "Education and family"
G_PROPERTY = "Property information"
G_EXTERNAL = "External credit indicators"
G_OTHER = "Other application details"
GROUPS = [G_PERSONAL, G_WORK, G_CREDIT, G_FAMILY, G_PROPERTY, G_EXTERNAL, G_OTHER]

YES_NO_CAT = {"Y": "Yes", "N": "No"}
CHOICE_LABELS = {
    "CODE_GENDER": {"F": "Female", "M": "Male"},
    "FLAG_OWN_CAR": YES_NO_CAT,
    "FLAG_OWN_REALTY": YES_NO_CAT,
    "EMERGENCYSTATE_MODE": {"Yes": "Yes", "No": "No"},
    "WEEKDAY_APPR_PROCESS_START": {
        d: d.capitalize() for d in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
    },
}


@dataclass(frozen=True)
class Spec:
    label: str
    description: str
    group: str
    kind: str = "number"            # number | integer | flag | category
    unit: Optional[str] = None
    min: Optional[float] = None     # bounds in USER units (before `sign` is applied)
    max: Optional[float] = None
    step: Optional[float] = None
    sign: int = 1                   # -1: user enters positive "days before application"; model stores negative
    featured: bool = False
    derived: bool = False
    keywords: tuple = field(default_factory=tuple)


def _s(label, description, group, **kw) -> Spec:
    return Spec(label=label, description=description, group=group, **kw)


CATALOG: dict[str, Spec] = {
    # ---- featured (always visible on the form) -------------------------------------------------
    "AGE_YEARS": _s("Age", "Applicant age in years. Also fills 'Days since birth' automatically.", G_PERSONAL,
                    unit="years", min=18, max=100, step=1, featured=True, derived=True,
                    keywords=("birthday", "old", "years")),
    "AMT_INCOME_TOTAL": _s("Annual income", "Total yearly income of the applicant.", G_WORK, unit="currency",
                           min=1, max=1e9, step=1000, featured=True, keywords=("salary", "earnings", "wage")),
    "AMT_CREDIT": _s("Credit amount", "Total amount of the loan being applied for.", G_CREDIT, unit="currency",
                     min=1, max=1e9, step=1000, featured=True, keywords=("loan", "principal")),
    "EMPLOYMENT_YEARS": _s("Employment years", "Years in the current job. Also fills 'Days employed' automatically.",
                           G_WORK, unit="years", min=0, max=60, step=0.5, featured=True, derived=True,
                           keywords=("job", "tenure", "work")),
    "AMT_ANNUITY": _s("Annual instalment", "Loan annuity: the regular repayment amount for this loan, as used by the model.",
                      G_CREDIT, unit="currency", min=1, max=1e8, step=500, featured=True,
                      keywords=("emi", "repayment", "payment", "annuity", "instalment")),
    "AMT_GOODS_PRICE": _s("Goods price", "Price of the goods the loan finances (consumer loans).", G_CREDIT,
                          unit="currency", min=1, max=1e9, step=1000, featured=True, keywords=("purchase", "item")),

    # ---- personal --------------------------------------------------------------------------------
    "CODE_GENDER": _s("Gender", "Gender recorded on the application.", G_PERSONAL, kind="category"),
    "DAYS_BIRTH": _s("Days since birth", "Applicant age expressed as days before the application (enter a positive number).",
                     G_PERSONAL, unit="days", min=6570, max=36500, step=1, sign=-1, derived=True, keywords=("age", "birth")),
    "DAYS_REGISTRATION": _s("Days since registration changed", "Days before the application that the registration was last changed.",
                            G_PERSONAL, unit="days", min=0, max=30000, step=1, sign=-1),
    "DAYS_ID_PUBLISH": _s("Days since ID document changed", "Days before the application that the identity document was changed.",
                          G_PERSONAL, unit="days", min=0, max=30000, step=1, sign=-1, keywords=("identity", "passport")),
    "DAYS_LAST_PHONE_CHANGE": _s("Days since phone changed", "Days before the application that the phone number was changed.",
                                 G_PERSONAL, unit="days", min=0, max=30000, step=1, sign=-1, keywords=("mobile", "number")),
    "FLAG_MOBIL": _s("Mobile phone provided", "Whether a mobile phone number was provided.", G_PERSONAL, kind="flag"),
    "FLAG_EMP_PHONE": _s("Work phone provided", "Whether a work phone number was provided.", G_PERSONAL, kind="flag"),
    "FLAG_WORK_PHONE": _s("Home phone provided (work flag)", "Whether a work-related home phone was provided.", G_PERSONAL, kind="flag"),
    "FLAG_CONT_MOBILE": _s("Mobile phone reachable", "Whether the mobile phone was reachable.", G_PERSONAL, kind="flag"),
    "FLAG_PHONE": _s("Home phone provided", "Whether a home phone number was provided.", G_PERSONAL, kind="flag"),
    "FLAG_EMAIL": _s("Email provided", "Whether an email address was provided.", G_PERSONAL, kind="flag"),

    # ---- employment & income ---------------------------------------------------------------------
    "NAME_INCOME_TYPE": _s("Income type", "Main source of income.", G_WORK, kind="category",
                           keywords=("pensioner", "working", "student")),
    "OCCUPATION_TYPE": _s("Occupation", "Occupation of the applicant.", G_WORK, kind="category", keywords=("profession", "job")),
    "ORGANIZATION_TYPE": _s("Employer type", "Type of organisation where the applicant works.", G_WORK, kind="category",
                            keywords=("company", "employer", "industry")),
    "DAYS_EMPLOYED": _s("Days employed", "Days before the application that the current employment started (enter a positive number).",
                        G_WORK, unit="days", min=0, max=30000, step=1, sign=-1, derived=True, keywords=("tenure", "job")),

    # ---- credit & loan ---------------------------------------------------------------------------
    "NAME_CONTRACT_TYPE": _s("Loan type", "Cash loan or revolving loan.", G_CREDIT, kind="category"),
    "NAME_TYPE_SUITE": _s("Accompanied by", "Who accompanied the client when applying.", G_CREDIT, kind="category"),
    "CREDIT_INCOME_RATIO": _s("Credit-to-income ratio", "Credit amount divided by annual income. Calculated automatically when both are entered.",
                              G_CREDIT, unit="ratio", min=0, max=1000, step=0.01, derived=True, keywords=("leverage",)),
    "ANNUITY_INCOME_RATIO": _s("Instalment-to-income ratio", "Annual instalment divided by annual income. Calculated automatically when both are entered.",
                               G_CREDIT, unit="ratio", min=0, max=100, step=0.01, derived=True, keywords=("burden", "affordability")),
    "GOODS_CREDIT_RATIO": _s("Goods-to-credit ratio", "Goods price divided by credit amount. Calculated automatically when both are entered.",
                             G_CREDIT, unit="ratio", min=0, max=100, step=0.01, derived=True),
    "WEEKDAY_APPR_PROCESS_START": _s("Application weekday", "Weekday the application was started.", G_CREDIT, kind="category"),
    "HOUR_APPR_PROCESS_START": _s("Application hour", "Hour of day (0-23) the application was started.", G_CREDIT,
                                  kind="integer", unit="hour", min=0, max=23, step=1),

    # ---- education & family ----------------------------------------------------------------------
    "NAME_EDUCATION_TYPE": _s("Education level", "Highest education level reached.", G_FAMILY, kind="category",
                              keywords=("degree", "school", "university")),
    "NAME_FAMILY_STATUS": _s("Family status", "Marital / family status.", G_FAMILY, kind="category",
                             keywords=("married", "single", "widow")),
    "CNT_CHILDREN": _s("Number of children", "Number of children of the applicant.", G_FAMILY, kind="integer", min=0, max=20, step=1),
    "CNT_FAM_MEMBERS": _s("Family members", "Number of family members.", G_FAMILY, kind="integer", min=1, max=25, step=1),

    # ---- property --------------------------------------------------------------------------------
    "FLAG_OWN_CAR": _s("Owns a car", "Whether the applicant owns a car.", G_PROPERTY, kind="category"),
    "FLAG_OWN_REALTY": _s("Owns a house or flat", "Whether the applicant owns real estate.", G_PROPERTY, kind="category",
                          keywords=("home", "property")),
    "OWN_CAR_AGE": _s("Car age", "Age of the applicant's car in years.", G_PROPERTY, unit="years", min=0, max=100, step=1),
    "NAME_HOUSING_TYPE": _s("Housing type", "How the applicant is housed.", G_PROPERTY, kind="category", keywords=("rent", "parents")),
    "REGION_POPULATION_RELATIVE": _s("Region population (normalised)", "Normalised population of the region (higher = more populated).",
                                     G_PROPERTY, min=0, max=1, step=0.001),
    "FONDKAPREMONT_MODE": _s("Building repair fund type", "Capital-repair fund type of the building (mode).", G_PROPERTY, kind="category"),
    "HOUSETYPE_MODE": _s("Building type", "Type of housing building (mode).", G_PROPERTY, kind="category"),
    "WALLSMATERIAL_MODE": _s("Wall material", "Main wall material of the building (mode).", G_PROPERTY, kind="category"),
    "EMERGENCYSTATE_MODE": _s("Emergency state of building", "Whether the building is in an emergency state (mode).", G_PROPERTY, kind="category"),
    "TOTALAREA_MODE": _s("Total area (normalised)", "Normalised total area of the building (mode).", G_PROPERTY, min=0, max=1, step=0.001),

    # ---- external indicators ---------------------------------------------------------------------
    "EXT_SOURCE_1": _s("External source score 1", "Normalised score (0-1) from external data source 1. Higher generally goes with lower recorded difficulty.",
                       G_EXTERNAL, min=0, max=1, step=0.01, keywords=("score", "bureau", "rating", "external")),
    "EXT_SOURCE_2": _s("External source score 2", "Normalised score (0-1) from external data source 2.",
                       G_EXTERNAL, min=0, max=1, step=0.01, keywords=("score", "bureau", "rating", "external")),
    "EXT_SOURCE_3": _s("External source score 3", "Normalised score (0-1) from external data source 3.",
                       G_EXTERNAL, min=0, max=1, step=0.01, keywords=("score", "bureau", "rating", "external")),
    "REGION_RATING_CLIENT": _s("Region rating", "Lender's rating (1-3) of the applicant's region.", G_EXTERNAL,
                               kind="integer", min=1, max=3, step=1),
    "REGION_RATING_CLIENT_W_CITY": _s("Region rating (with city)", "Lender's rating (1-3) of the region, taking the city into account.",
                                      G_EXTERNAL, kind="integer", min=1, max=3, step=1),
    "OBS_30_CNT_SOCIAL_CIRCLE": _s("Social circle observations (30 days)", "People in the applicant's surroundings observed 30+ days past due.",
                                   G_EXTERNAL, kind="integer", min=0, max=500, step=1),
    "DEF_30_CNT_SOCIAL_CIRCLE": _s("Social circle defaults (30 days)", "People in the applicant's surroundings who defaulted at 30+ days past due.",
                                   G_EXTERNAL, kind="integer", min=0, max=500, step=1),
    "OBS_60_CNT_SOCIAL_CIRCLE": _s("Social circle observations (60 days)", "People in the applicant's surroundings observed 60+ days past due.",
                                   G_EXTERNAL, kind="integer", min=0, max=500, step=1),
    "DEF_60_CNT_SOCIAL_CIRCLE": _s("Social circle defaults (60 days)", "People in the applicant's surroundings who defaulted at 60+ days past due.",
                                   G_EXTERNAL, kind="integer", min=0, max=500, step=1),
    "AMT_REQ_CREDIT_BUREAU_HOUR": _s("Bureau enquiries: last hour", "Credit-bureau enquiries in the hour before the application.",
                                     G_EXTERNAL, kind="integer", min=0, max=1000, step=1),
    "AMT_REQ_CREDIT_BUREAU_DAY": _s("Bureau enquiries: last day", "Credit-bureau enquiries in the day before the application.",
                                    G_EXTERNAL, kind="integer", min=0, max=1000, step=1),
    "AMT_REQ_CREDIT_BUREAU_WEEK": _s("Bureau enquiries: last week", "Credit-bureau enquiries in the week before the application.",
                                     G_EXTERNAL, kind="integer", min=0, max=1000, step=1),
    "AMT_REQ_CREDIT_BUREAU_MON": _s("Bureau enquiries: last month", "Credit-bureau enquiries in the month before the application (excluding the last week).",
                                    G_EXTERNAL, kind="integer", min=0, max=1000, step=1),
    "AMT_REQ_CREDIT_BUREAU_QRT": _s("Bureau enquiries: last quarter", "Credit-bureau enquiries in the quarter before the application (excluding the last month).",
                                    G_EXTERNAL, kind="integer", min=0, max=1000, step=1),
    "AMT_REQ_CREDIT_BUREAU_YEAR": _s("Bureau enquiries: last year", "Credit-bureau enquiries in the year before the application (excluding the last quarter).",
                                     G_EXTERNAL, kind="integer", min=0, max=1000, step=1),

    # ---- other application details (address-mismatch flags) --------------------------------------
    "REG_REGION_NOT_LIVE_REGION": _s("Registered region differs from contact region", "Permanent and contact addresses differ at region level.", G_OTHER, kind="flag"),
    "REG_REGION_NOT_WORK_REGION": _s("Registered region differs from work region", "Permanent and work addresses differ at region level.", G_OTHER, kind="flag"),
    "LIVE_REGION_NOT_WORK_REGION": _s("Contact region differs from work region", "Contact and work addresses differ at region level.", G_OTHER, kind="flag"),
    "REG_CITY_NOT_LIVE_CITY": _s("Registered city differs from contact city", "Permanent and contact addresses differ at city level.", G_OTHER, kind="flag"),
    "REG_CITY_NOT_WORK_CITY": _s("Registered city differs from work city", "Permanent and work addresses differ at city level.", G_OTHER, kind="flag"),
    "LIVE_CITY_NOT_WORK_CITY": _s("Contact city differs from work city", "Contact and work addresses differ at city level.", G_OTHER, kind="flag"),
}

# ---- families generated programmatically (keeps this file readable) ---------------------------------
_BUILDING_BASES = {
    "APARTMENTS": "Apartment size", "BASEMENTAREA": "Basement area",
    "YEARS_BEGINEXPLUATATION": "Years since building put into use", "YEARS_BUILD": "Building age",
    "COMMONAREA": "Common area", "ELEVATORS": "Elevators", "ENTRANCES": "Entrances", "FLOORSMAX": "Maximum floors",
    "FLOORSMIN": "Minimum floors", "LANDAREA": "Land area", "LIVINGAPARTMENTS": "Living apartments",
    "LIVINGAREA": "Living area", "NONLIVINGAPARTMENTS": "Non-living apartments", "NONLIVINGAREA": "Non-living area",
}
_SUFFIX = {"AVG": "average", "MODE": "mode", "MEDI": "median"}
for _base, _name in _BUILDING_BASES.items():
    for _suf, _stat in _SUFFIX.items():
        CATALOG[f"{_base}_{_suf}"] = _s(
            f"{_name} ({_stat})",
            f"Normalised ({_stat}) building statistic: {_name.lower()}. Value between 0 and 1.",
            G_PROPERTY, min=0, max=1, step=0.001, keywords=("building", "housing", "apartment"))

for _n in range(2, 22):
    CATALOG[f"FLAG_DOCUMENT_{_n}"] = _s(f"Document {_n} provided", f"Whether document {_n} was provided with the application.",
                                        G_OTHER, kind="flag", keywords=("paperwork",))

# Derived features. Formulas were inferred by reproducing the fitted medians stored in the pickle
# (e.g. median AGE_YEARS 43.0527 x 365.25 = 15725 = median DAYS_BIRTH). They are NOT stored in the pickle.
DERIVATIONS = [
    {"target": "AGE_YEARS", "requires": ["DAYS_BIRTH"], "formula": "-DAYS_BIRTH / 365.25"},
    {"target": "DAYS_BIRTH", "requires": ["AGE_YEARS"], "formula": "-AGE_YEARS * 365.25"},
    {"target": "EMPLOYMENT_YEARS", "requires": ["DAYS_EMPLOYED"], "formula": "-DAYS_EMPLOYED / 365.25"},
    {"target": "DAYS_EMPLOYED", "requires": ["EMPLOYMENT_YEARS"], "formula": "-EMPLOYMENT_YEARS * 365.25"},
    {"target": "CREDIT_INCOME_RATIO", "requires": ["AMT_CREDIT", "AMT_INCOME_TOTAL"], "formula": "AMT_CREDIT / AMT_INCOME_TOTAL"},
    {"target": "ANNUITY_INCOME_RATIO", "requires": ["AMT_ANNUITY", "AMT_INCOME_TOTAL"], "formula": "AMT_ANNUITY / AMT_INCOME_TOTAL"},
    {"target": "GOODS_CREDIT_RATIO", "requires": ["AMT_GOODS_PRICE", "AMT_CREDIT"], "formula": "AMT_GOODS_PRICE / AMT_CREDIT"},
]
