# Core ETL + User API

FastAPI service (port 8001) that bootstraps FitAI's Postgres schema with seed data and exposes authentication/user profile endpoints consumed by the frontend, calendar agent, and RAG service. Dependencies are defined in `pyproject.toml` and installed with `uv` (no `requirements.txt`).

## What this service does
- **ETL bootstrap**: loads three CSVs from GCS (`gym_recommendation`, `gym_members_exercise_tracking`, `exercise_catalog`) into Postgres and seeds demo users so downstream services have data to work with.
- **User & auth API**: register/login with JWTs, fetch/update the current user, and admin-style CRUD by user id.
- **Health check**: `/health` returns `{ "status": "ok", "service": "core-etl-api" }`.

## Prerequisites
- Postgres reachable with the same schema as `services/db/init.sql`.
- Google service account key with read access to `gs://fitai-data-bucket` (project `rich-access-471117-r0`).
- Environment variables (defaults shown):
  - `POSTGRES_USER=fitai`
  - `POSTGRES_PASSWORD=fitai`
  - `POSTGRES_DB=fitai_app`
  - `POSTGRES_HOST=db`
  - `POSTGRES_PORT=5432`
  - `GOOGLE_APPLICATION_CREDENTIALS=/secrets/rich-access-471117-r0-f17d92fbf298.json`
  - `JWT_SECRET=change-me-in-prod`
  - `JWT_EXPIRE_MINUTES=120`

## Run with Docker Compose (recommended)
From the repo root:
```bash
docker compose up -d core-etl-api
# or start the whole stack
docker compose up -d
```

The container entrypoint runs the ETL once before uvicorn starts. Logs:
```bash
docker compose logs -f core-etl-api
```

## Run locally without Docker (uv)
```bash
cd services/core-etl-api
pip install --upgrade uv            # once, if you don't have uv installed
uv sync                              # installs deps into .venv (Python 3.12+)
export POSTGRES_HOST=localhost       # adjust if needed
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
uv run uvicorn app:app --reload --host 0.0.0.0 --port 8001
# optional: run ETL once manually
uv run python etl.py
```

## ETL flow
The ETL waits for Postgres, then:
1) Downloads CSVs from `gs://fitai-data-bucket/raw-data/`.
2) Cleans/renames columns (lowercase + underscores; maps dataset ids to `source_id`).
3) Appends into Postgres tables (`gym_recommendation`, `exercise_tracking`, `exercise_catalog`).
4) Seeds demo users with password `88888888` (idempotent via `ON CONFLICT DO NOTHING`).

To trigger manually while the service is running:
```bash
curl -X POST http://localhost:8001/run-etl
```

## API surface
| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/health` | none | Liveness check |
| POST | `/auth/register` | none | Create user + return JWT |
| POST | `/auth/login` | none | Validate credentials, return JWT |
| GET | `/users/me` | Bearer | Fetch current user from JWT |
| PUT | `/users/me` | Bearer | Update current user |
| POST | `/users` | none | Create user (no auth guard; mainly for internal seeding/tests) |
| GET | `/users/{user_id}` | none | Fetch user by id |
| PUT | `/users/{user_id}` | none | Update user by id |
| POST | `/run-etl` | none | Run GCS → Postgres ETL and seed users |

JWTs use `Authorization: Bearer <token>` and expire after `JWT_EXPIRE_MINUTES`.

### Payload examples
Register:
```bash
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "password": "SuperSecret1",
    "full_name": "Demo User",
    "height_cm": 175,
    "weight_kg": 70,
    "body_type": "mesomorphic",
    "gender": "male",
    "age_years": 30,
    "training_goal": "increase strength"
  }'
```

Login:
```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "password": "SuperSecret1"}'
```

Get/update current user (requires token from register/login):
```bash
TOKEN="Bearer <paste-access-token>"
curl -H "Authorization: $TOKEN" http://localhost:8001/users/me

curl -X PUT http://localhost:8001/users/me \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Demo User",
    "height_cm": 176,
    "weight_kg": 71,
    "body_type": "mesomorphic",
    "gender": "male",
    "age_years": 31,
    "training_goal": "lean bulk"
  }'
```

## Data model (see `services/db/init.sql`)
- `users`: profiles + optional auth (hashed passwords). Shared across the platform.
- `gym_recommendation`: curated recommendations from the CSV.
- `exercise_catalog`: exercise lookup table with video URLs and movement metadata.
- `exercise_tracking`: member workout telemetry from the CSV.
- `ml_generated_plans`: populated by planner/RAG services (not by this ETL).

## Common gotchas
- 401 on `/users/me` or `/users/me` updates: missing/expired Bearer token.
- ETL fails immediately: verify `GOOGLE_APPLICATION_CREDENTIALS` points to a readable JSON key with access to `fitai-data-bucket`.
- Cannot reach Postgres: ensure `db` service is up (`docker compose ps`) and env vars match your connection settings.
