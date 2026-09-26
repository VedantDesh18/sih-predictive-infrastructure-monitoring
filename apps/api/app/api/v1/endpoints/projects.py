"""Synthetic portfolio, risk, warning and statistics endpoints for the MVP."""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.models.project import Project
from app.models.risk_prediction import RiskPredictionHistory
from app.services.risk_engine import SYNTHETIC_LABEL, calculate_risk, project_payload

REAL_DATA_LABEL = "PAIMANA Real Ongoing Dataset (100 Projects)"

projects_router = APIRouter(tags=["Predictive Monitoring"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


def _data_label(projects: list[Project]) -> str:
    if not projects or any(p.is_synthetic for p in projects):
        return SYNTHETIC_LABEL
    return REAL_DATA_LABEL


async def _all_projects(db: AsyncSession) -> list[Project]:
    result = await db.scalars(select(Project).order_by(Project.name))
    return list(result)


async def _find_project(project_id: str, db: AsyncSession) -> Project:
    project = await db.scalar(
        select(Project).where(
            (Project.paimana_project_id == project_id) | (Project.id == project_id)
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@projects_router.get("/projects")
async def list_projects(
    db: DatabaseSession,
    ministry: str | None = None,
    sector: str | None = None,
    risk_level: str | None = Query(
        default=None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$"
    ),
    trend: str | None = Query(
        default=None, pattern="^(STABLE|IMPROVING|WORSENING|RAPIDLY WORSENING)$"
    ),
) -> dict[str, Any]:
    projects = await _all_projects(db)
    rows = [project_payload(project) for project in projects]
    if ministry:
        rows = [row for row in rows if row["ministry"] == ministry]
    if sector:
        rows = [row for row in rows if row["sector"] == sector]
    if risk_level:
        rows = [
            row for row in rows if row["risk"]["scores"]["risk_level"] == risk_level
        ]
    if trend:
        rows = [row for row in rows if row["risk"]["trajectory"]["trend"] == trend]
    rows.sort(key=lambda row: row["risk"]["scores"]["overall_risk"], reverse=True)
    return {"data_source": _data_label(projects), "total": len(rows), "projects": rows}


@projects_router.get("/projects/{project_id}")
async def get_project(project_id: str, db: DatabaseSession) -> dict[str, Any]:
    return project_payload(await _find_project(project_id, db))


@projects_router.get("/projects/{project_id}/risk")
async def get_project_risk(project_id: str, db: DatabaseSession) -> dict[str, Any]:
    project = await _find_project(project_id, db)
    risk = calculate_risk(project)
    res = {
        "project_id": project.paimana_project_id,
        "project_name": project.name,
        "data_source": _data_label([project]),
        **risk,
    }
    if project.ml_risk_predictions:
        res["ml_risk"] = project.ml_risk_predictions
    return res


@projects_router.get("/projects/{project_id}/alerts")
async def get_project_alerts(project_id: str, db: DatabaseSession) -> dict[str, Any]:
    project = await _find_project(project_id, db)
    res = {
        "project_id": project.paimana_project_id,
        "project_name": project.name,
        "data_source": _data_label([project]),
        "alerts": calculate_risk(project)["alerts"],
    }
    if project.ml_alerts:
        res["ml_alerts"] = project.ml_alerts
    return res


@projects_router.get("/projects/{project_id}/trajectory")
async def get_project_trajectory(
    project_id: str, db: DatabaseSession
) -> dict[str, Any]:
    project = await _find_project(project_id, db)
    history_rows = await db.scalars(
        select(RiskPredictionHistory)
        .where(RiskPredictionHistory.project_id == project.paimana_project_id)
        .order_by(RiskPredictionHistory.snapshot_date.asc())
    )
    records = list(history_rows)
    return {
        "project_id": project.paimana_project_id,
        "project_name": project.name,
        "sector": project.sector,
        "agency": project.agency,
        "data_source": _data_label([project]),
        "total_snapshots": len(records),
        "trajectory": [
            {
                "snapshot_date": r.snapshot_date.isoformat(),
                "model_version": r.model_version,
                "cost_probability": round(r.cost_probability, 4),
                "schedule_probability": round(r.schedule_probability, 4),
                "overall_probability": round(r.overall_probability, 4),
                "risk_level": r.risk_level,
                "realized_cost_overrun": r.realized_cost_overrun,
                "realized_schedule_delay": r.realized_schedule_delay,
            }
            for r in records
        ],
    }


@projects_router.get("/risk/portfolio")
async def portfolio_risk(db: DatabaseSession) -> dict[str, Any]:
    projects = await _all_projects(db)
    enriched = [(project, calculate_risk(project)) for project in projects]
    distribution: dict[str, int] = {
        key: 0 for key in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    }
    ml_distribution: dict[str, int] = {
        key: 0 for key in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    }
    cost_buckets: dict[str, int] = {
        "on-budget": 0,
        "0-10%": 0,
        "10-20%": 0,
        "20-50%": 0,
        ">50%": 0,
    }
    ministry_scores: dict[str, list[int]] = defaultdict(list)
    sector_scores: dict[str, list[int]] = defaultdict(list)
    trajectory_points: dict[str, list[int]] = defaultdict(list)
    for project, risk in enriched:
        score = risk["scores"]["overall_risk"]
        distribution[risk["scores"]["risk_level"]] += 1
        if project.ml_risk_predictions:
            ml_lvl = str(project.ml_risk_predictions.get("risk_level", "LOW")).upper()
            if ml_lvl in ml_distribution:
                ml_distribution[ml_lvl] += 1
        app_cost = float(project.approved_cost)
        rev_cost = float(project.revised_cost)
        growth = ((rev_cost - app_cost) / app_cost * 100) if app_cost > 0 else 0
        if growth <= 0:
            cost_buckets["on-budget"] += 1
        elif growth <= 10:
            cost_buckets["0-10%"] += 1
        elif growth <= 20:
            cost_buckets["10-20%"] += 1
        elif growth <= 50:
            cost_buckets["20-50%"] += 1
        else:
            cost_buckets[">50%"] += 1

        ministry_scores[project.ministry].append(score)
        sector_scores[project.sector].append(score)
        for point in risk["trajectory"]["history"]:
            trajectory_points[str(point["month"])].append(int(point["risk"]))

    def to_average(source: dict[str, list[int]]) -> list[dict[str, int | str]]:
        return [
            {"name": name, "risk": round(sum(values) / len(values))}
            for name, values in sorted(
                source.items(),
                key=lambda item: sum(item[1]) / len(item[1]),
                reverse=True,
            )
        ]

    return {
        "data_source": _data_label(projects),
        "risk_distribution": [
            {"level": level, "count": count} for level, count in distribution.items()
        ],
        "ml_risk_distribution": [
            {"level": level, "count": count} for level, count in ml_distribution.items()
        ],
        "cost_risk_buckets": [
            {"bucket": bucket, "count": count} for bucket, count in cost_buckets.items()
        ],
        "portfolio_trend": [
            {"month": month, "risk": round(sum(values) / len(values))}
            for month, values in trajectory_points.items()
        ],
        "ministry_comparison": to_average(ministry_scores),
        "sector_comparison": to_average(sector_scores),
        "top_risky_projects": [
            {
                "project_id": project.paimana_project_id,
                "project_name": project.name,
                "overall_risk": risk["scores"]["overall_risk"],
                "risk_level": risk["scores"]["risk_level"],
                "trend": risk["trajectory"]["trend"],
            }
            for project, risk in sorted(
                enriched,
                key=lambda item: item[1]["scores"]["overall_risk"],
                reverse=True,
            )[:10]
        ],
    }


@projects_router.get("/statistics")
async def statistics(db: DatabaseSession) -> dict[str, Any]:
    projects = await _all_projects(db)
    enriched = [(project, calculate_risk(project)) for project in projects]
    total_approved = sum(float(project.approved_cost) for project, _ in enriched)
    total_revised = sum(float(project.revised_cost) for project, _ in enriched)
    potential_exposure = sum(
        max(float(project.revised_cost) - float(project.approved_cost), 0)
        for project, _ in enriched
    )
    return {
        "data_source": _data_label(projects),
        "total_projects": len(enriched),
        "high_risk_projects": sum(
            risk["scores"]["risk_level"] == "HIGH" for _, risk in enriched
        ),
        "critical_projects": sum(
            risk["scores"]["risk_level"] == "CRITICAL" for _, risk in enriched
        ),
        "rising_risk_projects": sum(
            risk["trajectory"]["trend"] in {"WORSENING", "RAPIDLY WORSENING"}
            for _, risk in enriched
        ),
        "total_approved_cost": round(total_approved, 2),
        "total_revised_cost": round(total_revised, 2),
        "potential_cost_exposure": round(potential_exposure, 2),
    }
