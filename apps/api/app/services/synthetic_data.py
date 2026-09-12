"""Deterministic, clearly labelled demonstration portfolio for the SIH MVP."""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project

MINISTRIES = [
    (
        "Ministry of Road Transport & Highways",
        "Roads & Highways",
        "National Highways Authority of India",
    ),
    ("Ministry of Railways", "Railways", "Rail Vikas Nigam Limited"),
    ("Ministry of Jal Shakti", "Water Resources", "National Water Development Agency"),
    ("Ministry of Power", "Power", "National Thermal Power Corporation"),
    (
        "Ministry of Housing & Urban Affairs",
        "Urban Development",
        "National Capital Region Planning Board",
    ),
    (
        "Ministry of Ports, Shipping and Waterways",
        "Ports & Shipping",
        "Sagarmala Development Company",
    ),
]

LOCATIONS = [
    "Maharashtra",
    "Uttar Pradesh",
    "Tamil Nadu",
    "Gujarat",
    "Karnataka",
    "Rajasthan",
    "Madhya Pradesh",
    "Odisha",
    "Assam",
    "Bihar",
]

PROJECT_WORDS = [
    "Economic Corridor",
    "Metro Extension",
    "Irrigation Modernisation",
    "Transmission Upgrade",
    "Integrated Freight Terminal",
    "River Link",
    "Smart Water Grid",
    "Logistics Hub",
    "Coastal Connectivity Programme",
    "Regional Mobility Link",
]

CONDITIONS = ["ON_TRACK", "COST_RISK", "SCHEDULE_RISK", "HIGH_RISK", "RECOVERY"]


def _history(
    condition: str, final_score: int, rng: random.Random
) -> list[dict[str, object]]:
    if condition == "HIGH_RISK":
        values = [
            final_score - 34,
            final_score - 25,
            final_score - 16,
            final_score - 8,
            final_score,
        ]
    elif condition == "SCHEDULE_RISK":
        values = [
            final_score - 18,
            final_score - 14,
            final_score - 9,
            final_score - 4,
            final_score,
        ]
    elif condition == "COST_RISK":
        values = [
            final_score - 15,
            final_score - 11,
            final_score - 7,
            final_score - 3,
            final_score,
        ]
    elif condition == "RECOVERY":
        values = [
            final_score + 25,
            final_score + 19,
            final_score + 12,
            final_score + 5,
            final_score,
        ]
    else:
        values = [
            final_score - 2,
            final_score - 1,
            final_score,
            final_score - 1,
            final_score,
        ]
    start = date(2026, 3, 1)
    return [
        {
            "month": (start + timedelta(days=31 * index)).strftime("%b"),
            "risk": max(5, min(98, value)),
        }
        for index, value in enumerate(values)
    ]


def _project(index: int, rng: random.Random) -> Project:
    ministry, sector, agency = MINISTRIES[index % len(MINISTRIES)]
    condition = CONDITIONS[index % len(CONDITIONS)]
    approved = rng.randrange(850, 18000) * 10
    planned_progress = rng.randint(55, 88)
    planned_completion = date(2026, 7, 1) + timedelta(days=rng.randint(-240, 240))
    if condition == "ON_TRACK":
        growth, gap, delay, expense_gap, final = (
            rng.uniform(1, 6),
            rng.uniform(-2, 5),
            rng.randint(0, 35),
            rng.uniform(0, 8),
            rng.randint(18, 42),
        )
    elif condition == "COST_RISK":
        growth, gap, delay, expense_gap, final = (
            rng.uniform(12, 24),
            rng.uniform(2, 11),
            rng.randint(20, 95),
            rng.uniform(14, 28),
            rng.randint(50, 72),
        )
    elif condition == "SCHEDULE_RISK":
        growth, gap, delay, expense_gap, final = (
            rng.uniform(3, 10),
            rng.uniform(13, 25),
            rng.randint(145, 300),
            rng.uniform(8, 20),
            rng.randint(58, 80),
        )
    elif condition == "HIGH_RISK":
        growth, gap, delay, expense_gap, final = (
            rng.uniform(15, 29),
            rng.uniform(20, 34),
            rng.randint(220, 430),
            rng.uniform(18, 34),
            rng.randint(80, 94),
        )
    else:
        growth, gap, delay, expense_gap, final = (
            rng.uniform(7, 15),
            rng.uniform(5, 14),
            rng.randint(45, 150),
            rng.uniform(6, 17),
            rng.randint(39, 61),
        )
    revised = approved * (1 + growth / 100)
    physical = max(20, min(96, planned_progress - gap))
    expenditure_ratio = min(94, physical + expense_gap)
    expenditure = revised * expenditure_ratio / 100
    return Project(
        name=f"{LOCATIONS[index % len(LOCATIONS)]} {PROJECT_WORDS[index % len(PROJECT_WORDS)]} {index + 1:02d}",
        description="Synthetic demonstration project generated for the SIH MVP.",
        paimana_project_id=f"SYN-{index + 1:03d}",
        status="active",
        ministry=ministry,
        sector=sector,
        agency=agency,
        location=LOCATIONS[index % len(LOCATIONS)],
        approved_cost=Decimal(str(round(approved, 2))),
        revised_cost=Decimal(str(round(revised, 2))),
        expenditure=Decimal(str(round(expenditure, 2))),
        planned_progress=round(planned_progress, 1),
        physical_progress=round(physical, 1),
        planned_completion=planned_completion,
        expected_completion=planned_completion + timedelta(days=delay),
        condition=condition,
        risk_history=_history(condition, final, rng),
        is_synthetic=True,
    )


def demo_project() -> Project:
    """The primary judge-flow project; all values feed the transparent engine."""
    return Project(
        name="Demo National Transport Corridor",
        description="Synthetic demonstration of a healthy project progressing into rapid risk escalation.",
        paimana_project_id="SYN-DEMO-001",
        status="active",
        ministry="Ministry of Road Transport & Highways",
        sector="Roads & Highways",
        agency="National Highways Authority of India",
        location="Maharashtra–Karnataka Corridor",
        approved_cost=Decimal("28500.00"),
        revised_cost=Decimal("33117.00"),
        expenditure=Decimal("25500.00"),
        planned_progress=80.0,
        physical_progress=52.6,
        planned_completion=date(2025, 12, 31),
        expected_completion=date(2026, 8, 2),
        condition="HIGH_RISK",
        risk_history=[
            {"month": "Mar", "risk": 42},
            {"month": "Apr", "risk": 51},
            {"month": "May", "risk": 63},
            {"month": "Jun", "risk": 74},
            {"month": "Jul", "risk": 84},
        ],
        is_synthetic=True,
    )


async def seed_synthetic_projects(db: AsyncSession) -> None:
    """Seed exactly 150 records once; never overwrite a subsequently loaded portfolio."""
    existing = await db.scalar(select(func.count()).select_from(Project))
    if existing:
        return
    rng = random.Random(20260826)
    db.add(demo_project())
    db.add_all(_project(index, rng) for index in range(149))
    await db.commit()
