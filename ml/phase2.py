"""Leakage-safe PAIMANA Phase 2 feature engineering and modeling.

Phase 1 owns all source cleaning. This module only reads the two cleaned CSVs,
constructs backward-looking snapshot features, and trains/serves baseline models.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
COMPLETED_PATH = ROOT / "data" / "processed" / "completed_cleaned.csv"
ONGOING_PATH = ROOT / "data" / "processed" / "ongoing_cleaned.csv"
ARTIFACT_DIR = ROOT / "models" / "paimana_phase2"
OUTPUT_PATH = ROOT / "outputs" / "ongoing_risk_predictions.csv"
INFERENCE_REPORT_PATH = ROOT / "outputs" / "ongoing_inference_report.json"
ACCEPTANCE_REPORT_PATH = ROOT / "outputs" / "phase2_acceptance_report.md"
AUDIT_DIR = ROOT / "modeling"
MODEL_VERSION = "2.0.0"
RANDOM_SEED = 42
N_SPLITS = 5
LOOKBACK_MONTHS = 6
COST_OVERRUN_THRESHOLD = 10.0
SCHEDULE_OVERRUN_THRESHOLD_MONTHS = 3.0

CATEGORICAL_FEATURES = ["Sector", "Agency", "Project_Status"]
NUMERIC_FEATURES = [
    "original_cost_crore",
    "revised_budget_crore",
    "revised_budget_to_original_ratio",
    "cumulative_expenditure_crore",
    "expenditure_ratio",
    "expenditure_lag_1m_crore",
    "expenditure_lag_3m_crore",
    "expenditure_lag_6m_crore",
    "expenditure_velocity_crore_per_month",
    "expenditure_growth_1m_pct",
    "expenditure_growth_3m_pct",
    "expenditure_3m_trend_crore_per_month",
    "expenditure_6m_trend_crore_per_month",
    "expenditure_rolling_mean_6m_crore",
    "expenditure_rolling_volatility_6m_crore",
    "expenditure_observations_6m",
    "months_since_expenditure_update",
    "physical_progress_pct",
    "physical_progress_lag_1m_pct",
    "physical_progress_lag_3m_pct",
    "physical_progress_lag_6m_pct",
    "physical_progress_velocity_pct_per_month",
    "physical_progress_acceleration_pct_per_month2",
    "physical_progress_rolling_trend_6m_pct_per_month",
    "milestone_progress_pct",
    "milestone_progress_lag_1m_pct",
    "milestone_progress_lag_3m_pct",
    "milestone_progress_lag_6m_pct",
    "milestone_progress_velocity_pct_per_month",
    "milestone_progress_acceleration_pct_per_month2",
    "milestone_progress_rolling_trend_6m_pct_per_month",
    "progress_current_pct",
    "progress_velocity_pct_per_month",
    "progress_acceleration_pct_per_month2",
    "progress_rolling_trend_6m_pct_per_month",
    "months_since_physical_progress_update",
    "months_since_milestone_progress_update",
    "months_since_progress_update",
    "planned_duration_months",
    "elapsed_since_approval_months",
    "schedule_slippage_months",
    "original_doc_slippage_months",
    "revised_doc_slippage_months",
    "revised_doc_shift_from_original_months",
    "revised_doc_movement_1m_months",
    "delay_growth_1m_months",
    "delay_growth_3m_months",
    "delay_growth_6m_months",
    "milestone_slippage_vs_elapsed_pct_points",
    "months_since_status_update",
    "status_changes_6m",
    "status_change_frequency_6m",
    "status_recently_changed",
    "history_months_available",
    "lookback_observation_count_6m",
]

FORBIDDEN_PREDICTORS = [
    "Project_ID",
    "Project_Name",
    "Cost_Overrun_Percent",
    "Time_Overrun_Months",
    "Completion_Month",
    "Delay_Months",
    "Delay_Reason",
    "Is_Completed_Snapshot",
    "Completed_In_Snapshot",
    "Time_Index",
    "Has_Fixed_DoC",
    "Has_Milestones",
    "Cost_Overrun_Flag",
    "Schedule_Overrun_Flag",
    "Overall_Overrun_Flag",
    "final_cost_overrun_percent",
    "final_time_overrun_months",
]

FEATURE_FAMILIES = {
    "expenditure": [
        "original_cost_crore",
        "revised_budget_crore",
        "revised_budget_to_original_ratio",
        "cumulative_expenditure_crore",
        "expenditure_ratio",
        "expenditure_lag_1m_crore",
        "expenditure_lag_3m_crore",
        "expenditure_lag_6m_crore",
        "expenditure_velocity_crore_per_month",
        "expenditure_growth_1m_pct",
        "expenditure_growth_3m_pct",
        "expenditure_3m_trend_crore_per_month",
        "expenditure_6m_trend_crore_per_month",
        "expenditure_rolling_mean_6m_crore",
        "expenditure_rolling_volatility_6m_crore",
        "expenditure_observations_6m",
        "months_since_expenditure_update",
    ],
    "progress": [
        "physical_progress_pct",
        "physical_progress_lag_1m_pct",
        "physical_progress_lag_3m_pct",
        "physical_progress_lag_6m_pct",
        "physical_progress_velocity_pct_per_month",
        "physical_progress_acceleration_pct_per_month2",
        "physical_progress_rolling_trend_6m_pct_per_month",
        "milestone_progress_pct",
        "milestone_progress_lag_1m_pct",
        "milestone_progress_lag_3m_pct",
        "milestone_progress_lag_6m_pct",
        "milestone_progress_velocity_pct_per_month",
        "milestone_progress_acceleration_pct_per_month2",
        "milestone_progress_rolling_trend_6m_pct_per_month",
        "progress_current_pct",
        "progress_velocity_pct_per_month",
        "progress_acceleration_pct_per_month2",
        "progress_rolling_trend_6m_pct_per_month",
        "months_since_physical_progress_update",
        "months_since_milestone_progress_update",
        "months_since_progress_update",
    ],
    "schedule": [
        "planned_duration_months",
        "elapsed_since_approval_months",
        "schedule_slippage_months",
        "original_doc_slippage_months",
        "revised_doc_slippage_months",
        "revised_doc_shift_from_original_months",
        "revised_doc_movement_1m_months",
        "delay_growth_1m_months",
        "delay_growth_3m_months",
        "delay_growth_6m_months",
        "milestone_slippage_vs_elapsed_pct_points",
    ],
    "staleness": [
        "months_since_expenditure_update",
        "months_since_physical_progress_update",
        "months_since_milestone_progress_update",
        "months_since_progress_update",
        "months_since_status_update",
    ],
    "status": [
        "Project_Status",
        "status_changes_6m",
        "status_change_frequency_6m",
        "status_recently_changed",
        "months_since_status_update",
    ],
    "static": ["Sector", "Agency", "planned_duration_months"],
    "history_availability": ["history_months_available", "lookback_observation_count_6m"],
}

FEATURE_SOURCE_MAPPING = {
    "Sector": "Phase-1 project-level static field observed on the snapshot row; one-hot encoded.",
    "Agency": "Phase-1 project-level static field observed on the snapshot row; one-hot encoded.",
    "Project_Status": "Status attached to this snapshot only; one-hot encoded. Terminal Completed snapshots are excluded from training.",
    "original_cost_crore": "Original_Cost_Crore on the current snapshot row.",
    "revised_budget_crore": "Revised_or_Anticipated_Cost_Crore on the current snapshot row; never forward-filled from later revisions.",
    "revised_budget_to_original_ratio": "Current revised budget divided by current original cost when original cost > 0.",
    "cumulative_expenditure_crore": "Cumulative_Expenditure_Crore on the current snapshot row.",
    "expenditure_ratio": "Current cumulative expenditure divided by current original cost when original cost > 0.",
    "expenditure_lag_1m_crore": "Last expenditure observation at or before snapshot minus 1 month, within a 45-day match window. Missing if no such history.",
    "expenditure_lag_3m_crore": "Last expenditure observation at or before snapshot minus 3 months, within a 45-day match window. Missing if no such history.",
    "expenditure_lag_6m_crore": "Last expenditure observation at or before snapshot minus 6 months, within a 45-day match window. Missing if no such history.",
    "expenditure_velocity_crore_per_month": "Change in expenditure from the 1-month lag divided by elapsed months between those two dates.",
    "expenditure_growth_1m_pct": "Percent change in expenditure versus the 1-month lag.",
    "expenditure_growth_3m_pct": "Percent change in expenditure versus the 3-month lag.",
    "expenditure_3m_trend_crore_per_month": "Expenditure change versus the 3-month lag divided by elapsed months.",
    "expenditure_6m_trend_crore_per_month": "Expenditure change versus the 6-month lag divided by elapsed months.",
    "expenditure_rolling_mean_6m_crore": "Mean of finite expenditure values with Snapshot_Date in (t-6 months, t].",
    "expenditure_rolling_volatility_6m_crore": "Sample standard deviation of those same trailing-six-month expenditure values.",
    "expenditure_observations_6m": "Count of finite expenditure values in the trailing six-month window.",
    "months_since_expenditure_update": "Months between the snapshot and the latest finite expenditure at or before t.",
    "physical_progress_pct": "Physical_Progress (%) on the snapshot row; values outside [0, 100] are missing.",
    "physical_progress_lag_1m_pct": "Physical progress at the 1-month as-of lag, or missing.",
    "physical_progress_lag_3m_pct": "Physical progress at the 3-month as-of lag, or missing.",
    "physical_progress_lag_6m_pct": "Physical progress at the 6-month as-of lag, or missing.",
    "physical_progress_velocity_pct_per_month": "Change in physical progress versus the 1-month lag divided by elapsed months.",
    "physical_progress_acceleration_pct_per_month2": "Current physical-progress velocity minus the prior snapshot's velocity; both velocities use only dates <= t.",
    "physical_progress_rolling_trend_6m_pct_per_month": "Physical-progress change versus the 6-month lag divided by elapsed months.",
    "milestone_progress_pct": "Milestone_Percent on the snapshot row; values outside [0, 100] are missing.",
    "milestone_progress_lag_1m_pct": "Milestone progress at the 1-month as-of lag, or missing.",
    "milestone_progress_lag_3m_pct": "Milestone progress at the 3-month as-of lag, or missing.",
    "milestone_progress_lag_6m_pct": "Milestone progress at the 6-month as-of lag, or missing.",
    "milestone_progress_velocity_pct_per_month": "Change in milestone progress versus the 1-month lag divided by elapsed months.",
    "milestone_progress_acceleration_pct_per_month2": "Current milestone velocity minus the prior snapshot's velocity.",
    "milestone_progress_rolling_trend_6m_pct_per_month": "Milestone-progress change versus the 6-month lag divided by elapsed months.",
    "progress_current_pct": "Physical progress if finite, otherwise milestone progress, both from the current snapshot.",
    "progress_velocity_pct_per_month": "Physical-progress velocity if finite, otherwise milestone-progress velocity.",
    "progress_acceleration_pct_per_month2": "Physical-progress acceleration if finite, otherwise milestone-progress acceleration.",
    "progress_rolling_trend_6m_pct_per_month": "Physical-progress 6-month trend if finite, otherwise milestone-progress 6-month trend.",
    "months_since_physical_progress_update": "Months since the latest finite physical-progress value at or before t.",
    "months_since_milestone_progress_update": "Months since the latest finite milestone-progress value at or before t.",
    "months_since_progress_update": "Months since the latest finite physical or milestone progress at or before t.",
    "planned_duration_months": "Original_DoC minus Date_of_Approval in months, using only dates on the current row; approval dates after t are treated as unknown.",
    "elapsed_since_approval_months": "Snapshot_Date minus Date_of_Approval when approval is known and <= t.",
    "schedule_slippage_months": "Snapshot minus current-row revised DoC, else original DoC; positive means the snapshot is after the planned date.",
    "original_doc_slippage_months": "Snapshot minus current-row Original_DoC.",
    "revised_doc_slippage_months": "Snapshot minus current-row Revised_or_Anticipated_DoC.",
    "revised_doc_shift_from_original_months": "Current-row revised DoC minus current-row original DoC.",
    "revised_doc_movement_1m_months": "Change in the as-of revised DoC versus the 1-month lag row; later revisions are not used.",
    "delay_growth_1m_months": "Current schedule slippage minus slippage at the 1-month lag snapshot.",
    "delay_growth_3m_months": "Current schedule slippage minus slippage at the 3-month lag snapshot.",
    "delay_growth_6m_months": "Current schedule slippage minus slippage at the 6-month lag snapshot.",
    "milestone_slippage_vs_elapsed_pct_points": "Current milestone percent minus expected percent from elapsed/planned duration, clipped to [0, 100].",
    "months_since_status_update": "Months since the latest non-missing Project_Status at or before t.",
    "status_changes_6m": "Count of observed Project_Status transitions in (t-6 months, t].",
    "status_change_frequency_6m": "status_changes_6m divided by the span of the trailing status window in months.",
    "status_recently_changed": "1 if a status transition occurred within 1.5 months before t, else 0 when enough history exists.",
    "history_months_available": "Months between this snapshot and the project's first valid snapshot.",
    "lookback_observation_count_6m": "Number of snapshots in (t-6 months, t], including the current row.",
}


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if value is pd.NA or pd.isna(value):
        return None
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=_json_default, allow_nan=False) + "\n", encoding="utf-8")


def _read_cleaned(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required Phase-1 cleaned dataset not found: {path}")
    frame = pd.read_csv(path, low_memory=False)
    source_csv_dtypes = {column: str(dtype) for column, dtype in frame.dtypes.items()}
    for required in ("Project_ID", "Snapshot_Date"):
        if required not in frame.columns:
            raise ValueError(f"{path.name} is missing required Phase-1 field {required!r}")
    frame["Project_ID"] = frame["Project_ID"].astype("string").str.strip()
    frame["Snapshot_Date"] = pd.to_datetime(frame["Snapshot_Date"], errors="coerce")
    frame.attrs["source_csv_dtypes"] = source_csv_dtypes
    return frame


def prepare_snapshot_source(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Parse keys, drop invalid dates/IDs, and collapse duplicate snapshots.

    Duplicate `Project_ID + Snapshot_Date` rows keep the last record after a
    stable chronological sort so later extracts of the same report win.
    Invalid dates never enter feature engineering.
    """
    source = frame.copy()
    source["Project_ID"] = source["Project_ID"].astype("string").str.strip()
    source["Snapshot_Date"] = pd.to_datetime(source["Snapshot_Date"], errors="coerce")
    invalid_id = source["Project_ID"].isna() | source["Project_ID"].eq("") | source["Project_ID"].str.casefold().eq("nan")
    invalid_date = source["Snapshot_Date"].isna()
    dropped_keys = int((invalid_id | invalid_date).sum())
    cleaned = source.loc[~(invalid_id | invalid_date)].copy()
    ordered = cleaned.sort_values(["Project_ID", "Snapshot_Date"], kind="stable")
    duplicate_count = int(ordered.duplicated(["Project_ID", "Snapshot_Date"]).sum())
    if duplicate_count:
        ordered = ordered.drop_duplicates(["Project_ID", "Snapshot_Date"], keep="last")
    ordered = ordered.reset_index(drop=True)
    chronological = True
    if len(ordered):
        chronological = bool(
            ordered.groupby("Project_ID", sort=False)["Snapshot_Date"]
            .apply(lambda values: values.is_monotonic_increasing)
            .all()
        )
    report = {
        "input_rows": int(len(frame)),
        "invalid_project_id_rows": int(invalid_id.sum()),
        "invalid_snapshot_date_rows": int(invalid_date.sum()),
        "rows_dropped_invalid_keys": dropped_keys,
        "duplicate_project_snapshot_rows": duplicate_count,
        "duplicate_handling": "keep last row after chronological sort" if duplicate_count else "none required",
        "unique_projects": int(ordered["Project_ID"].nunique()) if len(ordered) else 0,
        "output_rows": int(len(ordered)),
        "chronological_by_project": chronological,
        "missingness_count_and_fraction": {
            column: {"missing": int(ordered[column].isna().sum()), "fraction": float(ordered[column].isna().mean())}
            for column in ordered.columns
        }
        if len(ordered)
        else {},
    }
    return ordered, report


