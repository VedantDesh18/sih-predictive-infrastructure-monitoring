"""Transparent prototype risk engine.

This module deliberately uses explainable, calculation-based indicators rather
than claiming an ML model.  Its output boundary is intentionally stable so a
future statistical/XGBoost model can replace the scoring implementation.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.models.project import Project

SYNTHETIC_LABEL = "Synthetic Demonstration Data"


def _clamp(value: float) -> int:
    return round(max(0, min(100, value)))


def _severity(score: int) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 65:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def _number(value: Decimal | float) -> float:
    return round(float(value), 2)


def calculate_risk(project: Project) -> dict[str, Any]:
    """Calculate reproducible project-risk features, scores and explanations."""
    approved_cost = float(project.approved_cost)
    revised_cost = float(project.revised_cost)
    expenditure = float(project.expenditure)
    cost_growth = ((revised_cost - approved_cost) / approved_cost) * 100
    progress_variance = project.planned_progress - project.physical_progress
    milestone_delay = max(
        (project.expected_completion - project.planned_completion).days, 0
    )
    expenditure_ratio = (expenditure / revised_cost) * 100
    expenditure_acceleration = max(expenditure_ratio - project.physical_progress, 0)

    cost_risk = _clamp(cost_growth * 3.56 + expenditure_acceleration * 1.2)
    schedule_risk = _clamp(milestone_delay / 4 + max(progress_variance, 0))
    execution_risk = _clamp(
        max(progress_variance, 0) * 2 + expenditure_acceleration * 0.76
    )

    history = project.risk_history
    scores = [int(point["risk"]) for point in history]
    velocity = scores[-1] - scores[-2] if len(scores) >= 2 else 0
    previous_velocity = scores[-2] - scores[-3] if len(scores) >= 3 else 0
    acceleration = velocity - previous_velocity
    recent_change = scores[-1] - scores[-3] if len(scores) >= 3 else velocity
    if velocity >= 8 or recent_change >= 16:
        trend = "RAPIDLY WORSENING"
    elif velocity >= 3:
        trend = "WORSENING"
    elif velocity <= -3:
        trend = "IMPROVING"
    else:
        trend = "STABLE"

    escalation_adjustment = min(5, max(0, velocity * 0.26))
    overall_risk = _clamp(
        cost_risk * 0.40
        + schedule_risk * 0.35
        + execution_risk * 0.25
        + escalation_adjustment
    )

    driver_candidates = [
        ("Schedule Slippage", (milestone_delay + 9) // 10),
        ("Progress Variance", round(max(progress_variance, 0) * 0.7)),
        ("Cost Growth", round(max(cost_growth, 0))),
        ("Expenditure Acceleration", round(expenditure_acceleration * 0.44)),
    ]
    drivers = [
        {"driver": driver, "contribution": contribution}
        for driver, contribution in driver_candidates
        if contribution > 0
    ]
    drivers.sort(key=lambda item: item["contribution"], reverse=True)

    alerts: list[dict[str, Any]] = []
    if cost_growth >= 10:
        alerts.append(
            {
                "type": "COST OVERRUN WARNING",
                "severity": _severity(cost_risk),
                "reason": "Approved-to-revised cost growth is materially elevated.",
                "supporting_metric": f"Cost growth: {cost_growth:.1f}%",
            }
        )
    if milestone_delay >= 90:
        alerts.append(
            {
                "type": "SCHEDULE DELAY WARNING",
                "severity": _severity(schedule_risk),
                "reason": "Expected completion has moved beyond the approved schedule.",
                "supporting_metric": f"Milestone delay: {milestone_delay} days",
            }
        )
    if execution_risk >= 55:
        alerts.append(
            {
                "type": "EXECUTION RISK WARNING",
                "severity": _severity(execution_risk),
                "reason": "Physical delivery is lagging expenditure and plan.",
                "supporting_metric": f"Progress variance: {progress_variance:.1f} percentage points",
            }
        )
    if trend == "RAPIDLY WORSENING":
        baseline = scores[-3] if len(scores) >= 3 else scores[0]
        alerts.append(
            {
                "type": "RAPID RISK ESCALATION",
                "severity": "CRITICAL" if overall_risk >= 90 else "HIGH",
                "reason": f"Risk increased from {baseline} to {scores[-1]} over the last 3 reporting periods.",
                "supporting_metric": f"Risk velocity: +{velocity} points per period",
            }
        )

    alerts.sort(key=lambda alert: alert["type"] != "RAPID RISK ESCALATION")

    return {
        "features": {
            "cost_growth": round(cost_growth, 1),
            "progress_variance": round(progress_variance, 1),
            "schedule_variance": milestone_delay,
            "expenditure_ratio": round(expenditure_ratio, 1),
            "milestone_delay": milestone_delay,
            "risk_trend": trend,
        },
        "scores": {
            "cost_risk": cost_risk,
            "schedule_risk": schedule_risk,
            "execution_risk": execution_risk,
            "overall_risk": overall_risk,
            "risk_level": _severity(overall_risk),
        },
        "trajectory": {
            "history": history,
            "risk_velocity": velocity,
            "risk_acceleration": acceleration,
            "trend": trend,
        },
        "drivers": drivers[:4],
        "alerts": alerts,
        "predictions": {
            "estimated_cost_overrun": round(max(cost_growth, 0), 1),
            "delay_probability": min(
                99,
                round(schedule_risk * 0.75 + execution_risk * 0.30),
            ),
        },
    }


def project_payload(project: Project, include_risk: bool = True) -> dict[str, Any]:
    """Return the API representation used by both table and detail routes."""
    payload: dict[str, Any] = {
        "project_id": project.paimana_project_id,
        "project_name": project.name,
        "ministry": project.ministry,
        "sector": project.sector,
        "agency": project.agency,
        "location": project.location,
        "approved_cost": _number(project.approved_cost),
        "revised_cost": _number(project.revised_cost),
        "expenditure": _number(project.expenditure),
        "planned_progress": project.planned_progress,
        "physical_progress": project.physical_progress,
        "planned_completion": project.planned_completion.isoformat(),
        "expected_completion": project.expected_completion.isoformat(),
        "condition": project.condition,
        "data_source": (
            SYNTHETIC_LABEL if project.is_synthetic else "PAIMANA Real Ongoing Dataset (100 Projects)"
        ),
    }
    if include_risk:
        payload["risk"] = calculate_risk(project)
        if project.ml_risk_predictions:
            payload["ml_risk"] = project.ml_risk_predictions
            payload["ml_alerts"] = project.ml_alerts or []
    return payload
