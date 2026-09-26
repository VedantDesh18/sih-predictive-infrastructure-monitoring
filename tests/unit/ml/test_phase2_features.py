from __future__ import annotations

import pandas as pd

from ml.phase2 import CATEGORICAL_FEATURES, NUMERIC_FEATURES, build_snapshot_features


def _snapshots(months: int = 8) -> pd.DataFrame:
    dates = pd.date_range("2022-01-01", periods=months, freq="MS")
    return pd.DataFrame(
        {
            "Project_ID": ["P-1"] * months,
            "Project_Name": ["Never a model feature"] * months,
            "Snapshot_Date": dates,
            "Sector": ["RAILWAYS"] * months,
            "Agency": ["AGENCY-A"] * months,
            "Project_Status": ["On Schedule"] * (months - 1) + ["Delayed"],
            "Date_of_Approval": [pd.Timestamp("2021-01-01")] * months,
            "Original_DoC": [pd.Timestamp("2023-01-01")] * months,
            "Revised_or_Anticipated_DoC": [pd.Timestamp("2023-03-01")] * months,
            "Original_Cost_Crore": [100.0] * months,
            "Revised_or_Anticipated_Cost_Crore": [110.0] * months,
            "Cumulative_Expenditure_Crore": [10.0 * (index + 1) for index in range(months)],
            "Milestone_Percent": [5.0 * (index + 1) for index in range(months)],
            "Physical_Progress (%)": [None] * (months - 1) + [40.0],
            "Milestones_Achieved": list(range(months)),
            "Milestones_Total": [20.0] * months,
            "Cost_Overrun_Percent": [999.0] * months,
            "Time_Overrun_Months": [999.0] * months,
        }
    )


def test_features_are_keyed_and_chronological() -> None:
    features = build_snapshot_features(_snapshots())
    assert len(features) == 8
    assert not features.duplicated(["Project_ID", "Snapshot_Date"]).any()
    assert features["Snapshot_Date"].is_monotonic_increasing
    assert set(NUMERIC_FEATURES + CATEGORICAL_FEATURES).issubset(features.columns)
    assert "Project_Name" not in NUMERIC_FEATURES + CATEGORICAL_FEATURES
    assert "Project_ID" not in NUMERIC_FEATURES + CATEGORICAL_FEATURES
    assert "Cost_Overrun_Percent" not in NUMERIC_FEATURES + CATEGORICAL_FEATURES
    assert "Time_Overrun_Months" not in NUMERIC_FEATURES + CATEGORICAL_FEATURES


def test_future_mutations_do_not_change_earlier_snapshot_features() -> None:
    original = _snapshots()
    baseline = build_snapshot_features(original)
    changed = original.copy()
    future_row = changed.index[-1]
    changed.loc[future_row, "Cumulative_Expenditure_Crore"] = 900_000.0
    changed.loc[future_row, "Milestone_Percent"] = 99.0
    changed.loc[future_row, "Project_Status"] = "Completed"
    changed.loc[future_row, "Revised_or_Anticipated_DoC"] = pd.Timestamp("2040-01-01")
    changed_features = build_snapshot_features(changed)
    pd.testing.assert_frame_equal(
        baseline.iloc[:-1].reset_index(drop=True),
        changed_features.iloc[:-1].reset_index(drop=True),
        check_dtype=False,
    )


def test_progress_percentages_outside_valid_range_are_missing() -> None:
    source = _snapshots()
    source.loc[7, "Milestone_Percent"] = 155.0
    features = build_snapshot_features(source)
    assert pd.isna(features.loc[7, "milestone_progress_pct"])


def test_status_volatility_uses_only_six_month_window() -> None:
    source = _snapshots()
    source.loc[1, "Project_Status"] = "Delayed"
    features = build_snapshot_features(source)
    assert features.loc[7, "status_changes_6m"] == 1.0
    assert features.loc[7, "status_recently_changed"] == 1.0