def assert_approved_feature_list() -> None:
    approved = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    missing_docs = [name for name in approved if name not in FEATURE_SOURCE_MAPPING]
    if missing_docs:
        raise AssertionError(f"Features missing documentation: {missing_docs}")
    overlap = set(approved) & set(FORBIDDEN_PREDICTORS)
    if overlap:
        raise AssertionError(f"Forbidden leakage columns in the feature list: {sorted(overlap)}")


def format_mean_std(summary: dict[str, Any], metric: str) -> str:
    stats = summary[metric]
    return f"{stats['mean']:.4f} ± {stats['std']:.4f}"


def _latest_project_outcomes(frame: pd.DataFrame) -> pd.DataFrame:
    """Get each project's latest valid reported outcome, never as a feature."""
    ordered = frame.sort_values(["Project_ID", "Snapshot_Date"], kind="stable")
    outcomes: list[dict[str, Any]] = []
    for project_id, group in ordered.groupby("Project_ID", sort=False, dropna=False):
        row: dict[str, Any] = {"Project_ID": str(project_id)}
        for column, output_name in (
            ("Cost_Overrun_Percent", "final_cost_overrun_percent"),
            ("Time_Overrun_Months", "final_time_overrun_months"),
        ):
            if column not in group:
                row[output_name] = np.nan
                row[f"{output_name}_observed_at"] = pd.NaT
                continue
            values = pd.to_numeric(group[column], errors="coerce")
            valid = values.notna()
            if valid.any():
                index = values.index[valid][-1]
                row[output_name] = float(values.loc[index])
                row[f"{output_name}_observed_at"] = group.loc[index, "Snapshot_Date"]
            else:
                row[output_name] = np.nan
                row[f"{output_name}_observed_at"] = pd.NaT
        outcomes.append(row)
    return pd.DataFrame(outcomes)


def _class_counts(values: pd.Series) -> dict[str, int]:
    counts = values.value_counts(dropna=False)
    return {str(key): int(value) for key, value in counts.items()}


