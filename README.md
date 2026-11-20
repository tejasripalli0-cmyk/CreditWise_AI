# CreditWise AI

Credit risk and loan payment difficulty prediction: a React (Vite) frontend and a FastAPI inference API that run the **original, unmodified** Gradient Boosting model exported from Google Colab. One GitHub repository, one Vercel project.

> **Not a CIBIL score and not a lending decision.** The model is trained on the public Home Credit Default Risk dataset. The target is *recorded payment difficulty* (0 = none recorded, 1 = recorded). It is an educational/research project; fairness was not assessed and it must not be used to make decisions about real people.

## What is in the repo

```
CreditWise_AI/
├── api/index.py              Vercel entry point (exports the FastAPI `app`)
├── backend/creditwise/       Inference package
│   ├── model_store.py        Loads + validates the original pickle once per process
│   ├── catalog.py            Labels / groups / ranges for the 125 original inputs
│   ├── inputs.py             Validation, derived features, full 125-column row builder
│   ├── predictor.py          Score, saved threshold, completeness, SHAP explanation
│   ├── analytics.py          Reads the exported CSVs (stdlib only)
│   ├── metadata.py, schemas.py, app.py
├── frontend/                 React + Vite (Recharts, lucide-react)
├── model_assets/             Your Colab export, untouched (model, 5 CSVs, 2 PNGs)
├── tests/                    69 pytest tests that use the real model
├── requirements.txt          Runtime deps (what Vercel installs)
├── requirements-dev.txt      + pytest, httpx, uvicorn
├── vercel.json, .python-version
```

The model file is never copied into anything served to browsers. `frontend/scripts/sync-assets.mjs` copies **only the two PNGs** into `frontend/public/analytics/` at build time.

## What was found when inspecting the model

| Item | Finding |
|---|---|
| Container | `dict` with `model, preprocessor, threshold, model_name, feature_names, transformed_feature_names, target_mapping` |
| Model | `GradientBoostingClassifier` (100 trees, depth 3, lr 0.1, min_samples_leaf 20) |
| Threshold | `0.14999999999999997` (0.15). Used as saved, never 0.5 |
| Inputs | 125 original features (109 numeric, 16 categorical) → 247 encoded columns |
| Numeric missing values | `SimpleImputer(median)` then `StandardScaler` |
| Categorical missing values | `SimpleImputer(most_frequent)` then `OneHotEncoder(handle_unknown='ignore')` |
| Unknown categories | Ignored by the encoder; the API also rejects them |
| Target mapping | `{0: 'No recorded payment difficulty', 1: 'Recorded payment difficulty'}` |
| SHA-256 of the pickle | `2c876bc25782ee945018a995e887b69eb745e8c19a50df0fd43f41511282a1c1` (a test fails if it changes) |

Findings that shaped the implementation:

1. **`None` is not "missing" for categoricals.** scikit-learn's imputer only treats `np.nan` as missing in object columns. Using `None` silently turns all 16 categorical groups into all-zero one-hot vectors (a state never seen in training) and changes the prediction. The API builds blanks as `np.nan`, and a regression test (`test_regression_none_in_categorical_would_be_wrong`) guards it.
2. **Blank ≠ neutral.** A blank categorical is replaced by the most frequent training category (e.g. gender → `F`, education → `Secondary / secondary special`). The UI and results say so, and "assumed" fields are marked in the explanation because they still influence the score.
3. **The model barely uses raw `AMT_CREDIT` / `AMT_INCOME_TOTAL`;** it relies on derived ratios. So derived features are calculated automatically. The formulas are *inferred* from the stored medians (`AGE_YEARS = -DAYS_BIRTH/365.25`, `EMPLOYMENT_YEARS = -DAYS_EMPLOYED/365.25`, `CREDIT_INCOME_RATIO = AMT_CREDIT/AMT_INCOME_TOTAL`, `ANNUITY_INCOME_RATIO = AMT_ANNUITY/AMT_INCOME_TOTAL`, `GOODS_CREDIT_RATIO = AMT_GOODS_PRICE/AMT_CREDIT`); they are not stored in the pickle. Please confirm them against your notebook.
4. **SHAP works.** `TreeExplainer` runs on the saved model and pipeline; contributions are summed per original feature and checked to add up to the model output (error ~1e-15). If the check ever fails the explanation is withheld, not faked.
5. **Comparison vs final metrics are different operating points.** Gradient Boosting accuracy is 0.701 in `model_comparison.csv` but 0.856 in `final_model_metrics.csv` (threshold 0.15). The Analytics page says so. Only ROC-AUC and PR-AUC are directly comparable between the two.
6. **Test-set size** (20,000 rows, 1,615 positive) is not in a CSV. It is transcribed from `confusion_matrix.png`, and a test confirms those four counts reproduce the saved accuracy, precision and recall exactly.

## Run locally

Requires Python 3.12 and Node 20.19+ (Node 22 recommended).

### Windows PowerShell

```powershell
# 1) Python environment + API dependencies
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements-dev.txt

# 2) Frontend dependencies
cd frontend
npm install
cd ..

# 3) Run the tests (uses the real model)
python -m pytest

# 4) Start the API (terminal 1, from the repo root)
python -m uvicorn api.index:app --reload --port 8000

# 5) Start the frontend (terminal 2)
cd frontend
npm run dev                            # open http://localhost:5173
```

