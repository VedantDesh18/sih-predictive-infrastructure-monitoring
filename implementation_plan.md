# AI-Powered Predictive Infrastructure Monitoring — Project Foundation

Set up the monorepo structure, containerized services, and basic health endpoints for the SIH prototype.

## Proposed Changes

### Monorepo Structure

```
d:\SIH project\
├── apps/
│   ├── web/          # Next.js + TypeScript + Tailwind + shadcn/ui
│   └── api/          # FastAPI + SQLAlchemy + Pydantic
├── ml/               # (empty placeholder for future ML work)
├── pipelines/        # (empty placeholder)
├── data/             # (empty placeholder)
├── tests/
│   ├── api/          # pytest tests for FastAPI
│   └── web/          # Jest/Vitest tests for Next.js
├── docs/             # README content, architecture docs
├── infrastructure/   # Docker-related configs
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

### 1. Next.js Frontend (`apps/web`)

- Initialize with `npx create-next-app@latest` (TypeScript, Tailwind CSS, App Router, ESLint)
- Add a basic landing page with a health status indicator
- Add an API health-check route (`/api/health`) that proxies to the backend
- Configure environment variable `NEXT_PUBLIC_API_URL` pointing to FastAPI
- Dockerfile for production build (multi-stage: build → standalone)

---

### 2. FastAPI Backend (`apps/api`)

#### [NEW] `apps/api/app/main.py`
- FastAPI app with CORS middleware
- `/health` endpoint returning `{"status": "healthy", "database": "connected|error"}`
- `/api/v1/health` versioned endpoint

#### [NEW] `apps/api/app/core/config.py`
- Pydantic `Settings` class loading from environment variables
- `DATABASE_URL`, `API_HOST`, `API_PORT`, `CORS_ORIGINS`, etc.

#### [NEW] `apps/api/app/core/database.py`
- SQLAlchemy async engine + session factory
- `get_db` dependency for FastAPI
- Connection test utility

#### [NEW] `apps/api/app/models/__init__.py`
- SQLAlchemy Base model (placeholder for future models)

#### [NEW] `apps/api/requirements.txt`
- fastapi, uvicorn, sqlalchemy, asyncpg, psycopg2-binary, pydantic-settings, python-dotenv, alembic, pytest, httpx

#### [NEW] `apps/api/Dockerfile`
- Python 3.11 slim image, install deps, run uvicorn

---

### 3. PostgreSQL

- Use official `postgres:16-alpine` image in Docker Compose
- Persistent volume for data
- Health check with `pg_isready`
- Default database: `sih_monitor`

---

### 4. Docker Compose (`docker-compose.yml`)

Three services:
| Service | Image | Port | Depends On |
|---------|-------|------|------------|
| `web` | Build `apps/web` | 3000 | `api` |
| `api` | Build `apps/api` | 8000 | `db` |
| `db` | postgres:16-alpine | 5432 | — |

- Shared `.env` file
- Named volume `postgres_data`
- Health checks on all services
- Network: `sih-network`

---

### 5. Environment Configuration

#### [NEW] `.env.example`
```
# PostgreSQL
POSTGRES_USER=sih_user
POSTGRES_PASSWORD=sih_password
POSTGRES_DB=sih_monitor
POSTGRES_HOST=db
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://sih_user:sih_password@db:5432/sih_monitor

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

### 6. Testing Structure

#### `tests/api/`
- `test_health.py` — test `/health` endpoint returns 200 and expected schema
- `conftest.py` — pytest fixtures with TestClient

#### `tests/web/`
- Placeholder test file for future frontend tests

---

### 7. Documentation

#### [NEW] `README.md`
- Project overview, architecture diagram (mermaid), quick start with `docker compose up`, environment setup, testing instructions

---

### 8. Placeholder Directories

Create `.gitkeep` in:
- `ml/`
- `pipelines/`
- `data/`
- `docs/`

---

## Verification Plan

### Automated Tests
1. `docker compose up --build` — all 3 services start
2. `curl http://localhost:8000/health` — returns `{"status":"healthy","database":"connected"}`
3. `curl http://localhost:3000` — returns Next.js page
4. `cd apps/api && pytest` — API tests pass

### Manual Verification
- Visit `http://localhost:3000` in browser
- Visit `http://localhost:8000/docs` for Swagger UI
- Check PostgreSQL connectivity via health endpoint
