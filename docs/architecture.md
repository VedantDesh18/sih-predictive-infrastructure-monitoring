# System Architecture

## Overview

The AI-Powered Predictive Infrastructure Monitoring system is a decision-support layer
that consumes PAIMANA/OCMS-compatible data to predict cost overruns, schedule delays,
and implementation risks for infrastructure projects.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                       │
│                     TypeScript + Tailwind CSS                   │
│                          Port: 3000                             │
└──────────────────────────────┬──────────────────────────────────┘
                               │ REST API
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│                   Python 3.11 + async                           │
│                          Port: 8000                             │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐ │
│  │ API v1   │  │ Services │  │ Models   │  │ Schemas        │ │
│  │ Endpoints│  │ (Logic)  │  │ (ORM)    │  │ (Validation)   │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘ │
└──────────────────────────────┬──────────────────────────────────┘
                               │ SQLAlchemy async + asyncpg
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL 16                                 │
│                       Port: 5432                                │
│                    Database: sih_monitor                         │
└─────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Frontend (`apps/web`)
- User interface for monitoring dashboards (future phases)
- Calls backend REST API for data
- No direct database access

### Backend (`apps/api`)
- REST API with versioned endpoints (`/api/v1/`)
- Health probes for infrastructure monitoring
- Database access via async SQLAlchemy
- Schema migrations via Alembic
- Standard response/error envelopes

### Database
- PostgreSQL 16 with UUID support
- Schema managed exclusively through Alembic migrations
- Async access via asyncpg driver

### ML Pipeline (future)
- Feature engineering (`ml/features/`)
- Predictive models (`ml/models/{cost,schedule,risk}/`)
- Model evaluation (`ml/evaluation/`)
- Explainability via SHAP (`ml/explainability/`)

### Data Pipeline (future)
- Ingestion from PAIMANA/OCMS (`pipelines/ingestion/`)
- Transformation (`pipelines/transformation/`)
- Training pipelines (`pipelines/training/`)
- Inference pipelines (`pipelines/inference/`)

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| API Framework | FastAPI | Async-native, auto-docs, Pydantic integration |
| ORM | SQLAlchemy 2.0 async | Type-safe, async support, Alembic integration |
| DB Driver | asyncpg | Best async PostgreSQL performance |
| Frontend | Next.js + TypeScript | SSR, routing, type safety |
| Migrations | Alembic | SQLAlchemy-native, async-aware |
| Containerization | Docker Compose | Simple local development |
