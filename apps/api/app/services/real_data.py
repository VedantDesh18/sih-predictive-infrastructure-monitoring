"""Real data loader for the 100 ongoing PAIMANA infrastructure projects."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import REPOSITORY_ROOT
from app.models.project import Project
from app.models.risk_prediction import RiskPredictionHistory

ONGOING_CSV = REPOSITORY_ROOT / "data" / "processed" / "ongoing_cleaned.csv"
PREDICTIONS_CSV = REPOSITORY_ROOT / "outputs" / "ongoing_risk_predictions.csv"
THRESHOLDS_JSON = REPOSITORY_ROOT / "models" / "paimana_phase2" / "risk_thresholds.json"

SECTOR_MINISTRY_MAP = {
    "ROAD TRANSPORT AND HIGHWAYS": "Ministry of Road Transport and Highways",
    "RAILWAYS": "Ministry of Railways",
    "PETROLEUM": "Ministry of Petroleum and Natural Gas",
    "COAL": "Ministry of Coal",
    "POWER": "Ministry of Power",
    "CIVIL AVIATION": "Ministry of Civil Aviation",
    "MINES": "Ministry of Mines",
}


def _clean_str(val: Any, default: str = "") -> str:
    if val is None or pd.isna(val):
        return default
    return str(val).strip()


def _clean_float(val: Any, default: float = 0.0) -> float:
    if val is None or pd.isna(val):
        return default
    try:
        f = float(val)
        return default if np.isnan(f) or np.isinf(f) else f
    except (ValueError, TypeError):
        return default


def _clean_optional_float(val: Any) -> float | None:
    if val is None or pd.isna(val):
        return None
    try:
        f = float(val)
        return None if np.isnan(f) or np.isinf(f) else f
    except (ValueError, TypeError):
        return None


def _clean_decimal(val: Any, default: str = "0.00") -> Decimal:
    f = _clean_float(val, 0.0)
    return Decimal(f"{f:.2f}")


def _clean_date(val: Any, fallback: date) -> date:
    if val is None or pd.isna(val):
        return fallback
    try:
        ts = pd.to_datetime(val)
        if pd.isna(ts):
            return fallback
        return ts.date()
    except Exception:
        return fallback


async def load_real_portfolio(db: AsyncSession) -> dict[str, int]:
    """Load the 100 real ongoing projects and their full snapshot risk trajectories.

    Replaces any synthetic seed data while keeping original Project_ID as primary key.
    """
    if not ONGOING_CSV.exists():
        raise FileNotFoundError(f"Missing required ongoing dataset: {ONGOING_CSV}")

    # Remove any synthetic demonstration projects
    await db.execute(
        delete(Project).where(
            (Project.is_synthetic == True) | (Project.paimana_project_id.like("SYN-%"))  # noqa: E712
        )
    )

    df_clean = pd.read_csv(ONGOING_CSV, low_memory=False)
    for date_col in ["Snapshot_Date", "Date_of_Approval", "Original_DoC", "Revised_or_Anticipated_DoC"]:
        if date_col in df_clean:
            df_clean[date_col] = pd.to_datetime(df_clean[date_col], errors="coerce")

    df_pred = pd.read_csv(PREDICTIONS_CSV) if PREDICTIONS_CSV.exists() else pd.DataFrame()
    if not df_pred.empty:
        df_pred["Snapshot_Date"] = pd.to_datetime(df_pred["Snapshot_Date"], errors="coerce")
        merged = pd.merge(
            df_clean,
            df_pred[[
                "Project_ID",
                "Snapshot_Date",
                "Cost_Overrun_Probability",
                "Schedule_Overrun_Probability",
                "Overall_Risk_Probability",
                "Risk_Level",
            ]],
            on=["Project_ID", "Snapshot_Date"],
            how="left",
        )
    else:
        merged = df_clean.copy()
        merged["Cost_Overrun_Probability"] = 0.0
        merged["Schedule_Overrun_Probability"] = 0.0
        merged["Overall_Risk_Probability"] = 0.0
        merged["Risk_Level"] = "LOW"

    # Threshold for ML alerts
    high_threshold = 0.647
    if THRESHOLDS_JSON.exists():
        try:
            with open(THRESHOLDS_JSON, encoding="utf-8") as f:
                data = json.load(f)
                high_threshold = data.get("threshold_values", {}).get("high_max_inclusive", 0.647)
        except Exception:
            pass

    # Group by project to build latest project records & full histories
    projects_to_upsert: list[dict[str, Any]] = []
    history_records: list[dict[str, Any]] = []

    for pid, group in merged.groupby("Project_ID"):
        group = group.sort_values("Snapshot_Date")
        latest = group.iloc[-1]
        pid_str = str(pid).strip()

        # Build trajectory for Project.risk_history (last 6 snapshots)
        recent_snaps = group.tail(6)
        risk_history: list[dict[str, Any]] = []
        for _, snap in recent_snaps.iterrows():
            snap_dt = snap["Snapshot_Date"]
            month_label = snap_dt.strftime("%b %y") if pd.notna(snap_dt) else "Unknown"
            prob = _clean_float(snap.get("Overall_Risk_Probability", 0.0))
            # Scale probability 0-1 to 0-100 risk score
            risk_score = max(5, min(98, round(prob * 100)))
            risk_history.append({"month": month_label, "risk": risk_score})

        if not risk_history:
            risk_history = [{"month": "Latest", "risk": 25}]

        # Prepare Project record
        sector_str = _clean_str(latest.get("Sector"), "General Infrastructure")
        ministry_str = SECTOR_MINISTRY_MAP.get(
            sector_str.upper(),
            f"Ministry of {sector_str.title()}",
        )
        agency_str = _clean_str(latest.get("Agency"), "National Implementation Agency")
        proj_name = _clean_str(latest.get("Project_Name"), f"Project {pid_str}")

        snap_date = latest["Snapshot_Date"].date() if pd.notna(latest["Snapshot_Date"]) else date.today()
        p_comp = _clean_date(latest.get("Original_DoC"), snap_date)
        e_comp = _clean_date(latest.get("Revised_or_Anticipated_DoC"), p_comp)

        approved_cost = _clean_decimal(latest.get("Original_Cost_Crore"), "10.00")
        revised_cost = _clean_decimal(latest.get("Revised_or_Anticipated_Cost_Crore"), str(approved_cost))
        expenditure = _clean_decimal(latest.get("Cumulative_Expenditure_Crore"), "0.00")

        cost_overrun_pct = _clean_float(latest.get("Cost_Overrun_Percent"), 0.0)
        time_overrun_mo = _clean_float(latest.get("Time_Overrun_Months"), 0.0)
        delay_mo = _clean_float(latest.get("Delay_Months"), time_overrun_mo)

        if cost_overrun_pct > 20.0 or delay_mo > 12.0:
            condition = "HIGH_RISK"
        elif cost_overrun_pct > 10.0:
            condition = "COST_RISK"
        elif delay_mo > 3.0:
            condition = "SCHEDULE_RISK"
        else:
            condition = "ON_TRACK"

        phys_prog = latest.get("Physical_Progress (%)")
        if pd.isna(phys_prog):
            phys_prog = latest.get("Milestone_Percent")
        if pd.isna(phys_prog):
            # estimate from expenditure ratio if missing
            rev_f = float(revised_cost)
            exp_f = float(expenditure)
            phys_prog = min(95.0, (exp_f / rev_f * 100.0)) if rev_f > 0 else 50.0
        physical_progress = round(_clean_float(phys_prog, 50.0), 1)

        # ML predictions for latest snapshot
        cost_p = _clean_float(latest.get("Cost_Overrun_Probability"), 0.0)
        sched_p = _clean_float(latest.get("Schedule_Overrun_Probability"), 0.0)
        overall_p = _clean_float(latest.get("Overall_Risk_Probability"), 0.0)
        risk_lvl = _clean_str(latest.get("Risk_Level"), "LOW")

        ml_preds = {
            "cost_overrun_probability": round(cost_p, 4),
            "schedule_overrun_probability": round(sched_p, 4),
            "overall_risk_probability": round(overall_p, 4),
            "risk_level": risk_lvl,
            "snapshot_date": snap_date.isoformat(),
        }

        ml_alerts = []
        if cost_p >= high_threshold:
            ml_alerts.append({
                "type": "ML COST OVERRUN WARNING",
                "severity": risk_lvl,
                "reason": f"Phase 2 ML model predicts high likelihood ({cost_p:.1%}) of material cost overrun (>10%).",
                "supporting_metric": f"Predicted probability: {cost_p:.1%}",
            })
        if sched_p >= high_threshold:
            ml_alerts.append({
                "type": "ML SCHEDULE DELAY WARNING",
                "severity": risk_lvl,
                "reason": f"Phase 2 ML model predicts high likelihood ({sched_p:.1%}) of material schedule delay (>3 months).",
                "supporting_metric": f"Predicted probability: {sched_p:.1%}",
            })

        projects_to_upsert.append({
            "id": pid_str,
            "paimana_project_id": pid_str,
            "name": proj_name,
            "description": f"{sector_str} infrastructure project monitored under PAIMANA OCMS.",
            "status": _clean_str(latest.get("Project_Status"), "active"),
            "ministry": ministry_str,
            "sector": sector_str,
            "agency": agency_str,
            "location": "India (National)",
            "approved_cost": approved_cost,
            "revised_cost": revised_cost,
            "expenditure": expenditure,
            "planned_progress": 100.0,
            "physical_progress": physical_progress,
            "planned_completion": p_comp,
            "expected_completion": e_comp,
            "condition": condition,
            "risk_history": risk_history,
            "ml_risk_predictions": ml_preds,
            "ml_alerts": ml_alerts,
            "is_synthetic": False,
        })

        # Historical predictions for each snapshot of this project
        for _, row in group.iterrows():
            row_snap_date = row["Snapshot_Date"].date() if pd.notna(row["Snapshot_Date"]) else snap_date
            c_overrun = row.get("Cost_Overrun_Percent")
            s_delay = row.get("Time_Overrun_Months")
            if pd.isna(s_delay):
                s_delay = row.get("Delay_Months")

            history_records.append({
                "project_id": pid_str,
                "snapshot_date": row_snap_date,
                "model_version": "2.0.0",
                "cost_probability": _clean_float(row.get("Cost_Overrun_Probability")),
                "schedule_probability": _clean_float(row.get("Schedule_Overrun_Probability")),
                "overall_probability": _clean_float(row.get("Overall_Risk_Probability")),
                "risk_level": _clean_str(row.get("Risk_Level"), "LOW"),
                "realized_cost_overrun": _clean_optional_float(c_overrun),
                "realized_schedule_delay": _clean_optional_float(s_delay),
            })

    # Upsert Projects
    for proj_data in projects_to_upsert:
        stmt = insert(Project).values(proj_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={k: v for k, v in proj_data.items() if k != "id"},
        )
        await db.execute(stmt)

    # Upsert RiskPredictionHistory in chunks
    chunk_size = 1000
    for i in range(0, len(history_records), chunk_size):
        chunk = history_records[i : i + chunk_size]
        hist_stmt = insert(RiskPredictionHistory).values(chunk)
        hist_stmt = hist_stmt.on_conflict_do_update(
            index_elements=["project_id", "snapshot_date"],
            set_={
                "model_version": hist_stmt.excluded.model_version,
                "cost_probability": hist_stmt.excluded.cost_probability,
                "schedule_probability": hist_stmt.excluded.schedule_probability,
                "overall_probability": hist_stmt.excluded.overall_probability,
                "risk_level": hist_stmt.excluded.risk_level,
                "realized_cost_overrun": hist_stmt.excluded.realized_cost_overrun,
                "realized_schedule_delay": hist_stmt.excluded.realized_schedule_delay,
            },
        )
        await db.execute(hist_stmt)

    await db.commit()

    return {
        "projects_loaded": len(projects_to_upsert),
        "history_snapshots_loaded": len(history_records),
    }
