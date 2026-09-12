"""Regression coverage for the SIH judge-flow demonstration project."""

from app.services.risk_engine import calculate_risk
from app.services.synthetic_data import demo_project


def test_demo_corridor_has_the_expected_explainable_warning_profile():
    risk = calculate_risk(demo_project())

    assert risk["scores"] == {
        "cost_risk": 87,
        "schedule_risk": 81,
        "execution_risk": 73,
        "overall_risk": 84,
        "risk_level": "CRITICAL",
    }
    assert [point["risk"] for point in risk["trajectory"]["history"]] == [
        42,
        51,
        63,
        74,
        84,
    ]
    assert risk["trajectory"]["trend"] == "RAPIDLY WORSENING"
    assert risk["drivers"] == [
        {"driver": "Schedule Slippage", "contribution": 22},
        {"driver": "Progress Variance", "contribution": 19},
        {"driver": "Cost Growth", "contribution": 16},
        {"driver": "Expenditure Acceleration", "contribution": 11},
    ]
    assert risk["alerts"][0] == {
        "type": "RAPID RISK ESCALATION",
        "severity": "HIGH",
        "reason": "Risk increased from 63 to 84 over the last 3 reporting periods.",
        "supporting_metric": "Risk velocity: +10 points per period",
    }
