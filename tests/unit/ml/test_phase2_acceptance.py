from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.phase2 import (
    CATEGORICAL_FEATURES,
    FORBIDDEN_PREDICTORS,
    NUMERIC_FEATURES,
    build_snapshot_features,
    prepare_snapshot_source,
    run_temporal_integrity_check,
)


def test_prepare_snapshot_source_drops_invalid_keys_and_duplicates() -> None:
    source = pd.DataFrame(
        {
            "Project_ID": ["P-1", "P-1", "", "P-2"],
            "Snapshot_Date": ["2022-01-01", "2022-01-01", "2022-02-01", "not-a-date"],
            "Cumulative_Expenditure_Crore": [1.0, 2.0, 3.0, 4.0],
        }
    )
    cleaned, report = prepare_snapshot_source(source)
    assert report["duplicate_project_snapshot_rows"] == 1
    assert report["rows_dropped_invalid_keys"] == 2
    assert list(cleaned["Project_ID"]) == ["P-1"]
    assert float(cleaned.iloc[0]["Cumulative_Expenditure_Crore"]) == 2.0
    assert report["chronological_by_project"] is True


def test_groupkfold_never_shares_project_ids() -> None:
    rows = []
    for project in range(10):
        for month in range(3):
            rows.append(
                {
                    "feat": float(project + month),
                    "y": int(project >= 5),
                    "Project_ID": f"P-{project}",
                }
            )
    frame = pd.DataFrame(rows)
    groups = frame["Project_ID"].to_numpy()
    y = frame["y"].to_numpy()
    X = frame[["feat"]]
    first = []
    for train_index, validation_index in GroupKFold(n_splits=5).split(X, y, groups):
        train_ids = set(groups[train_index].tolist())
        validation_ids = set(groups[validation_index].tolist())
        assert train_ids.isdisjoint(validation_ids)
        first.append((sorted(train_ids), sorted(validation_ids)))
    assert len(first) == 5
    second = [
        (sorted(set(groups[train])), sorted(set(groups[val])))
        for train, val in GroupKFold(n_splits=5).split(X, y, groups)
    ]
    assert first == second


def test_approved_features_exclude_identity_and_outcomes() -> None:
    approved = set(NUMERIC_FEATURES + CATEGORICAL_FEATURES)
    assert not approved.intersection(FORBIDDEN_PREDICTORS)
    for name in ("Project_ID", "Project_Name", "Cost_Overrun_Percent", "Time_Overrun_Months"):
        assert name not in approved


def test_temporal_integrity_on_synthetic_series() -> None:
    months = 8
    dates = pd.date_range("2022-01-01", periods=months, freq="MS")
    frame = pd.DataFrame(
        {
            "Project_ID": ["P-1"] * months,
            "Snapshot_Date": dates,
            "Sector": ["RAILWAYS"] * months,
            "Agency": ["AGENCY-A"] * months,
            "Project_Status": ["On Schedule"] * months,
            "Date_of_Approval": [pd.Timestamp("2021-01-01")] * months,
            "Original_DoC": [pd.Timestamp("2023-01-01")] * months,
            "Revised_or_Anticipated_DoC": [pd.Timestamp("2023-03-01")] * months,
            "Original_Cost_Crore": [100.0] * months,
            "Revised_or_Anticipated_Cost_Crore": [110.0] * months,
            "Cumulative_Expenditure_Crore": [10.0 * (index + 1) for index in range(months)],
            "Milestone_Percent": [5.0 * (index + 1) for index in range(months)],
            "Physical_Progress (%)": [None] * months,
        }
    )
    result = run_temporal_integrity_check(frame, sample_projects=1)
    assert result["passed"] is True
    assert result["projects_checked"] == 1
    truncated = build_snapshot_features(frame.iloc[:-2])
    full = build_snapshot_features(frame)
    pd.testing.assert_frame_equal(
        full.iloc[:-2].reset_index(drop=True),
        truncated.reset_index(drop=True),
        check_dtype=False,
    )
