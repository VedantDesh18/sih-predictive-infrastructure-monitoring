# Data Architecture

## Overview

The system processes infrastructure project data from PAIMANA/OCMS sources,
transforms it into ML-ready features, and stores predictions alongside source data.

## Data Flow

```
PAIMANA/OCMS Data Source
        │
        ▼
┌─────────────────┐
│   Ingestion     │  pipelines/ingestion/
│   Pipeline      │  - Validate incoming data
│                 │  - Map to internal schema
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Raw Storage    │  data/raw/
│                 │  - Parquet format
│                 │  - Immutable source of truth
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Transformation  │  pipelines/transformation/
│   Pipeline      │  - Clean, normalize
│                 │  - Compute derived fields
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Processed     │  data/processed/
│   Storage       │  - Cleaned data
│                 │  - Parquet format
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Feature      │  ml/features/
│  Engineering    │  - Cost features
│                 │  - Schedule features
│                 │  - Risk features
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Feature Store  │  data/features/
│                 │  - ML-ready features
│                 │  - Versioned
└────────┬────────┘
         │
    ┌────┴─────┐
    ▼          ▼
┌────────┐ ┌──────────┐
│Training│ │Inference │
│Pipeline│ │Pipeline  │
└────────┘ └──────────┘
```

## Storage Strategy

| Layer | Format | Location | Purpose |
|-------|--------|----------|---------|
| Raw | Parquet | `data/raw/` | Immutable source data from PAIMANA |
| Processed | Parquet | `data/processed/` | Cleaned and transformed data |
| Features | Parquet | `data/features/` | ML-ready feature sets |
| Samples | CSV/Parquet | `data/samples/` | Sample datasets for development |
| Operational | PostgreSQL | `sih_monitor` DB | Project metadata, predictions, alerts |

## PAIMANA Integration Points

The system does **not** replace PAIMANA. It consumes PAIMANA-compatible data:

1. **Project metadata**: Project ID, name, dates, budget, status
2. **Progress reports**: Milestone completion, physical progress
3. **Financial data**: Expenditure, budget revisions, payment records
4. **Timeline data**: Planned vs actual dates, schedule changes

Each project is linked via `paimana_project_id` (unique identifier from PAIMANA/OCMS).

## Database Schema (Phase 1)

### `projects` table
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, auto-generated |
| name | VARCHAR(255) | NOT NULL |
| description | TEXT | NULLABLE |
| paimana_project_id | VARCHAR(100) | UNIQUE, INDEXED |
| status | VARCHAR(50) | DEFAULT 'active', INDEXED |
| created_at | TIMESTAMPTZ | DEFAULT now() |
| updated_at | TIMESTAMPTZ | DEFAULT now() |

Future phases will add tables for: risk_scores, predictions, early_warnings, features.

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Data Processing | Polars | Fast DataFrame operations |
| Analytical Queries | DuckDB | In-process OLAP |
| Storage Format | Parquet | Columnar, compressed, fast reads |
| Operational DB | PostgreSQL | ACID, JSON support, async drivers |
