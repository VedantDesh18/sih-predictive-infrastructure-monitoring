"""Synthetic portfolio, risk, warning and statistics endpoints for the MVP."""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.models.project import Project
from app.services.risk_engine import SYNTHETIC_LABEL, calculate_risk, project_payload

projects_router = APIRouter(tags=["Predictive Monitoring"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


async def _all_projects(db: AsyncSession) -> list[Project]:
    result = await db.scalars(select(Project).order_by(Project.name))
    return list(result)


async def _find_project(project_id: str, db: AsyncSession) -> Project:
    project = await db.scalar(
        select(Project).where(Project.paimana_project_id == project_id)
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
    projects = _all_projects(db)
    rows = [project_payload(project) for project in await projects]
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
    return {"data_source": SYNTHETIC_LABEL, "total": len(rows), "projects": rows}


@projects_router.get("/projects/{project_id}")
async def get_project(project_id: str, db: DatabaseSession) -> dict[str, Any]:
    return project_payload(await _find_project(project_id, db))


@projects_router.get("/projects/{project_id}/risk")
async def get_project_risk(project_id: str, db: DatabaseSession) -> dict[str, Any]:
    project = await _find_project(project_id, db)
    risk = calculate_risk(project)
    return {
        "project_id": project.paimana_project_id,
        "project_name": project.name,
        "data_source": SYNTHETIC_LABEL,
        **risk,
    }


@projects_router.get("/projects/{project_id}/alerts")
async def get_project_alerts(project_id: str, db: DatabaseSession) -> dict[str, Any]:
    project = await _find_project(project_id, db)
    return {
        "project_id": project.paimana_project_id,
        "project_name": project.name,
        "data_source": SYNTHETIC_LABEL,
        "alerts": calculate_risk(project)["alerts"],
    }


@projects_router.get("/risk/portfolio")
async def portfolio_risk(db: DatabaseSession) -> dict[str, Any]:
    projects = await _all_projects(db)
    enriched = [(project, calculate_risk(project)) for project in projects]
    distribution: dict[str, int] = {
        key: 0 for key in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    }
    ministry_scores: dict[str, list[int]] = defaultdict(list)
    sector_scores: dict[str, list[int]] = defaultdict(list)
    trajectory_points: dict[str, list[int]] = defaultdict(list)
    for project, risk in enriched:
        score = risk["scores"]["overall_risk"]
        distribution[risk["scores"]["risk_level"]] += 1
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
        "data_source": SYNTHETIC_LABEL,
        "risk_distribution": [
            {"level": level, "count": count} for level, count in distribution.items()
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
        "data_source": SYNTHETIC_LABEL,
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
