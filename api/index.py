"""Vercel entry point (Python runtime). Exposes the FastAPI ASGI app as `app`.

Routes are all under /api/*. Shared code lives in ../backend so it is not deployed as extra functions.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from creditwise.app import app  # noqa: E402,F401
