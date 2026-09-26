"""Reusable Phase 2 project-risk prediction interface for API/dashboard adapters."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.phase2 import (  # noqa: E402
    predict_cost_overrun,
    predict_project_risk,
    predict_schedule_overrun,
    score_ongoing_projects,
)

__all__ = [
    "predict_cost_overrun",
    "predict_project_risk",
    "predict_schedule_overrun",
    "score_ongoing_projects",
]
