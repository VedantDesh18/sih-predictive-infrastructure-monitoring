# AI-Powered Predictive Infrastructure Monitoring & Early Warning System

This is a compact, working SIH MVP for PAIMANA/OCMS-compatible infrastructure
monitoring. It is a decision-support layer, not a replacement for PAIMANA.

The shipped portfolio is **Synthetic Demonstration Data**: 150 fictional
infrastructure projects generated deterministically for a safe demo. The risk
engine is transparent, calculation-based prototype logic; it makes no trained
ML or accuracy claim.

## Architecture

```
Next.js web (3000)  →  FastAPI API (8000)  →  PostgreSQL 16
```

- `apps/web` — Next.js 16, TypeScript, Tailwind CSS
- `apps/api` — FastAPI, async SQLAlchemy, asyncpg, Alembic
- `apps/api/app/services/synthetic_data.py` — deterministic 150-project demo portfolio
- `apps/api/app/services/risk_engine.py` — modular predictive-risk prototype

The frontend calls its same-origin `/api/health` route. In Docker, that route
uses the internal `api` hostname; the browser never connects directly to the
database or container-only API address.

## Prerequisites

- Node.js 22 LTS or newer (`node --version`)
- Python 3.11 or newer
- PostgreSQL 16 for native local development, or Docker Desktop for Compose

The frontend Docker image uses Node 22. The `package.json` engine floor is also
Node 22, which is compatible with the installed Next.js version.

## Configuration

Create one repository-root `.env` file:

```powershell
Copy-Item .env.example .env
```

The same `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` values are used
for both native local development and Docker. `DATABASE_URL` is the native local
connection URL (`localhost`). Docker Compose derives an internal `db` hostname
connection URL from the same values, avoiding conflicting `.env` files.

`POSTGRES_ADMIN_URL` is used only by `setup_db.py`, which initializes a native
local PostgreSQL instance. Set it to a valid local PostgreSQL administrator URL
before using that script. Do not commit real credentials.

## Native local development

1. Install API and frontend dependencies:

   ```powershell
   python -m venv venv
   .\venv\Scripts\python.exe -m pip install -r apps\api\requirements.txt
   Push-Location apps\web
   npm ci
   Pop-Location
   ```

2. Initialize the configured local database and apply the MVP migration:

   ```powershell
   .\venv\Scripts\python.exe setup_db.py
   Push-Location apps\api
   ..\..\venv\Scripts\python.exe -m alembic upgrade head
   Pop-Location
   ```

   On its first startup, the API seeds the 150-record synthetic portfolio.

3. Start both services from the repository root:

   ```powershell
   .\start_project.ps1
   ```

   The script runs FastAPI with `--reload` for local development and starts the
   Next.js development server. It is safe to launch from any working directory.

To start the services manually, use two terminals from the repository root:

```powershell
$env:PYTHONPATH = "$PWD\apps\api"
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

```powershell
Push-Location apps\web
npm run dev
```

## Docker Compose

Docker Compose runs the production-style containers: the API applies Alembic
migrations and starts Uvicorn **without** `--reload`.

```powershell
docker compose up --build
```

The Compose services are `web`, `api`, and `db`. PostgreSQL is exposed on host
port `5433` by default (`POSTGRES_HOST_PORT`) so native PostgreSQL on `5432` does
not conflict with the Docker database. Inside Compose, the API always connects to
`db:5432`.

For a completely clean Docker database, use the following command. It deletes
the named Docker PostgreSQL volume:

```powershell
docker compose down -v
docker compose up --build
```

## Health endpoints

| Endpoint | Expected behavior |
| --- | --- |
| `GET /health/live` | HTTP 200 whenever the FastAPI process is running; does not query PostgreSQL. |
| `GET /health/ready` | HTTP 200 only when PostgreSQL is available; HTTP 503 with safe dependency status otherwise. |
| `GET /api/v1/health` | Versioned application health response; HTTP 503 when PostgreSQL is unavailable. |
| `GET /docs` | Swagger UI. |

## MVP monitoring API

All responses are sourced from PostgreSQL and labelled as synthetic where
applicable.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/projects` | Sortable/filterable project risk register (`ministry`, `sector`, `risk_level`, `trend`) |
| `GET /api/v1/projects/{id}` | Project details, metrics, risk, drivers and alerts |
| `GET /api/v1/projects/{id}/risk` | Risk-engine features, scores and trajectory |
| `GET /api/v1/projects/{id}/alerts` | Early-warning list |
| `GET /api/v1/risk/portfolio` | Charts and the top intervention queue |
| `GET /api/v1/statistics` | Portfolio KPI cards |

The primary demo endpoint is `GET /api/v1/projects/SYN-DEMO-001`. It returns
**Demo National Transport Corridor** with risk **84/100**, components **87 / 81 /
73**, the trajectory `42 → 51 → 63 → 74 → 84`, calculated drivers, and a HIGH
rapid-risk-escalation warning.

Example verification commands:

```powershell
Invoke-WebRequest http://localhost:8000/health/live
Invoke-WebRequest http://localhost:8000/health/ready
Invoke-WebRequest http://localhost:8000/api/v1/health
Invoke-WebRequest http://localhost:3000/api/health
```

## Testing and quality checks

Run all API commands from `apps/api` so Alembic and Python imports resolve
consistently. Settings still locate the repository-root `.env`.

```powershell
Push-Location apps\api
..\..\venv\Scripts\python.exe -m pytest ..\..\tests\unit -v
..\..\venv\Scripts\python.exe -m pytest ..\..\tests\integration -m integration -v
..\..\venv\Scripts\python.exe -m ruff check app
..\..\venv\Scripts\python.exe -m black --check app
Pop-Location
```

Unit tests replace database access and cover API contracts. Integration tests use
the configured `DATABASE_URL` and verify the configured database, user, and a
basic query against PostgreSQL. Initialize the local database first.

Frontend checks:

```powershell
Push-Location apps\web
npm run lint
npm run format:check
npm run build
Pop-Location
```

## Database migrations

Alembic manages all schema changes. The initial `projects` table is the only
current schema; do not add Phase 2 tables yet.

```powershell
Push-Location apps\api
..\..\venv\Scripts\python.exe -m alembic history
..\..\venv\Scripts\python.exe -m alembic upgrade head
..\..\venv\Scripts\python.exe -m alembic revision --autogenerate -m "description"
Pop-Location
```

## Final demo commands

From the repository root, use these commands for the native final prototype:

```powershell
Push-Location apps\api
..\..\venv\Scripts\python.exe -m alembic upgrade head
Pop-Location
.\start_project.ps1
```

Open [http://localhost:3000](http://localhost:3000), then select **Open primary
demo project**. For the API documentation, open
[http://localhost:8000/docs](http://localhost:8000/docs).

## Scope boundary

The UI deliberately describes this as **Predictive Risk Engine — prototype**.
The `risk_engine.py` output contract is the replacement boundary for a future
validated XGBoost, LightGBM, or statistical model.

## PAIMANA Phase 2 (snapshot models)

Phase 2 trains leakage-safe cost and schedule models from
`data/processed/completed_cleaned.csv` and scores
`data/processed/ongoing_cleaned.csv` without retraining. Commands, feature
definitions, and artifact paths are documented in `modeling/README.md`.

```powershell
.\venv\Scripts\python.exe -m pip install -r ml\requirements-phase2.txt
.\venv\Scripts\python.exe pipelines\training\train_phase2.py
```
