import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore", category=UserWarning)

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def bundle():
    from creditwise.model_store import get_bundle
    return get_bundle()


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from api.index import app
    return TestClient(app, raise_server_exceptions=False)


CORE = {"AGE_YEARS": 35, "AMT_INCOME_TOTAL": 180000, "AMT_CREDIT": 900000, "EMPLOYMENT_YEARS": 4,
        "AMT_ANNUITY": 40000, "AMT_GOODS_PRICE": 810000}
EXT = {"EXT_SOURCE_1": 0.25, "EXT_SOURCE_2": 0.20, "EXT_SOURCE_3": 0.15}