In VS Code you can also run the task **Run both** (Terminal → Run Task).

### macOS / Linux

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
(cd frontend && npm install)
python -m pytest
python -m uvicorn api.index:app --reload --port 8000     # terminal 1
(cd frontend && npm run dev)                              # terminal 2
```

Vite proxies `/api/*` to `http://127.0.0.1:8000`. Interactive API docs: <http://localhost:8000/api/docs>.

### Build the frontend

```powershell
cd frontend
npm run build        # output in frontend/dist
npm run preview
```

### Run with the Vercel CLI (closest to production)

```powershell
npm i -g vercel
vercel login
vercel dev
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness (`?deep=true` also runs one real prediction) |
| GET | `/api/model` | Model type, parameters, threshold, preprocessing, library versions |
| GET | `/api/features` | The 125 original inputs: labels, groups, ranges, real categories |
| GET | `/api/analytics` | Exported CSV results as JSON |
| POST | `/api/predict` | `{ "inputs": { "AGE_YEARS": 35, "EXT_SOURCE_2": 0.4 }, "explain": true, "top_n": 10 }` |

`/api/predict` accepts any subset of the original features. Days-based fields (`DAYS_BIRTH`, `DAYS_EMPLOYED`, …) are entered as **positive days before the application**. Errors return `{ "detail": { "code", "message", "errors": [{ "field", "message" }] } }` and never echo submitted values or internal paths.

## How partial input works

1. Build a 1 × 125 DataFrame with every original column in the saved order.
2. Numeric blanks are `NaN`; categorical blanks are `np.nan`.
3. Put the user's validated values in their columns; calculate derived features only when their inputs exist and the user did not enter them.
4. Run the **saved** `ColumnTransformer`, then the saved model's `predict_proba`.
5. Class 1 if `probability >= saved threshold`.

Nothing is dropped, zero-filled, retrained or stored.

**Information coverage** is the share of the model's total global SHAP importance (grouped by original feature) carried by the fields you provided or that were calculated from them. The six headline fields alone cover about 25 %; adding the three external source scores lifts that to about 64 %.

**Score bands** (Low / Moderate / Elevated / High) are descriptive buckets at 0.5×, 1× and 2× the saved threshold. They are not calibrated probabilities.

## Deploy

### 1) Push to GitHub

```powershell
git init
git add .
git status        # confirm .venv, node_modules and frontend/dist are NOT listed, and model_assets/creditwise_model.pkl IS
git commit -m "CreditWise AI"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

Create the empty repository on github.com first (no README/licence). The `.pkl` must be committed because the API loads it at runtime.

### 2) Deploy on Vercel (Hobby)

1. vercel.com → **Add New… → Project** → import the GitHub repository.
2. Leave **Root Directory** as the repository root. `vercel.json` sets the framework to *Other*, the build command and `frontend/dist` as the output.
3. No environment variables are needed. Click **Deploy**.
4. Check `https://<your-app>.vercel.app/api/health?deep=true`, then try a prediction.

Or from the CLI: `vercel --prod`.

### Hobby-plan fit (measured, not guessed)

| Item | Value |
|---|---|
| Python bundle limit | 500 MB uncompressed (Vercel docs, checked July 2026) |
| `pip install -r requirements.txt`, unstripped | ≈ 373 MB site-packages + ≈ 3 MB code/assets |
| Stripped of caches/tests | ≈ 239 MB |
| Frontend | static files from the CDN, not in the function |

`excludeFiles` in `vercel.json` keeps `frontend/`, `tests/` etc. out of the function. Cold starts are real: the first request after idle loads scikit-learn and the pickle (the UI warns about this). Expect a few seconds, then fast warm requests (~20 ms in local tests). Cold-start time on Vercel was **not measured**.

## Tests

```powershell
python -m pytest
```

69 tests cover model loading and integrity, metadata, a full 125-field prediction, many partial combinations, blank numeric and categorical handling (including the `None` trap), validation, threshold behaviour, derived features, SHAP additivity, CSV loading and reconciliation, and every endpoint (including privacy: no echoed values, no path leaks). A spy test asserts the saved preprocessor receives a 1 × 125 frame in the original column order.

## Compatibility

The model was exported with scikit-learn 1.6.1, NumPy 2.4.6, pandas 2.2.3, SciPy 1.16.3, joblib 1.6.0 (Python 3.13 in Colab). `requirements.txt` pins exactly those. This project was developed and tested on Python 3.12 and loads the pickle with **no version warnings**. If you change these versions, `/api/model` reports `libraries_match_export` and any load warnings.

## Limitations

- Precision at the saved threshold is ~25 %; most flagged applicants in the test data had no recorded difficulty.
- The score is not calibrated; do not treat it as a guaranteed probability.
- The model uses personal attributes (e.g. gender, education); fairness was not evaluated.
- Predictions from few details are less reliable; missing values are replaced with training medians/modes, not recovered.
- Derived-feature formulas are inferred (see above). The currency of the original amounts is not specified in the export.
- No `LICENSE` file is included because no licence was specified. Add one before publishing. The Home Credit dataset has its own terms.