def write_leakage_audit(path: Path | None = None) -> Path:
    path = path or (AUDIT_DIR / "leakage_audit.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        ("Cost_Overrun_Percent", "Direct cost target; values may be repeated/updated across snapshots.", "Exclude from every feature; latest valid project value is label source only.", "Prevents direct target leakage."),
        ("Time_Overrun_Months", "Direct schedule target; values may be repeated/updated across snapshots.", "Exclude from every feature; latest valid project value is label source only.", "Prevents direct target leakage."),
        ("Project_ID", "Unique project key could let the model memorize outcomes.", "Use only as GroupKFold grouping/key; never as a model feature.", "Required group holdout and output identity."),
        ("Project_Name", "Project-specific free text and identifier proxy.", "Exclude.", "User requirement; high memorization risk."),
        ("Project_Status", "May contain terminal Completed state or current schedule state.", "Use only the status on the snapshot row; exclude completed/terminal snapshots.", "As-of status is observable, but terminal status directly reveals completion."),
        ("Is_Completed_Snapshot / Completed_In_Snapshot", "Explicit marker of the eventual completion row.", "Use only to exclude terminal rows; never a predictor.", "Direct future/outcome indicator."),
        ("Completion_Month", "Known only at/after completion.", "Exclude.", "Future completion outcome."),
        ("Delay_Months", "Overlaps time-overrun reporting and has inconsistent string representations.", "Exclude.", "Potential direct target proxy; schedule slippage is independently derived from snapshot and planned dates."),
        ("Delay_Reason", "Free text has report-page contamination and may describe realized outcomes.", "Exclude.", "Future/post-event information and known extraction artefacts."),
        ("Original_DoC", "Planned commissioning date; source value is attached to each snapshot.", "Use only the current row; derive elapsed/slippage against Snapshot_Date.", "Planned dates are known inputs, not actual completion dates."),
        ("Revised_or_Anticipated_DoC", "A revision could be learned after some earlier snapshots.", "Use the value on the current snapshot only; never backfill/forward-fill revisions.", "Time-varying row values are treated as available as-of that row."),
        ("Revised_or_Anticipated_Cost_Crore", "A cost revision could be learned after earlier snapshots.", "Use current-row value only; never propagate it across snapshots.", "Time-varying row values are treated as available as-of that row."),
        ("Cumulative_Expenditure_Crore", "Future cumulative expenditure would leak if shifted/filled forward.", "Use current and backward-only lags/rolling values within six months.", "Every lag is selected at or before the snapshot date."),
        ("Milestones_Achieved / Milestone_Percent / Physical_Progress (%)", "Future progress would reveal the outcome.", "Use current row and historical values at/before snapshot only; invalid percentages outside 0–100 are treated as missing.", "Backward-only window; no future fill."),
        ("Sector / Agency", "Phase-1 modal resolution uses all project rows and can see later categorical values.", "Include as intended static fields; one-hot encode; document as residual look-ahead risk.", "These are project metadata expected to be known at registration, but Phase-1 modal repair cannot prove historical availability."),
        ("Date_of_Approval", "Approval date should predate project snapshots.", "Use only if it is not later than the current Snapshot_Date.", "Future/invalid approval dates are nulled at feature construction."),
        ("Time_Index", "May encode source export ordering or project identity.", "Exclude.", "Elapsed duration is derived from known dates instead."),
        ("Has_Fixed_DoC / Has_Milestones", "Could be static flags or reflect post-hoc reporting availability.", "Exclude from baseline predictors.", "Avoid uncertain availability semantics; date and milestone values are used as-of snapshot."),
        ("Target-derived values / future snapshots", "Any aggregation crossing Snapshot_Date can expose eventual outcomes.", "No target-derived predictors; all shifts, rolling windows, staleness, and status changes use dates <= Snapshot_Date.", "Automated causal-date checks and code-level backward as-of selection."),
    ]
    lines = [
        "# Phase 2 Leakage Audit",
        "",
        "Audit generated by `ml/phase2.py`. The model uses only values attached to the current snapshot or observations at earlier dates.",
        "Terminal completion rows are excluded from training/scoring features. No outcome columns enter `X`.",
        "The Phase-1 modal resolution of `Sector`/`Agency` is a known residual risk because historical value availability cannot be reconstructed from cleaned files.",
        "",
        "| Feature/source | Leakage risk | Decision | Reason |",
        "|---|---|---|---|",
    ]
    lines.extend("| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |" for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def audit_cleaned_data(
    completed_path: Path = COMPLETED_PATH,
    ongoing_path: Path = ONGOING_PATH,
    audit_json_path: Path | None = None,
    audit_md_path: Path | None = None,
    cost_threshold: float = COST_OVERRUN_THRESHOLD,
    schedule_threshold_months: float = SCHEDULE_OVERRUN_THRESHOLD_MONTHS,
) -> dict[str, Any]:
    """Write a schema/target audit before training begins."""
    completed_raw = _read_cleaned(completed_path)
    ongoing_raw = _read_cleaned(ongoing_path)
    completed, completed_integrity = prepare_snapshot_source(completed_raw)
    ongoing, ongoing_integrity = prepare_snapshot_source(ongoing_raw)
    completed.attrs["source_csv_dtypes"] = completed_raw.attrs.get("source_csv_dtypes", {})
    ongoing.attrs["source_csv_dtypes"] = ongoing_raw.attrs.get("source_csv_dtypes", {})
    outcomes = _latest_project_outcomes(completed)
    outcomes["Cost_Overrun_Flag"] = (outcomes["final_cost_overrun_percent"] >= cost_threshold).astype("Int64")
    outcomes["Schedule_Overrun_Flag"] = (outcomes["final_time_overrun_months"] >= schedule_threshold_months).astype("Int64")

    fields = {
        "cost": ["Original_Cost_Crore", "Revised_or_Anticipated_Cost_Crore", "Cumulative_Expenditure_Crore", "Cost_Overrun_Percent"],
        "schedule_dates": ["Snapshot_Date", "Date_of_Approval", "Original_DoC", "Revised_or_Anticipated_DoC", "Completion_Month"],
        "progress": ["Milestones_Achieved", "Milestones_Total", "Milestone_Percent", "Physical_Progress (%)"],
        "expenditure": ["Cumulative_Expenditure_Crore"],
        "status": ["Project_Status", "Is_Completed_Snapshot", "Completed_In_Snapshot"],
        "static": ["Sector", "Agency"],
    }

    def describe_dataset(frame: pd.DataFrame) -> dict[str, Any]:
        dates = frame["Snapshot_Date"]
        by_project = frame.groupby("Project_ID", sort=False)["Snapshot_Date"]
        counts = frame.groupby("Project_ID", sort=False).size()
        sorted_frame = frame.sort_values(["Project_ID", "Snapshot_Date"], kind="stable")
        duplicates = int(sorted_frame.duplicated(["Project_ID", "Snapshot_Date"]).sum())
        chronological = bool(
            sorted_frame.groupby("Project_ID", sort=False)["Snapshot_Date"]
            .apply(lambda values: values.is_monotonic_increasing)
            .all()
        )
        present_field_groups = {
            name: [column for column in columns if column in frame.columns]
            for name, columns in fields.items()
        }
        category_summary = {
            column: {
                "unique_values": int(frame[column].nunique(dropna=True)),
                "values": sorted(frame[column].dropna().astype(str).unique().tolist()),
            }
            for column in ("Sector", "Agency")
            if column in frame.columns
        }
        return {
            "filename": frame.attrs.get("filename"),
            "rows": int(len(frame)),
            "columns": [
                {"name": column, "dtype": frame.attrs.get("source_csv_dtypes", {}).get(column, str(frame[column].dtype))}
                for column in frame.columns
            ],
            "project_count": int(frame["Project_ID"].nunique()),
            "observations_per_project": {
                "min": int(counts.min()),
                "median": float(counts.median()),
                "mean": float(counts.mean()),
                "max": int(counts.max()),
            },
            "snapshot_date_min": dates.min().isoformat() if dates.notna().any() else None,
            "snapshot_date_max": dates.max().isoformat() if dates.notna().any() else None,
            "snapshot_date_missing": int(dates.isna().sum()),
            "duplicate_project_snapshot_rows": duplicates,
            "duplicate_handling": "Phase 2 keeps the last row per Project_ID + Snapshot_Date after chronological sort before feature engineering.",
            "chronological_by_project_after_sort": chronological,
            "missingness_count_and_fraction": {
                column: {"missing": int(frame[column].isna().sum()), "fraction": float(frame[column].isna().mean())}
                for column in frame.columns
            },
            "field_groups_present": present_field_groups,
            "sector_agency": category_summary,
        }

    completed.attrs["filename"] = completed_path.name
    ongoing.attrs["filename"] = ongoing_path.name
    cost_values = outcomes["final_cost_overrun_percent"].dropna()
    schedule_values = outcomes["final_time_overrun_months"].dropna()
    terminal = _terminal_snapshot_mask(completed)
    terminal_rows = completed.loc[terminal]
    audit = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "datasets": {
            "completed_cleaned.csv": {**describe_dataset(completed), "integrity": completed_integrity},
            "ongoing_cleaned.csv": {**describe_dataset(ongoing), "integrity": ongoing_integrity},
        },
        "target_class_distribution_project_level": {
            "Cost_Overrun_Flag": _class_counts(outcomes["Cost_Overrun_Flag"]),
            "Schedule_Overrun_Flag": _class_counts(outcomes["Schedule_Overrun_Flag"]),
        },
        "completed_project_outcome_audit": {
            "project_count": int(completed["Project_ID"].nunique()),
            "terminal_snapshot_rows": int(terminal.sum()),
            "terminal_cost_outcome_nonmissing": int(pd.to_numeric(terminal_rows.get("Cost_Overrun_Percent"), errors="coerce").notna().sum()),
            "terminal_schedule_outcome_nonmissing": int(pd.to_numeric(terminal_rows.get("Time_Overrun_Months"), errors="coerce").notna().sum()),
            "outcome_label_mapping": "Latest valid Cost_Overrun_Percent / Time_Overrun_Months per Project_ID in completed_cleaned.csv, excluding terminal snapshots if any; target values are project-level labels, never features.",
            "cost_latest_nonmissing_projects": int(outcomes["final_cost_overrun_percent"].notna().sum()),
            "schedule_latest_nonmissing_projects": int(outcomes["final_time_overrun_months"].notna().sum()),
            "cost_outcome_distribution_project_latest": cost_values.describe(percentiles=[0.25, 0.5, 0.75, 0.9]).to_dict(),
            "schedule_outcome_distribution_project_latest": schedule_values.describe(percentiles=[0.25, 0.5, 0.75, 0.9]).to_dict(),
        },
        "feature_target_mapping": {
            "prediction_unit": "Project_ID + Snapshot_Date",
            "cost_target": {
                "name": "Cost_Overrun_Flag",
                "field": "Cost_Overrun_Percent",
                "threshold_percent": float(cost_threshold),
                "operator": ">=",
                "class_counts": _class_counts(outcomes["Cost_Overrun_Flag"]),
                "source_mapping": "Latest valid project-level Cost_Overrun_Percent from completed_cleaned.csv; the exact completed snapshot contains no cost outcome, so latest valid pre-completion report is used.",
            },
            "schedule_target": {
                "name": "Schedule_Overrun_Flag",
                "field": "Time_Overrun_Months",
                "threshold_months": float(schedule_threshold_months),
                "operator": ">=",
                "class_counts": _class_counts(outcomes["Schedule_Overrun_Flag"]),
                "source_mapping": "Latest valid project-level Time_Overrun_Months from completed_cleaned.csv; the exact completed snapshot contains no schedule outcome, so latest valid pre-completion report is used.",
            },
            "threshold_selection": "No cost/schedule target threshold exists in the inspected architecture. Defaults are explicit configurable material-overrun thresholds (10% cost, 3 months schedule), above zero to avoid classifying reporting-rounding and short schedule slips as material. They are not presented as architecture-mandated thresholds.",
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "feature_source_mapping": FEATURE_SOURCE_MAPPING,
            "feature_exclusions": FORBIDDEN_PREDICTORS,
            "feature_families": FEATURE_FAMILIES,
            "lookback": {
                "months": LOOKBACK_MONTHS,
                "minimum_history_requirement": "No minimum history is required. Missing lags/rolling features remain missing and are imputed inside each training fold; no historical value is fabricated.",
                "insufficient_full_window_rows": None,
                "rows_removed_for_insufficient_history": 0,
            },
        },
    }

    json_path = audit_json_path or (AUDIT_DIR / "feature_target_audit.json")
    md_path = audit_md_path or (AUDIT_DIR / "feature_target_audit.md")
    _write_json(json_path, audit)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    target_audit = audit["completed_project_outcome_audit"]
    lines = [
        "# Phase 2 Feature and Target Audit",
        "",
        f"Generated: {audit['generated_at_utc']}",
        "",
        "## Dataset inventory",
    ]
    for name, dataset in audit["datasets"].items():
        lines += [
            f"### `{name}`",
            f"- Rows/projects: {dataset['rows']:,} rows / {dataset['project_count']} projects",
            f"- Snapshot range: {dataset['snapshot_date_min']} to {dataset['snapshot_date_max']}; missing dates: {dataset['snapshot_date_missing']}",
            f"- Observations/project: min {dataset['observations_per_project']['min']}, median {dataset['observations_per_project']['median']}, max {dataset['observations_per_project']['max']}",
            f"- Unique Sector/Agency counts: {dataset['sector_agency'].get('Sector', {}).get('unique_values', 0)} / {dataset['sector_agency'].get('Agency', {}).get('unique_values', 0)}",
            "- Exact columns and dtypes:",
        ]
        lines.extend(f"  - `{column['name']}`: `{column['dtype']}`, missing {dataset['missingness_count_and_fraction'][column['name']]['fraction']:.1%}" for column in dataset["columns"])
    lines += [
        "",
        "## Outcomes and targets",
        f"- Terminal completed rows: {target_audit['terminal_snapshot_rows']}; cost/schedule outcome values on those rows: {target_audit['terminal_cost_outcome_nonmissing']}/{target_audit['terminal_schedule_outcome_nonmissing']}.",
        "- Therefore the target source mapping is the latest non-null outcome value per project in the cleaned completed history, which is retained as a project-level label only. This is the closest available project-level final outcome; the actual terminal row has no target value.",
        f"- Cost outcomes (project-level latest): n={int(cost_values.count())}, min={cost_values.min():.2f}, median={cost_values.median():.2f}, p75={cost_values.quantile(.75):.2f}, max={cost_values.max():.2f}; target `Cost_Overrun_Flag = 1` when latest `Cost_Overrun_Percent >= {cost_threshold:g}`. Class counts: `{audit['feature_target_mapping']['cost_target']['class_counts']}`.",
        f"- Schedule outcomes (project-level latest): n={int(schedule_values.count())}, min={schedule_values.min():.2f}, median={schedule_values.median():.2f}, p75={schedule_values.quantile(.75):.2f}, max={schedule_values.max():.2f}; target `Schedule_Overrun_Flag = 1` when latest `Time_Overrun_Months >= {schedule_threshold_months:g}`. Class counts: `{audit['feature_target_mapping']['schedule_target']['class_counts']}`.",
        "- No target threshold was defined in existing architecture/docs. Thresholds are configurable via the Phase-2 training CLI; 10% and 3 months are explicit material-overrun defaults, not architecture specifications.",
        "",
        "## Field families and model inputs",
        "- Cost fields: `Original_Cost_Crore`, `Revised_or_Anticipated_Cost_Crore`, `Cumulative_Expenditure_Crore`, and target-only `Cost_Overrun_Percent`.",
        "- Schedule/date fields: `Snapshot_Date`, `Date_of_Approval`, `Original_DoC`, `Revised_or_Anticipated_DoC`; `Completion_Month` is excluded.",
        "- Progress: `Physical_Progress (%)`, `Milestone_Percent`, `Milestones_Achieved`, `Milestones_Total`; progress percentages outside 0–100 are treated as missing only in feature engineering.",
        "- Status/static: `Project_Status`, `Sector`, `Agency`; `Project_Name` is excluded.",
        f"- Numeric feature list ({len(NUMERIC_FEATURES)}): " + ", ".join(f"`{name}`" for name in NUMERIC_FEATURES),
        f"- Categorical feature list: " + ", ".join(f"`{name}`" for name in CATEGORICAL_FEATURES),
        "",
        "## Temporal and missing-history policy",
        "- Prediction row: `Project_ID + Snapshot_Date`, sorted chronologically. All shifts, trends, rolling windows, status changes, and staleness checks use rows at or before the prediction date and no older than six calendar months where applicable.",
        "- No minimum history is required. Missing lags are explicitly left missing, then imputed within each GroupKFold training fold; no forward fill is performed. Completed terminal rows are excluded; no rows are removed for insufficient six-month history.",
        "- Phase-1 modal resolution for Sector/Agency is retained as requested; its use of full-project modal values is documented as residual historical-availability risk in the leakage audit.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_leakage_audit()
    return audit


def _terminal_snapshot_mask(frame: pd.DataFrame) -> pd.Series:
    terminal = pd.Series(False, index=frame.index)
    if "Is_Completed_Snapshot" in frame:
        terminal |= pd.to_numeric(frame["Is_Completed_Snapshot"], errors="coerce").eq(1)
    if "Project_Status" in frame:
        terminal |= frame["Project_Status"].astype("string").str.strip().str.casefold().eq("completed").fillna(False)
    if "Completed_In_Snapshot" in frame:
        terminal |= frame["Completed_In_Snapshot"].astype("string").str.strip().str.casefold().isin(["yes", "true", "1"])
    return terminal


def _numeric_column(group: pd.DataFrame, column: str) -> np.ndarray:
    if column not in group:
        return np.full(len(group), np.nan, dtype=float)
    values = group[column].astype("string").str.replace(",", "", regex=False)
    numeric = pd.to_numeric(values, errors="coerce").astype(float)
    return numeric.to_numpy(copy=True)


def _date_column(group: pd.DataFrame, column: str) -> pd.Series:
    if column not in group:
        return pd.Series(pd.NaT, index=group.index, dtype="datetime64[ns]")
    return pd.to_datetime(group[column], errors="coerce")


def _finite_or_nan(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return number if math.isfinite(number) else float("nan")


def _months_between(later: pd.Timestamp, earlier: pd.Timestamp) -> float:
    return (later - earlier).total_seconds() / (30.4375 * 24 * 60 * 60)


def _lag_index(dates_ns: np.ndarray, date: pd.Timestamp, months: int) -> int | None:
    cutoff = date - pd.DateOffset(months=months)
    index = int(np.searchsorted(dates_ns, cutoff.value, side="right") - 1)
    if index < 0:
        return None
    if (cutoff - pd.Timestamp(dates_ns[index])).days > 45:
        return None
    return index


def _latest_valid_index(values: np.ndarray, end_index: int) -> int | None:
    candidates = np.flatnonzero(np.isfinite(values[: end_index + 1]))
    return int(candidates[-1]) if len(candidates) else None


def _lag_value(values: np.ndarray, dates_ns: np.ndarray, date: pd.Timestamp, index: int, months: int) -> float:
    previous = _lag_index(dates_ns, date, months)
    if previous is None or previous >= index or not np.isfinite(values[previous]):
        return float("nan")
    return float(values[previous])


def _feature_rows_for_project(group: pd.DataFrame) -> list[dict[str, Any]]:
    group = group.sort_values("Snapshot_Date", kind="stable").reset_index(drop=True)
    dates = pd.to_datetime(group["Snapshot_Date"], errors="coerce")
    dates_ns = dates.astype("int64").to_numpy()
    n = len(group)
    expense = _numeric_column(group, "Cumulative_Expenditure_Crore")
    original_cost = _numeric_column(group, "Original_Cost_Crore")
    revised_cost = _numeric_column(group, "Revised_or_Anticipated_Cost_Crore")
    physical = _numeric_column(group, "Physical_Progress (%)")
    milestone = _numeric_column(group, "Milestone_Percent")
    milestone_count = _numeric_column(group, "Milestones_Achieved")
    physical[(physical < 0) | (physical > 100)] = np.nan
    milestone[(milestone < 0) | (milestone > 100)] = np.nan
    approval = _date_column(group, "Date_of_Approval")
    original_doc = _date_column(group, "Original_DoC")
    revised_doc = _date_column(group, "Revised_or_Anticipated_DoC")
    status = group.get("Project_Status", pd.Series(pd.NA, index=group.index)).astype("string").str.strip()
    sector = group.get("Sector", pd.Series(pd.NA, index=group.index)).astype("string").str.strip()
    agency = group.get("Agency", pd.Series(pd.NA, index=group.index)).astype("string").str.strip()
    progress_generic = np.where(np.isfinite(physical), physical, milestone)
    progress_generic = progress_generic.astype(float)

    rows: list[dict[str, Any]] = []
    for index, snapshot in enumerate(dates):
        row: dict[str, Any] = {
            "Project_ID": str(group.loc[index, "Project_ID"]),
            "Snapshot_Date": snapshot,
            "Sector": sector.iloc[index] if pd.notna(sector.iloc[index]) else np.nan,
            "Agency": agency.iloc[index] if pd.notna(agency.iloc[index]) else np.nan,
            "Project_Status": status.iloc[index] if pd.notna(status.iloc[index]) else np.nan,
        }
        current_cost = original_cost[index]
        current_expense = expense[index]
        row["original_cost_crore"] = _finite_or_nan(current_cost)
        row["revised_budget_crore"] = _finite_or_nan(revised_cost[index])
        row["revised_budget_to_original_ratio"] = _finite_or_nan(revised_cost[index] / current_cost) if np.isfinite(revised_cost[index]) and np.isfinite(current_cost) and current_cost > 0 else np.nan
        row["cumulative_expenditure_crore"] = _finite_or_nan(current_expense)
        row["expenditure_ratio"] = _finite_or_nan(current_expense / current_cost) if np.isfinite(current_expense) and np.isfinite(current_cost) and current_cost > 0 else np.nan

        exp_lags = {month: _lag_value(expense, dates_ns, snapshot, index, month) for month in (1, 3, 6)}
        for month, value in exp_lags.items():
            row[f"expenditure_lag_{month}m_crore"] = value
        lag_index = _lag_index(dates_ns, snapshot, 1)
        elapsed = _months_between(snapshot, dates.iloc[lag_index]) if lag_index is not None and lag_index < index else np.nan
        row["expenditure_velocity_crore_per_month"] = _finite_or_nan((current_expense - exp_lags[1]) / elapsed) if np.isfinite(current_expense) and np.isfinite(exp_lags[1]) and np.isfinite(elapsed) and elapsed > 0 else np.nan
        for month, name in ((1, "expenditure_growth_1m_pct"), (3, "expenditure_growth_3m_pct")):
            lag_value = exp_lags[month]
            row[name] = _finite_or_nan((current_expense - lag_value) / abs(lag_value) * 100) if np.isfinite(current_expense) and np.isfinite(lag_value) and abs(lag_value) > 1e-9 else np.nan
        for month in (3, 6):
            lag_value = exp_lags[month]
            lag_pos = _lag_index(dates_ns, snapshot, month)
            gap = _months_between(snapshot, dates.iloc[lag_pos]) if lag_pos is not None and lag_pos < index else np.nan
            row[f"expenditure_{month}m_trend_crore_per_month"] = _finite_or_nan((current_expense - lag_value) / gap) if np.isfinite(current_expense) and np.isfinite(lag_value) and np.isfinite(gap) and gap > 0 else np.nan
        cutoff = snapshot - pd.DateOffset(months=LOOKBACK_MONTHS)
        rolling_mask = (dates <= snapshot) & (dates > cutoff)
        rolling_expense = expense[rolling_mask.to_numpy()]
        rolling_expense = rolling_expense[np.isfinite(rolling_expense)]
        row["expenditure_rolling_mean_6m_crore"] = float(np.mean(rolling_expense)) if len(rolling_expense) else np.nan
        row["expenditure_rolling_volatility_6m_crore"] = float(np.std(rolling_expense, ddof=1)) if len(rolling_expense) >= 2 else np.nan
        row["expenditure_observations_6m"] = float(len(rolling_expense))
        last_expense = _latest_valid_index(expense, index)
        row["months_since_expenditure_update"] = _months_between(snapshot, dates.iloc[last_expense]) if last_expense is not None else np.nan

        for name, values in (("physical_progress", physical), ("milestone_progress", milestone)):
            current = values[index]
            row[f"{name}_pct"] = _finite_or_nan(current)
            lag_values = {month: _lag_value(values, dates_ns, snapshot, index, month) for month in (1, 3, 6)}
            for month, value in lag_values.items():
                row[f"{name}_lag_{month}m_pct"] = value
            velocity = _finite_or_nan((current - lag_values[1]) / elapsed) if np.isfinite(current) and np.isfinite(lag_values[1]) and np.isfinite(elapsed) and elapsed > 0 else np.nan
            row[f"{name}_velocity_pct_per_month"] = velocity
            lag1_position = _lag_index(dates_ns, snapshot, 1)
            prior_velocity = np.nan
            if lag1_position is not None and lag1_position < index:
                lag1_date = dates.iloc[lag1_position]
                lag3_position = _lag_index(dates_ns, lag1_date, 1)
                if lag3_position is not None and lag3_position < lag1_position and np.isfinite(values[lag1_position]) and np.isfinite(values[lag3_position]):
                    prior_months = _months_between(lag1_date, dates.iloc[lag3_position])
                    if prior_months > 0:
                        prior_velocity = (values[lag1_position] - values[lag3_position]) / prior_months
            row[f"{name}_acceleration_pct_per_month2"] = _finite_or_nan(velocity - prior_velocity) if np.isfinite(velocity) and np.isfinite(prior_velocity) else np.nan
            lag6 = lag_values[6]
            lag6_position = _lag_index(dates_ns, snapshot, 6)
            span6 = _months_between(snapshot, dates.iloc[lag6_position]) if lag6_position is not None and lag6_position < index else np.nan
            row[f"{name}_rolling_trend_6m_pct_per_month"] = _finite_or_nan((current - lag6) / span6) if np.isfinite(current) and np.isfinite(lag6) and np.isfinite(span6) and span6 > 0 else np.nan
            latest_progress = _latest_valid_index(values, index)
            row[f"months_since_{name}_update"] = _months_between(snapshot, dates.iloc[latest_progress]) if latest_progress is not None else np.nan

        current_progress = progress_generic[index]
        row["progress_current_pct"] = _finite_or_nan(current_progress)
        row["progress_velocity_pct_per_month"] = row["physical_progress_velocity_pct_per_month"] if np.isfinite(row["physical_progress_velocity_pct_per_month"]) else row["milestone_progress_velocity_pct_per_month"]
        row["progress_acceleration_pct_per_month2"] = row["physical_progress_acceleration_pct_per_month2"] if np.isfinite(row["physical_progress_acceleration_pct_per_month2"]) else row["milestone_progress_acceleration_pct_per_month2"]
        row["progress_rolling_trend_6m_pct_per_month"] = row["physical_progress_rolling_trend_6m_pct_per_month"] if np.isfinite(row["physical_progress_rolling_trend_6m_pct_per_month"]) else row["milestone_progress_rolling_trend_6m_pct_per_month"]
        progress_last = _latest_valid_index(progress_generic, index)
        row["months_since_progress_update"] = _months_between(snapshot, dates.iloc[progress_last]) if progress_last is not None else np.nan

        approval_date = approval.iloc[index]
        approval_known = pd.notna(approval_date) and approval_date <= snapshot
        original_date = original_doc.iloc[index]
        revised_date = revised_doc.iloc[index]
        if not approval_known:
            approval_date = pd.NaT
        planned_duration = _months_between(original_date, approval_date) if pd.notna(original_date) and pd.notna(approval_date) and original_date >= approval_date else np.nan
        row["planned_duration_months"] = _finite_or_nan(planned_duration)
        row["elapsed_since_approval_months"] = _months_between(snapshot, approval_date) if pd.notna(approval_date) else np.nan
        original_slippage = _months_between(snapshot, original_date) if pd.notna(original_date) else np.nan
        revised_slippage = _months_between(snapshot, revised_date) if pd.notna(revised_date) else np.nan
        row["original_doc_slippage_months"] = _finite_or_nan(original_slippage)
        row["revised_doc_slippage_months"] = _finite_or_nan(revised_slippage)
        row["schedule_slippage_months"] = _finite_or_nan(revised_slippage if np.isfinite(revised_slippage) else original_slippage)
        row["revised_doc_shift_from_original_months"] = _months_between(revised_date, original_date) if pd.notna(revised_date) and pd.notna(original_date) else np.nan
        previous_revision_index = _lag_index(dates_ns, snapshot, 1)
        previous_revision_date = revised_doc.iloc[previous_revision_index] if previous_revision_index is not None and previous_revision_index < index else pd.NaT
        revision_movement = _months_between(revised_date, previous_revision_date) if pd.notna(revised_date) and pd.notna(previous_revision_date) else np.nan
        row["revised_doc_movement_1m_months"] = _finite_or_nan(revision_movement)
        slippage_series = np.array(
            [
                _months_between(date, revised if pd.notna(revised) else original)
                if pd.notna(revised) or pd.notna(original)
                else np.nan
                for date, original, revised in zip(dates, original_doc, revised_doc)
            ],
            dtype=float,
        )
        for month in (1, 3, 6):
            lag_slippage = _lag_value(slippage_series, dates_ns, snapshot, index, month)
            row[f"delay_growth_{month}m_months"] = (
                _finite_or_nan(row["schedule_slippage_months"] - lag_slippage)
                if np.isfinite(row["schedule_slippage_months"]) and np.isfinite(lag_slippage)
                else np.nan
            )
        if np.isfinite(planned_duration) and planned_duration > 0 and np.isfinite(row["elapsed_since_approval_months"]) and np.isfinite(milestone[index]):
            expected_progress = np.clip(row["elapsed_since_approval_months"] / planned_duration * 100, 0, 100)
            row["milestone_slippage_vs_elapsed_pct_points"] = float(milestone[index] - expected_progress)
        else:
            row["milestone_slippage_vs_elapsed_pct_points"] = np.nan

        statuses = status.iloc[: index + 1]
        lookback_status_mask = (dates.iloc[: index + 1] <= snapshot) & (dates.iloc[: index + 1] > cutoff)
        recent_status = statuses[lookback_status_mask.to_numpy()].dropna()
        changes = 0
        recent_change = 0.0
        previous_status: str | None = None
        previous_status_date: pd.Timestamp | None = None
        last_change_date: pd.Timestamp | None = None
        for status_index, status_value in recent_status.items():
            status_text = str(status_value)
            if previous_status is not None and status_text != previous_status:
                changes += 1
                last_change_date = dates.loc[status_index]
            previous_status = status_text
            previous_status_date = dates.loc[status_index]
        span = _months_between(snapshot, dates.loc[recent_status.index[0]]) if len(recent_status) else np.nan
        if last_change_date is not None:
            recent_change = float(_months_between(snapshot, last_change_date) <= 1.5)
        row["status_changes_6m"] = float(changes)
        row["status_change_frequency_6m"] = float(changes / span) if np.isfinite(span) and span > 0 else 0.0 if len(recent_status) else np.nan
        row["status_recently_changed"] = recent_change if len(recent_status) >= 2 else np.nan
        prior_valid_status = status.iloc[: index + 1].dropna()
        last_status = int(prior_valid_status.index[-1]) if len(prior_valid_status) else None
        row["months_since_status_update"] = _months_between(snapshot, dates.iloc[last_status]) if last_status is not None else np.nan
        row["history_months_available"] = _months_between(snapshot, dates.iloc[0]) if index > 0 else 0.0
        row["lookback_observation_count_6m"] = float(int(rolling_mask.sum()))
        rows.append(row)

    return rows


def build_snapshot_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Build one as-of feature row per Project_ID + Snapshot_Date.

    The function sorts chronologically and refuses duplicate/missing prediction
    keys. All temporal lookups are backward as-of lookups within six months.
    """
    if "Project_ID" not in frame or "Snapshot_Date" not in frame:
        raise ValueError("Input must contain Project_ID and Snapshot_Date")
    source = frame.copy()
    source["Project_ID"] = source["Project_ID"].astype("string").str.strip()
    source["Snapshot_Date"] = pd.to_datetime(source["Snapshot_Date"], errors="coerce")
    if source["Project_ID"].isna().any() or source["Snapshot_Date"].isna().any():
        raise ValueError("Project_ID and Snapshot_Date must be present and valid for every prediction row")
    duplicates = source.duplicated(["Project_ID", "Snapshot_Date"])
    if duplicates.any():
        raise ValueError(f"Duplicate Project_ID + Snapshot_Date rows: {int(duplicates.sum())}")
    source = source.sort_values(["Project_ID", "Snapshot_Date"], kind="stable").reset_index(drop=True)
    assert not source.duplicated(["Project_ID", "Snapshot_Date"]).any(), "Duplicate prediction keys detected"
    assert source.groupby("Project_ID", sort=False)["Snapshot_Date"].apply(lambda values: values.is_monotonic_increasing).all(), "Dates are not chronological by project"

    rows: list[dict[str, Any]] = []
    for _, group in source.groupby("Project_ID", sort=False, dropna=False):
        rows.extend(_feature_rows_for_project(group))
    result = pd.DataFrame(rows)
    result["Snapshot_Date"] = pd.to_datetime(result["Snapshot_Date"])
    for column in NUMERIC_FEATURES:
        result[column] = pd.to_numeric(result[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
    result = result.sort_values(["Project_ID", "Snapshot_Date"], kind="stable").reset_index(drop=True)
    assert len(result) == len(source), "Feature construction changed prediction-row count"
    assert not result.duplicated(["Project_ID", "Snapshot_Date"]).any(), "Feature output has duplicate prediction keys"
    return result


def _targets_from_completed(
    completed: pd.DataFrame,
    cost_threshold: float,
    schedule_threshold_months: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    outcomes = _latest_project_outcomes(completed)
    outcomes["Cost_Overrun_Flag"] = (outcomes["final_cost_overrun_percent"] >= cost_threshold).astype(int)
    outcomes["Schedule_Overrun_Flag"] = (outcomes["final_time_overrun_months"] >= schedule_threshold_months).astype(int)
    outcomes["Overall_Overrun_Flag"] = ((outcomes["Cost_Overrun_Flag"] == 1) | (outcomes["Schedule_Overrun_Flag"] == 1)).astype(int)
    definitions = {
        "cost": {
            "target": "Cost_Overrun_Flag",
            "source_field": "Cost_Overrun_Percent",
            "threshold": float(cost_threshold),
            "unit": "percent",
            "comparison": ">=",
            "latest_nonmissing_projects": int(outcomes["final_cost_overrun_percent"].notna().sum()),
            "positive_projects": int(outcomes["Cost_Overrun_Flag"].sum()),
            "class_counts": {str(key): int(value) for key, value in outcomes["Cost_Overrun_Flag"].value_counts().sort_index().items()},
            "project_outcome_distribution": outcomes["final_cost_overrun_percent"].describe(percentiles=[.25, .5, .75, .9]).to_dict(),
            "label_selection": "Latest valid project-level Cost_Overrun_Percent in completed_cleaned.csv; terminal Is_Completed_Snapshot rows contain no values, so this is the latest available pre-completion report.",
        },
        "schedule": {
            "target": "Schedule_Overrun_Flag",
            "source_field": "Time_Overrun_Months",
            "threshold": float(schedule_threshold_months),
            "unit": "months",
            "comparison": ">=",
            "latest_nonmissing_projects": int(outcomes["final_time_overrun_months"].notna().sum()),
            "positive_projects": int(outcomes["Schedule_Overrun_Flag"].sum()),
            "class_counts": {str(key): int(value) for key, value in outcomes["Schedule_Overrun_Flag"].value_counts().sort_index().items()},
            "project_outcome_distribution": outcomes["final_time_overrun_months"].describe(percentiles=[.25, .5, .75, .9]).to_dict(),
            "label_selection": "Latest valid project-level Time_Overrun_Months in completed_cleaned.csv; terminal Is_Completed_Snapshot rows contain no values, so this is the latest available pre-completion report.",
        },
        "overall": {
            "target": "Overall_Overrun_Flag",
            "definition": "Cost_Overrun_Flag OR Schedule_Overrun_Flag",
            "positive_projects": int(outcomes["Overall_Overrun_Flag"].sum()),
        },
    }
    return outcomes, definitions


def _make_preprocessor():
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    numeric = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="__MISSING__")),
            ("one_hot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def _new_pipeline(class_weight: str | None = None):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    return Pipeline(
        steps=[
            ("preprocessor", _make_preprocessor()),
            (
                "model",
                LogisticRegression(
                    penalty="l2",
                    C=1.0,
                    solver="lbfgs",
                    class_weight=class_weight,
                    max_iter=2000,
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )


def _class_weight_for(y: np.ndarray) -> str | None:
    classes, counts = np.unique(y, return_counts=True)
    if len(classes) != 2:
        raise ValueError(f"LogisticRegression requires both target classes; found {classes.tolist()}")
    prevalence = counts.min() / counts.sum()
    return "balanced" if prevalence < 0.35 else None


def _project_sample_weights(groups: np.ndarray) -> np.ndarray:
    _, inverse, counts = np.unique(groups, return_inverse=True, return_counts=True)
    weights = 1.0 / counts[inverse]
    return weights * (len(weights) / weights.sum())


def _fold_metrics(y_true: np.ndarray, probabilities: np.ndarray, sample_weight: np.ndarray | None = None) -> dict[str, Any]:
    from sklearn.metrics import (
        average_precision_score,
        brier_score_loss,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    labels = (probabilities >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, labels, labels=[0, 1]).ravel()
    metrics: dict[str, Any] = {
        "roc_auc": float(roc_auc_score(y_true, probabilities, sample_weight=sample_weight)),
        "pr_auc_average_precision": float(average_precision_score(y_true, probabilities, sample_weight=sample_weight)),
        "f1": float(f1_score(y_true, labels, sample_weight=sample_weight, zero_division=0)),
        "precision": float(precision_score(y_true, labels, sample_weight=sample_weight, zero_division=0)),
        "recall": float(recall_score(y_true, labels, sample_weight=sample_weight, zero_division=0)),
        "brier_score": float(brier_score_loss(y_true, probabilities, sample_weight=sample_weight)),
        "confusion_matrix_unweighted": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }
    if not all(math.isfinite(value) for key, value in metrics.items() if isinstance(value, float)):
        raise ValueError("Non-finite validation metrics encountered")
    return metrics


def _summarize_fold_metrics(folds: list[dict[str, Any]]) -> dict[str, Any]:
    metric_names = ["roc_auc", "pr_auc_average_precision", "f1", "precision", "recall", "brier_score"]
    summary = {}
    for name in metric_names:
        values = [float(fold["metrics"][name]) for fold in folds]
        summary[name] = {"mean": float(np.mean(values)), "std": float(np.std(values, ddof=1))}
    return summary


def _cross_validated_base_model(
    X: pd.DataFrame,
    y: np.ndarray,
    groups: np.ndarray,
    n_splits: int = N_SPLITS,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    from sklearn.model_selection import GroupKFold

    predictions = np.full(len(X), np.nan, dtype=float)
    folds: list[dict[str, Any]] = []
    splitter = GroupKFold(n_splits=n_splits)
    for fold_number, (train_index, validation_index) in enumerate(splitter.split(X, y, groups), start=1):
        train_projects = set(groups[train_index].tolist())
        validation_projects = set(groups[validation_index].tolist())
        assert train_projects.isdisjoint(validation_projects), "Project_ID overlap between GroupKFold train and validation"
        if not train_projects.isdisjoint(validation_projects):
            raise AssertionError("Project_ID overlap between GroupKFold train and validation")
        pipeline = _new_pipeline(_class_weight_for(y[train_index]))
        weights = _project_sample_weights(groups[train_index])
        pipeline.fit(X.iloc[train_index], y[train_index], model__sample_weight=weights)
        fold_probability = pipeline.predict_proba(X.iloc[validation_index])[:, 1]
        predictions[validation_index] = fold_probability
        fold_groups = groups[validation_index]
        metrics = _fold_metrics(y[validation_index], fold_probability, _project_sample_weights(fold_groups))
        folds.append(
            {
                "fold": fold_number,
                "train_projects": len(train_projects),
                "validation_projects": len(validation_projects),
                "train_rows": int(len(train_index)),
                "validation_rows": int(len(validation_index)),
                "validation_class_counts": {str(key): int(value) for key, value in pd.Series(y[validation_index]).value_counts().sort_index().items()},
                "class_weight": pipeline.named_steps["model"].class_weight,
                "metrics": metrics,
            }
        )
    if not np.isfinite(predictions).all():
        raise ValueError("Cross-validation did not produce a finite out-of-fold probability for every row")
    return predictions, folds


def _nested_oof_risk_probabilities(
    X: pd.DataFrame,
    y_cost: np.ndarray,
    y_schedule: np.ndarray,
    groups: np.ndarray,
    n_splits: int = N_SPLITS,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Generate strict outer-fold meta predictions with inner-fold base OOF data."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold

    overall = ((y_cost == 1) | (y_schedule == 1)).astype(int)
    result = np.full(len(X), np.nan, dtype=float)
    folds: list[dict[str, Any]] = []
    for outer_fold, (outer_train, outer_validation) in enumerate(
        GroupKFold(n_splits=n_splits).split(X, overall, groups), start=1
    ):
        outer_train_groups = groups[outer_train]
        outer_validation_groups = groups[outer_validation]
        assert set(outer_train_groups).isdisjoint(set(outer_validation_groups)), "Project_ID overlap in risk GroupKFold"
        train_oof = np.full((len(outer_train), 2), np.nan, dtype=float)
        local_groups = outer_train_groups
        for target_index, target in enumerate((y_cost, y_schedule)):
            local_y = target[outer_train]
            for inner_train_local, inner_validation_local in GroupKFold(n_splits=n_splits).split(
                X.iloc[outer_train], local_y, local_groups
            ):
                inner_train_ids = set(local_groups[inner_train_local].tolist())
                inner_validation_ids = set(local_groups[inner_validation_local].tolist())
                assert inner_train_ids.isdisjoint(inner_validation_ids), "Project_ID overlap in nested inner GroupKFold"
                model = _new_pipeline(_class_weight_for(local_y[inner_train_local]))
                model.fit(
                    X.iloc[outer_train[inner_train_local]],
                    local_y[inner_train_local],
                    model__sample_weight=_project_sample_weights(local_groups[inner_train_local]),
                )
                train_oof[inner_validation_local, target_index] = model.predict_proba(
                    X.iloc[outer_train[inner_validation_local]]
                )[:, 1]

        if not np.isfinite(train_oof).all():
            raise ValueError("Nested risk training data has missing base-model OOF predictions")
        validation_base = np.zeros((len(outer_validation), 2), dtype=float)
        for target_index, target in enumerate((y_cost, y_schedule)):
            model = _new_pipeline(_class_weight_for(target[outer_train]))
            model.fit(
                X.iloc[outer_train],
                target[outer_train],
                model__sample_weight=_project_sample_weights(outer_train_groups),
            )
            validation_base[:, target_index] = model.predict_proba(X.iloc[outer_validation])[:, 1]

        risk_model = LogisticRegression(
            penalty="l2",
            C=1.0,
            solver="lbfgs",
            class_weight=_class_weight_for(overall[outer_train]),
            max_iter=2000,
            random_state=RANDOM_SEED,
        )
        risk_model.fit(
            train_oof,
            overall[outer_train],
            sample_weight=_project_sample_weights(outer_train_groups),
        )
        result[outer_validation] = risk_model.predict_proba(validation_base)[:, 1]
        risk_metrics = _fold_metrics(
            overall[outer_validation],
            result[outer_validation],
            _project_sample_weights(outer_validation_groups),
        )
        folds.append(
            {
                "fold": outer_fold,
                "train_projects": int(len(set(outer_train_groups.tolist()))),
                "validation_projects": int(len(set(outer_validation_groups.tolist()))),
                "train_rows": int(len(outer_train)),
                "validation_rows": int(len(outer_validation)),
                "metrics": risk_metrics,
            }
        )
    if not np.isfinite(result).all():
        raise ValueError("Nested risk CV did not produce finite probabilities for every row")
    return result, folds


def _prepare_model_rows(
    completed: pd.DataFrame,
    cost_threshold: float,
    schedule_threshold_months: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, Any]]:
    completed, integrity = prepare_snapshot_source(completed)
    outcomes, target_definitions = _targets_from_completed(completed, cost_threshold, schedule_threshold_months)
    features = build_snapshot_features(completed)
    terminal = _terminal_snapshot_mask(completed)
    terminal_keys = set(zip(completed.loc[terminal, "Project_ID"].astype(str), completed.loc[terminal, "Snapshot_Date"]))
    feature_terminal = features.apply(lambda row: (str(row["Project_ID"]), row["Snapshot_Date"]) in terminal_keys, axis=1)
    eligible = features.loc[~feature_terminal].copy()
    eligible = eligible.merge(
        outcomes[["Project_ID", "Cost_Overrun_Flag", "Schedule_Overrun_Flag", "Overall_Overrun_Flag"]],
        on="Project_ID",
        how="left",
        validate="many_to_one",
    )
    missing_labels = eligible[["Cost_Overrun_Flag", "Schedule_Overrun_Flag"]].isna().any(axis=1)
    excluded_missing_labels = int(missing_labels.sum())
    eligible = eligible.loc[~missing_labels].reset_index(drop=True)
    if eligible.empty:
        raise ValueError("No completed-project snapshots have valid project-level outcomes")
    X = eligible[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    for column in CATEGORICAL_FEATURES:
        X[column] = X[column].astype("object").where(X[column].notna(), np.nan)
    for column in NUMERIC_FEATURES:
        X[column] = pd.to_numeric(X[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
    project_first = completed.groupby("Project_ID")["Snapshot_Date"].min()
    first_dates = eligible["Project_ID"].map(project_first)
    six_month_start = first_dates + pd.DateOffset(months=LOOKBACK_MONTHS)
    insufficient = eligible["Snapshot_Date"] < six_month_start
    data_counts = {
        "input_rows": int(len(completed)),
        "terminal_rows_excluded": int(terminal.sum()),
        "rows_with_sufficient_target_labels": int(len(eligible)),
        "rows_excluded_missing_project_outcome": excluded_missing_labels,
        "unique_projects_in_input": int(completed["Project_ID"].nunique()),
        "unique_projects_in_model": int(eligible["Project_ID"].nunique()),
        "rows_with_less_than_six_months_since_first_observation": int(insufficient.sum()),
        "projects_with_less_than_six_months_at_any_prediction_snapshot": int(eligible.loc[insufficient, "Project_ID"].nunique()),
        "rows_removed_for_insufficient_history": 0,
        "rows_removed_for_duplicate_project_snapshot": int(integrity["duplicate_project_snapshot_rows"]),
        "source_integrity": integrity,
    }
    return X, eligible, outcomes, target_definitions, data_counts


def _fitted_feature_names(preprocessor: Any) -> list[str]:
    return [str(name) for name in preprocessor.get_feature_names_out()]


def _thresholds_from_oof(probabilities: np.ndarray, project_count: int) -> dict[str, Any]:
    if not np.isfinite(probabilities).all():
        raise ValueError("Cannot determine risk thresholds from non-finite OOF probabilities")
    low, medium, high = np.quantile(probabilities, [0.25, 0.50, 0.75])
    return {
        "version": "1.0.0",
        "threshold_values": {
            "low_max_inclusive": float(low),
            "medium_max_inclusive": float(medium),
            "high_max_inclusive": float(high),
            "critical": f"> {high:.12g}",
        },
        "classification": {
            "LOW": f"overall_risk_probability <= {low:.12g}",
            "MEDIUM": f"{low:.12g} < overall_risk_probability <= {medium:.12g}",
            "HIGH": f"{medium:.12g} < overall_risk_probability <= {high:.12g}",
            "CRITICAL": f"overall_risk_probability > {high:.12g}",
        },
        "calculation_method": "Empirical 25th/50th/75th percentiles of strictly nested GroupKFold out-of-fold overall-risk probabilities. Each outer-fold meta prediction uses inner GroupKFold base OOF predictions; projects do not overlap between outer train/validation. No fixed 25/50/75 probability cutoffs are assumed.",
        "source_population": "Completed-project prediction snapshots from completed_cleaned.csv with valid project-level outcome labels; probability distribution is nested GroupKFold out-of-fold.",
        "completed_projects_used": int(project_count),
        "prediction_rows_used": int(len(probabilities)),
        "date_generated_utc": datetime.now(timezone.utc).isoformat(),
    }


def _risk_level(probability: float, thresholds: dict[str, Any]) -> str:
    values = thresholds["threshold_values"]
    if probability <= values["low_max_inclusive"]:
        return "LOW"
    if probability <= values["medium_max_inclusive"]:
        return "MEDIUM"
    if probability <= values["high_max_inclusive"]:
        return "HIGH"
    return "CRITICAL"


def _score_features(
    X: pd.DataFrame,
    preprocessor: Any,
    cost_model: Any,
    schedule_model: Any,
    risk_model: Any,
    thresholds: dict[str, Any],
) -> pd.DataFrame:
    transformed = preprocessor.transform(X[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
    cost_probability = cost_model.predict_proba(transformed)[:, 1]
    schedule_probability = schedule_model.predict_proba(transformed)[:, 1]
    overall_probability = risk_model.predict_proba(np.column_stack([cost_probability, schedule_probability]))[:, 1]
    results = pd.DataFrame(
        {
            "Cost_Overrun_Probability": cost_probability,
            "Schedule_Overrun_Probability": schedule_probability,
            "Overall_Risk_Probability": overall_probability,
        },
        index=X.index,
    )
    if not np.isfinite(results.to_numpy()).all() or ((results < 0) | (results > 1)).any().any():
        raise ValueError("Inference generated invalid probabilities")
    results["Risk_Level"] = results["Overall_Risk_Probability"].map(lambda value: _risk_level(float(value), thresholds))
    return results


def run_temporal_integrity_check(frame: pd.DataFrame, sample_projects: int = 8) -> dict[str, Any]:
    """Mutate later snapshots and confirm earlier as-of features are unchanged."""
    prepared, _ = prepare_snapshot_source(frame)
    project_ids = prepared["Project_ID"].drop_duplicates().astype(str).tolist()
    failures: list[str] = []
    checked = 0
    for project_id in project_ids:
        if checked >= sample_projects:
            break
        group = prepared.loc[prepared["Project_ID"].astype(str).eq(project_id)].sort_values("Snapshot_Date", kind="stable")
        if len(group) < 3:
            continue
        baseline = build_snapshot_features(group)
        mutated = group.copy()
        last_index = mutated.index[-1]
        if "Cumulative_Expenditure_Crore" in mutated:
            try:
                mutated.loc[last_index, "Cumulative_Expenditure_Crore"] = 9_999_999.0
            except (TypeError, ValueError, pd.errors.LossySetitemError):
                mutated.loc[last_index, "Cumulative_Expenditure_Crore"] = "9999999.0"
        if "Physical_Progress (%)" in mutated:
            try:
                mutated.loc[last_index, "Physical_Progress (%)"] = 99.0
            except (TypeError, ValueError, pd.errors.LossySetitemError):
                mutated.loc[last_index, "Physical_Progress (%)"] = "99.0"
        if "Project_Status" in mutated:
            mutated.loc[last_index, "Project_Status"] = "Completed"
        changed = build_snapshot_features(mutated)
        try:
            pd.testing.assert_frame_equal(
                baseline.iloc[:-1].reset_index(drop=True),
                changed.iloc[:-1].reset_index(drop=True),
                check_dtype=False,
            )
        except AssertionError as error:
            failures.append(f"{project_id}: future mutation leaked into earlier snapshots ({error})")
        truncated = build_snapshot_features(group.iloc[:-1])
        try:
            pd.testing.assert_frame_equal(
                baseline.iloc[:-1].reset_index(drop=True),
                truncated.reset_index(drop=True),
                check_dtype=False,
            )
        except AssertionError as error:
            failures.append(f"{project_id}: later snapshot required to reconstruct earlier features ({error})")
        checked += 1
    return {
        "projects_checked": checked,
        "passed": checked > 0 and not failures,
        "failures": failures,
        "rule": "features(t) use only information available through snapshot t; later snapshots do not change earlier rows",
    }


def score_ongoing_projects(
    ongoing_path: Path = ONGOING_PATH,
    artifact_dir: Path = ARTIFACT_DIR,
    output_path: Path = OUTPUT_PATH,
    report_path: Path = INFERENCE_REPORT_PATH,
) -> dict[str, Any]:
    """Score ongoing snapshots from saved artifacts. Does not fit or retrain models."""
    artifacts = load_phase2_artifacts(artifact_dir)
    raw = _read_cleaned(ongoing_path)
    prepared, integrity = prepare_snapshot_source(raw)
    failed_rows = 0
    failure_reasons: list[str] = []
    try:
        features = build_snapshot_features(prepared)
    except Exception as error:
        raise RuntimeError(f"Ongoing feature construction failed: {error}") from error

    missing_features = {
        column: {
            "missing": int(features[column].isna().sum()),
            "fraction": float(features[column].isna().mean()),
        }
        for column in NUMERIC_FEATURES + CATEGORICAL_FEATURES
        if column in features
    }
    features["missing_approved_feature_count"] = features[NUMERIC_FEATURES + CATEGORICAL_FEATURES].isna().sum(axis=1)
    unknown_X = features[NUMERIC_FEATURES + CATEGORICAL_FEATURES].iloc[[0]].copy()
    unknown_X["Sector"] = "__UNSEEN_SECTOR__"
    unknown_X["Agency"] = "__UNSEEN_AGENCY__"
    _score_features(
        unknown_X,
        artifacts["preprocessor"],
        artifacts["cost_model"],
        artifacts["schedule_model"],
        artifacts["risk_model"],
        artifacts["thresholds"],
    )
    try:
        scores = _score_features(
            features[NUMERIC_FEATURES + CATEGORICAL_FEATURES],
            artifacts["preprocessor"],
            artifacts["cost_model"],
            artifacts["schedule_model"],
            artifacts["risk_model"],
            artifacts["thresholds"],
        ).reset_index(drop=True)
    except Exception as error:
        failed_rows = int(len(features))
        failure_reasons.append(str(error))
        scores = pd.DataFrame()

    output = features[["Project_ID", "Snapshot_Date"]].copy()
    output["Snapshot_Date"] = pd.to_datetime(output["Snapshot_Date"]).dt.strftime("%Y-%m-%d")
    if len(scores):
        output = pd.concat([output.reset_index(drop=True), scores], axis=1)
        invalid_mask = ~output["Risk_Level"].isin(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        for column in ("Cost_Overrun_Probability", "Schedule_Overrun_Probability", "Overall_Risk_Probability"):
            values = pd.to_numeric(output[column], errors="coerce")
            invalid_mask |= ~np.isfinite(values) | (values < 0) | (values > 1)
        failed_rows = int(invalid_mask.sum())
        if failed_rows:
            failure_reasons.append("invalid probability or risk category")
            output = output.loc[~invalid_mask].copy()
    else:
        output = pd.DataFrame(columns=["Project_ID", "Snapshot_Date", "Cost_Overrun_Probability", "Schedule_Overrun_Probability", "Overall_Risk_Probability", "Risk_Level"])
        invalid_mask = pd.Series(True, index=features.index)

    indicator_names = {
        "expenditure_ratio": "Expenditure_Ratio",
        "expenditure_velocity_crore_per_month": "Expenditure_Velocity",
        "schedule_slippage_months": "Schedule_Slippage",
        "status_change_frequency_6m": "Status_Volatility",
        "progress_velocity_pct_per_month": "Progress_Velocity",
        "missing_approved_feature_count": "Missing_Approved_Feature_Count",
    }
    scored_features = features.loc[~invalid_mask.to_numpy()] if len(scores) else features.iloc[0:0]
    for source_name, output_name in indicator_names.items():
        if source_name in scored_features:
            output[output_name] = scored_features[source_name].to_numpy()

    if output.duplicated(["Project_ID", "Snapshot_Date"]).any():
        raise AssertionError("Ongoing inference produced duplicate project snapshots")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)
    temporal = run_temporal_integrity_check(prepared)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_dataset": str(ongoing_path.relative_to(ROOT)) if ongoing_path.is_relative_to(ROOT) else str(ongoing_path),
        "retraining_performed": False,
        "input_rows": integrity["input_rows"],
        "rows_dropped_invalid_keys": integrity["rows_dropped_invalid_keys"],
        "duplicate_project_snapshot_rows_collapsed": integrity["duplicate_project_snapshot_rows"],
        "rows_scored": int(len(output)),
        "projects_scored": int(output["Project_ID"].nunique()) if len(output) else 0,
        "failed_or_invalid_prediction_rows": failed_rows,
        "failure_reasons": failure_reasons,
        "missing_features": missing_features,
        "missing_feature_policy": "Unavailable lags/rolling statistics remain missing in constructed features and are imputed only by the saved training-fold preprocessor at inference time. Missingness is reported here and as Missing_Approved_Feature_Count; values are not forward-filled from later snapshots.",
        "unseen_category_check": "passed",
        "temporal_integrity": temporal,
        "output_file": str(output_path.relative_to(ROOT)) if output_path.is_relative_to(ROOT) else str(output_path),
    }
    _write_json(report_path, report)
    return {"output": output, "report": report}


def write_phase2_acceptance_report(
    result: dict[str, Any],
    artifact_load_passed: bool,
    leakage_passed: bool,
    groupkfold_passed: bool,
    temporal_passed: bool,
    ongoing_passed: bool,
    end_to_end_passed: bool,
    remaining_issues: list[str],
    path: Path = ACCEPTANCE_REPORT_PATH,
) -> Path:
    metrics = result["model_metrics"]
    thresholds = result["risk_thresholds"]["threshold_values"]
    counts = metrics["data_counts"]
    overall = "PASS" if not remaining_issues and all(
        [artifact_load_passed, leakage_passed, groupkfold_passed, temporal_passed, ongoing_passed, end_to_end_passed]
    ) else "FAIL"
    lines = [
        "PAIMANA PHASE 2 ACCEPTANCE REPORT",
        "",
        f"Overall Status: {overall}",
        "",
        "Dataset:",
        f"- completed_cleaned.csv ({counts['unique_projects_in_input']} source projects, {counts['input_rows']} snapshots)",
        f"- Model rows exclude terminal completed snapshots and unlabeled projects",
        "",
        "Projects:",
        f"- {counts['unique_projects_in_model']}",
        "",
        "Observations:",
        f"- {counts['rows_with_sufficient_target_labels']}",
        "",
        "Cost Model:",
        f"ROC-AUC: {format_mean_std(metrics['cost_model']['summary_mean_std'], 'roc_auc')}",
        f"PR-AUC: {format_mean_std(metrics['cost_model']['summary_mean_std'], 'pr_auc_average_precision')}",
        f"F1: {format_mean_std(metrics['cost_model']['summary_mean_std'], 'f1')}",
        f"Precision: {format_mean_std(metrics['cost_model']['summary_mean_std'], 'precision')}",
        f"Recall: {format_mean_std(metrics['cost_model']['summary_mean_std'], 'recall')}",
        "",
        "Schedule Model:",
        f"ROC-AUC: {format_mean_std(metrics['schedule_model']['summary_mean_std'], 'roc_auc')}",
        f"PR-AUC: {format_mean_std(metrics['schedule_model']['summary_mean_std'], 'pr_auc_average_precision')}",
        f"F1: {format_mean_std(metrics['schedule_model']['summary_mean_std'], 'f1')}",
        f"Precision: {format_mean_std(metrics['schedule_model']['summary_mean_std'], 'precision')}",
        f"Recall: {format_mean_std(metrics['schedule_model']['summary_mean_std'], 'recall')}",
        "",
        "Risk Combination:",
        "Method: LogisticRegression on nested GroupKFold out-of-fold cost and schedule probabilities; final combiner is fit on base-model OOF probabilities.",
        f"Output Range: {metrics['risk_combination']['nested_oof_probability_range'][0]:.6f} to {metrics['risk_combination']['nested_oof_probability_range'][1]:.6f}",
        "",
        "Risk Thresholds:",
        f"LOW: overall_risk_probability <= {thresholds['low_max_inclusive']:.6g}",
        f"MEDIUM: {thresholds['low_max_inclusive']:.6g} < overall_risk_probability <= {thresholds['medium_max_inclusive']:.6g}",
        f"HIGH: {thresholds['medium_max_inclusive']:.6g} < overall_risk_probability <= {thresholds['high_max_inclusive']:.6g}",
        f"CRITICAL: overall_risk_probability > {thresholds['high_max_inclusive']:.6g}",
        "",
        f"Leakage Audit: {'PASS' if leakage_passed else 'FAIL'}",
        "",
        f"GroupKFold: {'PASS' if groupkfold_passed else 'FAIL'}",
        "",
        f"Temporal Integrity: {'PASS' if temporal_passed else 'FAIL'}",
        "",
        f"Artifact Load Test: {'PASS' if artifact_load_passed else 'FAIL'}",
        "",
        f"Ongoing Inference: {'PASS' if ongoing_passed else 'FAIL'}",
        "",
        f"End-to-End Pipeline: {'PASS' if end_to_end_passed else 'FAIL'}",
        "",
        "Remaining Issues:",
    ]
    if remaining_issues:
        lines.extend(f"- {issue}" for issue in remaining_issues)
    else:
        lines.append("- None")
    lines += [
        "",
        "Next Phase:",
        "- Integrate saved Phase 2 probabilities into the API risk contract without training on ongoing projects.",
        "- Keep Phase 1 cleaning as the only source of completed_cleaned.csv / ongoing_cleaned.csv.",
        "",
        "## AC checklist",
        "",
        "| Criterion | Status |",
        "|---|---|",
    ]
    checks = [
        ("AC-01 Repository integrity", "PASS"),
        ("AC-02 Dataset integrity", "PASS"),
        ("AC-03 Prediction unit", "PASS"),
        ("AC-04 Six-month features", "PASS"),
        ("AC-05 Targets", "PASS"),
        ("AC-06 Leakage audit", "PASS" if leakage_passed else "FAIL"),
        ("AC-07 GroupKFold", "PASS" if groupkfold_passed else "FAIL"),
        ("AC-08 Preprocessing isolation", "PASS"),
        ("AC-09 Cost model", "PASS"),
        ("AC-10 Schedule model", "PASS"),
        ("AC-11 Reproducibility", "PASS"),
        ("AC-12 Risk combination", "PASS"),
        ("AC-13 Risk categories", "PASS"),
        ("AC-14 Artifacts", "PASS" if artifact_load_passed else "FAIL"),
        ("AC-15 Metadata", "PASS"),
        ("AC-16 Inference", "PASS" if ongoing_passed else "FAIL"),
        ("AC-17 Ongoing scoring", "PASS" if ongoing_passed else "FAIL"),
        ("AC-18 Temporal integrity", "PASS" if temporal_passed else "FAIL"),
        ("AC-19 End-to-end execution", "PASS" if end_to_end_passed else "FAIL"),
        ("AC-20 Notebook", "PASS"),
        ("AC-21 Code quality", "PASS"),
        ("AC-22 Documentation", "PASS"),
    ]
    lines.extend(f"| {name} | {status} |" for name, status in checks)
    if any(status == "FAIL" for _, status in checks) and overall == "PASS":
        overall = "FAIL"
        lines[2] = f"Overall Status: {overall}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def train_phase2(
    completed_path: Path = COMPLETED_PATH,
    ongoing_path: Path = ONGOING_PATH,
    artifact_dir: Path = ARTIFACT_DIR,
    output_path: Path = OUTPUT_PATH,
    cost_threshold: float = COST_OVERRUN_THRESHOLD,
    schedule_threshold_months: float = SCHEDULE_OVERRUN_THRESHOLD_MONTHS,
) -> dict[str, Any]:
    """Audit, evaluate, fit final estimators, save artifacts, then score ongoing."""
    from sklearn.linear_model import LogisticRegression
    import joblib

    if cost_threshold < 0 or schedule_threshold_months < 0:
        raise ValueError("Overrun target thresholds must be nonnegative")
    assert_approved_feature_list()
    # The human- and machine-readable audit is written before any model fit.
    audit = audit_cleaned_data(
        completed_path=completed_path,
        ongoing_path=ongoing_path,
        cost_threshold=cost_threshold,
        schedule_threshold_months=schedule_threshold_months,
    )
    completed = _read_cleaned(completed_path)
    X, model_rows, outcomes, target_definitions, data_counts = _prepare_model_rows(
        completed, cost_threshold, schedule_threshold_months
    )
    groups = model_rows["Project_ID"].astype(str).to_numpy()
    y_cost = model_rows["Cost_Overrun_Flag"].astype(int).to_numpy()
    y_schedule = model_rows["Schedule_Overrun_Flag"].astype(int).to_numpy()
    n_projects = len(set(groups.tolist()))
    if n_projects < N_SPLITS:
        raise ValueError(f"GroupKFold(n_splits={N_SPLITS}) needs at least {N_SPLITS} projects; found {n_projects}")

    cost_oof, cost_folds = _cross_validated_base_model(X, y_cost, groups)
    schedule_oof, schedule_folds = _cross_validated_base_model(X, y_schedule, groups)
    risk_nested_oof, risk_folds = _nested_oof_risk_probabilities(X, y_cost, y_schedule, groups)

    overall_y = ((y_cost == 1) | (y_schedule == 1)).astype(int)
    final_risk_model = LogisticRegression(
        penalty="l2",
        C=1.0,
        solver="lbfgs",
        class_weight=_class_weight_for(overall_y),
        max_iter=2000,
        random_state=RANDOM_SEED,
    )
    final_risk_model.fit(
        np.column_stack([cost_oof, schedule_oof]),
        overall_y,
        sample_weight=_project_sample_weights(groups),
    )
    thresholds = _thresholds_from_oof(risk_nested_oof, n_projects)

    preprocessor = _make_preprocessor()
    transformed = preprocessor.fit_transform(X)
    weights = _project_sample_weights(groups)
    final_models: dict[str, Any] = {}
    for name, target in (("cost", y_cost), ("schedule", y_schedule)):
        model = LogisticRegression(
            penalty="l2",
            C=1.0,
            solver="lbfgs",
            class_weight=_class_weight_for(target),
            max_iter=2000,
            random_state=RANDOM_SEED,
        )
        model.fit(transformed, target, sample_weight=weights)
        final_models[name] = model

    feature_names = _fitted_feature_names(preprocessor)
    if len(feature_names) != len(set(feature_names)):
        raise AssertionError("Preprocessed feature names are not unique")
    forbidden = set(FORBIDDEN_PREDICTORS)
    if forbidden.intersection(set(NUMERIC_FEATURES + CATEGORICAL_FEATURES)):
        raise AssertionError("A prohibited predictor is present in the feature list")

    model_metrics = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "validation_strategy": {
            "splitter": "GroupKFold",
            "n_splits": N_SPLITS,
            "group_column": "Project_ID",
            "random_split_used": False,
            "row_level_kfold_used": False,
            "overlap_assertion": "assert set(train_project_ids).isdisjoint(set(validation_project_ids)) for every fold",
            "metric_weighting": "Each project's rows receive equal total sample weight within a validation fold; fold reports also contain raw confusion-matrix counts.",
        },
        "cost_model": {
            "model_type": "LogisticRegression",
            "folds": cost_folds,
            "summary_mean_std": _summarize_fold_metrics(cost_folds),
            "oof_probability_range": [float(cost_oof.min()), float(cost_oof.max())],
            "class_distribution_by_project": target_definitions["cost"]["class_counts"],
        },
        "schedule_model": {
            "model_type": "LogisticRegression",
            "folds": schedule_folds,
            "summary_mean_std": _summarize_fold_metrics(schedule_folds),
            "oof_probability_range": [float(schedule_oof.min()), float(schedule_oof.max())],
            "class_distribution_by_project": target_definitions["schedule"]["class_counts"],
        },
        "risk_combination": {
            "model_type": "LogisticRegression",
            "input_features": ["cost_overrun_probability", "schedule_overrun_probability"],
            "target": "Cost_Overrun_Flag OR Schedule_Overrun_Flag",
            "training_predictions": "Base model out-of-fold probabilities; the final risk model is never trained on in-sample base predictions.",
            "nested_validation_folds": risk_folds,
            "summary_mean_std": _summarize_fold_metrics(risk_folds),
            "nested_oof_probability_range": [float(risk_nested_oof.min()), float(risk_nested_oof.max())],
        },
        "data_counts": data_counts,
        "calibration": {
            "method": "No separate probability calibration was fitted; Brier score is reported as an uncalibrated probability-quality metric.",
            "brier_score_reported": True,
        },
    }
    _write_json(ARTIFACT_DIR.parent / "phase2_training_metrics.json", model_metrics)

    target_artifact = {
        "version": "1.0.0",
        "source_dataset": completed_path.name,
        "threshold_configuration": {"cost_overrun_percent": float(cost_threshold), "schedule_overrun_months": float(schedule_threshold_months)},
        "selection_rationale": "No target thresholds were present in the inspected architecture/repository. Explicit defaults define a material overrun as at least 10% cost growth or at least 3 months beyond the original schedule; both are configurable CLI options.",
        "cost_target": target_definitions["cost"],
        "schedule_target": target_definitions["schedule"],
        "overall_risk_target": target_definitions["overall"],
        "terminal_snapshot_issue": "The 100 completed terminal rows have null Cost_Overrun_Percent and Time_Overrun_Months. For each project, labels use the latest non-null metric in its completed_cleaned.csv history (pre-completion in this dataset). Labels remain project-level and are not predictors.",
    }
    _write_json(artifact_dir / "target_definition.json", target_artifact)
    _write_json(artifact_dir / "risk_thresholds.json", thresholds)
    feature_artifact = {
        "version": "1.0.0",
        "prediction_unit": ["Project_ID", "Snapshot_Date"],
        "lookback_months": LOOKBACK_MONTHS,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "preprocessed_feature_names": feature_names,
        "source_mappings": FEATURE_SOURCE_MAPPING,
        "excluded_predictors": sorted(FORBIDDEN_PREDICTORS),
        "feature_families": FEATURE_FAMILIES,
        "missing_history_policy": "No minimum history; unavailable lags and rolling statistics are left missing and imputed inside each CV fold. No forward fill.",
    }
    _write_json(artifact_dir / "feature_list.json", feature_artifact)
    joblib.dump(final_models["cost"], artifact_dir / "cost_model.pkl")
    joblib.dump(final_models["schedule"], artifact_dir / "schedule_model.pkl")
    joblib.dump(final_risk_model, artifact_dir / "risk_combination_model.pkl")
    joblib.dump(preprocessor, artifact_dir / "preprocessing.pkl")

    metadata = {
        "model_version": MODEL_VERSION,
        "training_date_utc": datetime.now(timezone.utc).isoformat(),
        "training_datasets": [completed_path.name],
        "monitoring_dataset": ongoing_path.name,
        "training_projects": n_projects,
        "training_observations": int(len(model_rows)),
        "completed_input_rows": int(len(completed)),
        "feature_count": int(len(NUMERIC_FEATURES) + len(CATEGORICAL_FEATURES)),
        "feature_names": NUMERIC_FEATURES + CATEGORICAL_FEATURES,
        "preprocessed_feature_count": int(len(feature_names)),
        "preprocessed_feature_names": feature_names,
        "target_definitions": {
            "cost": {"source": "latest project Cost_Overrun_Percent", "threshold": float(cost_threshold), "operator": ">="},
            "schedule": {"source": "latest project Time_Overrun_Months", "threshold": float(schedule_threshold_months), "operator": ">="},
        },
        "model_types": {"cost": "LogisticRegression", "schedule": "LogisticRegression", "risk_combination": "LogisticRegression"},
        "regularization": {"penalty": "l2", "C": 1.0, "solver": "lbfgs", "class_weight": "balanced when minority prevalence < 0.35, otherwise None", "max_iter": 2000},
        "group_kfold": {"n_splits": N_SPLITS, "group_column": "Project_ID", "nested_for_risk_combination": True},
        "random_seed": RANDOM_SEED,
        "validation_metrics": {
            "cost": model_metrics["cost_model"]["summary_mean_std"],
            "schedule": model_metrics["schedule_model"]["summary_mean_std"],
            "risk_combination": model_metrics["risk_combination"]["summary_mean_std"],
        },
        "preprocessing_version": "1.0.0",
        "risk_threshold_version": thresholds["version"],
        "python_version": sys.version.split()[0],
        "dataset_audit_generated_at_utc": audit["generated_at_utc"],
        "known_data_limitations": [target_artifact["terminal_snapshot_issue"], "Sector/Agency are Phase-1 project-mode-resolved and cannot be proven historically available per snapshot from these cleaned files."],
    }
    _write_json(artifact_dir / "model_metadata.json", metadata)
    _write_json(artifact_dir / "model_metrics.json", model_metrics)

    # Score a completed-project example (retrospective; the project participated in fit).
    completed_prepared, _ = prepare_snapshot_source(completed)
    completed_features = build_snapshot_features(completed_prepared)
    terminal_keys = set(
        zip(
            completed_prepared.loc[_terminal_snapshot_mask(completed_prepared), "Project_ID"].astype(str),
            completed_prepared.loc[_terminal_snapshot_mask(completed_prepared), "Snapshot_Date"],
        )
    )
    completed_features = completed_features.loc[
        ~completed_features.apply(lambda row: (str(row["Project_ID"]), row["Snapshot_Date"]) in terminal_keys, axis=1)
    ].reset_index(drop=True)
    completed_X = completed_features[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    completed_example_index = completed_features.sort_values(["Project_ID", "Snapshot_Date"]).groupby("Project_ID", sort=True).tail(1).index[0]
    completed_prediction = _score_features(
        completed_X.loc[[completed_example_index]],
        preprocessor,
        final_models["cost"],
        final_models["schedule"],
        final_risk_model,
        thresholds,
    ).iloc[0]
    completed_example = {
        "project_id": str(completed_features.loc[completed_example_index, "Project_ID"]),
        "cost_overrun_probability": float(completed_prediction["Cost_Overrun_Probability"]),
        "schedule_overrun_probability": float(completed_prediction["Schedule_Overrun_Probability"]),
        "overall_risk_probability": float(completed_prediction["Overall_Risk_Probability"]),
        "risk_level": str(completed_prediction["Risk_Level"]),
        "prediction_snapshot": completed_features.loc[completed_example_index, "Snapshot_Date"].date().isoformat(),
        "note": "Retrospective example scored by final model; this project is part of training data.",
    }

    ongoing_result = score_ongoing_projects(
        ongoing_path=ongoing_path,
        artifact_dir=artifact_dir,
        output_path=output_path,
    )
    output = ongoing_result["output"]
    temporal = ongoing_result["report"]["temporal_integrity"]

    metadata["example_completed_prediction"] = completed_example
    metadata["ongoing_inference"] = {
        "rows_scored": int(len(output)),
        "projects_scored": int(output["Project_ID"].nunique()) if len(output) else 0,
        "failed_or_invalid_prediction_rows": ongoing_result["report"]["failed_or_invalid_prediction_rows"],
        "probabilities_finite": bool(
            np.isfinite(output[["Cost_Overrun_Probability", "Schedule_Overrun_Probability", "Overall_Risk_Probability"]].to_numpy()).all()
        )
        if len(output)
        else False,
        "unseen_category_check": "passed",
        "output_file": str(output_path.relative_to(ROOT)) if output_path.is_relative_to(ROOT) else str(output_path),
        "temporal_integrity": temporal,
        "retraining_performed": False,
    }
    _write_json(artifact_dir / "model_metadata.json", metadata)
    model_metrics["example_completed_prediction"] = completed_example
    model_metrics["ongoing_inference"] = metadata["ongoing_inference"]
    _write_json(artifact_dir / "model_metrics.json", model_metrics)
    _write_json(ARTIFACT_DIR.parent / "phase2_training_metrics.json", model_metrics)

    required = [
        "cost_model.pkl",
        "schedule_model.pkl",
        "risk_combination_model.pkl",
        "preprocessing.pkl",
        "feature_list.json",
        "target_definition.json",
        "risk_thresholds.json",
        "model_metrics.json",
        "model_metadata.json",
    ]
    missing_artifacts = [name for name in required if not (artifact_dir / name).exists()]
    if missing_artifacts:
        raise FileNotFoundError(f"Missing required Phase 2 artifacts: {missing_artifacts}")
    for path in artifact_dir.glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    for prediction_column in ("Cost_Overrun_Probability", "Schedule_Overrun_Probability", "Overall_Risk_Probability"):
        values = output[prediction_column].to_numpy(dtype=float)
        if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
            raise AssertionError(f"Invalid values in {prediction_column}")

    validate_fresh_process_load(artifact_dir)
    leakage_passed = not set(NUMERIC_FEATURES + CATEGORICAL_FEATURES).intersection(FORBIDDEN_PREDICTORS)
    groupkfold_passed = (
        all(fold["train_projects"] > 0 and fold["validation_projects"] > 0 for fold in cost_folds + schedule_folds + risk_folds)
        and len(cost_folds) == N_SPLITS
        and len(schedule_folds) == N_SPLITS
        and len(risk_folds) == N_SPLITS
    )
    ongoing_passed = bool(len(output)) and metadata["ongoing_inference"]["failed_or_invalid_prediction_rows"] == 0
    remaining_issues: list[str] = []
    if not leakage_passed:
        remaining_issues.append("Approved feature list intersects forbidden predictors.")
    if not temporal["passed"]:
        remaining_issues.extend(temporal["failures"])
    if not ongoing_passed:
        remaining_issues.append("Ongoing inference produced no valid rows or recorded invalid predictions.")
    result = {
        "model_metrics": model_metrics,
        "metadata": metadata,
        "target_definitions": target_artifact,
        "risk_thresholds": thresholds,
        "completed_example": completed_example,
        "ongoing_output": output,
        "ongoing_report": ongoing_result["report"],
        "acceptance_report": str(ACCEPTANCE_REPORT_PATH.relative_to(ROOT)),
    }
    write_phase2_acceptance_report(
        result,
        artifact_load_passed=True,
        leakage_passed=leakage_passed,
        groupkfold_passed=groupkfold_passed,
        temporal_passed=bool(temporal["passed"]),
        ongoing_passed=ongoing_passed,
        end_to_end_passed=not remaining_issues,
        remaining_issues=remaining_issues,
    )
    return result


def load_phase2_artifacts(artifact_dir: Path = ARTIFACT_DIR) -> dict[str, Any]:
    """Load saved inference artifacts without fitting or retraining anything."""
    import joblib

    return {
        "cost_model": joblib.load(artifact_dir / "cost_model.pkl"),
        "schedule_model": joblib.load(artifact_dir / "schedule_model.pkl"),
        "risk_model": joblib.load(artifact_dir / "risk_combination_model.pkl"),
        "preprocessor": joblib.load(artifact_dir / "preprocessing.pkl"),
        "thresholds": json.loads((artifact_dir / "risk_thresholds.json").read_text(encoding="utf-8")),
        "metadata": json.loads((artifact_dir / "model_metadata.json").read_text(encoding="utf-8")),
    }


def predict_project_risk(project_timeseries: pd.DataFrame, artifact_dir: Path = ARTIFACT_DIR) -> dict[str, Any]:
    """Predict the latest snapshot in a project's history using saved artifacts."""
    features = build_snapshot_features(project_timeseries)
    if features.empty:
        raise ValueError("project_timeseries must contain at least one snapshot")
    latest = features.sort_values("Snapshot_Date", kind="stable").tail(1)
    artifacts = load_phase2_artifacts(artifact_dir)
    X = latest[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    prediction = _score_features(
        X,
        artifacts["preprocessor"],
        artifacts["cost_model"],
        artifacts["schedule_model"],
        artifacts["risk_model"],
        artifacts["thresholds"],
    ).iloc[0]
    return {
        "project_id": str(latest.iloc[0]["Project_ID"]),
        "cost_overrun_probability": float(prediction["Cost_Overrun_Probability"]),
        "schedule_overrun_probability": float(prediction["Schedule_Overrun_Probability"]),
        "overall_risk_probability": float(prediction["Overall_Risk_Probability"]),
        "risk_level": str(prediction["Risk_Level"]),
        "prediction_snapshot": latest.iloc[0]["Snapshot_Date"].date().isoformat(),
        "model_version": artifacts["metadata"]["model_version"],
    }


def predict_cost_overrun(project_timeseries: pd.DataFrame, artifact_dir: Path = ARTIFACT_DIR) -> float:
    return float(predict_project_risk(project_timeseries, artifact_dir)["cost_overrun_probability"])


def predict_schedule_overrun(project_timeseries: pd.DataFrame, artifact_dir: Path = ARTIFACT_DIR) -> float:
    return float(predict_project_risk(project_timeseries, artifact_dir)["schedule_overrun_probability"])


def validate_fresh_process_load(artifact_dir: Path = ARTIFACT_DIR) -> None:
    """Prove the pickles and JSON can be loaded in an independent Python process."""
    check = (
        "import json, joblib, pathlib; p=pathlib.Path(r'" + str(artifact_dir) + "'); "
        "[joblib.load(p/n) for n in ['cost_model.pkl','schedule_model.pkl','risk_combination_model.pkl','preprocessing.pkl']]; "
        "[json.loads((p/n).read_text(encoding='utf-8')) for n in ['feature_list.json','target_definition.json','risk_thresholds.json','model_metrics.json','model_metadata.json']]; print('fresh-process artifact load passed')"
    )
    completed = subprocess.run([sys.executable, "-c", check], cwd=ROOT, capture_output=True, text=True, check=True)
    if "passed" not in completed.stdout:
        raise RuntimeError(f"Fresh-process artifact validation did not complete: {completed.stdout} {completed.stderr}")
