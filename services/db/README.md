### PostgreSQL

#### Schema overview (`init.sql`)
`services/db/init.sql` recreates the schema whenever Postgres starts fresh. It provisions:
- `gym_recommendation`, `exercise_catalog`, `exercise_tracking`: populated by the ETL job from CSVs.
- `users`: intended for real user profiles; while the system is in development the ETL seeds a few demo rows so downstream components can exercise the schema. Demo seed accounts (password `88888888`): Avery Chen `averychen@fas.harvard.edu`, Jordan Patel `jordanpatel@fas.harvard.edu`, Maya Lopez `mayalopez@fas.harvard.edu`, Xuan Zai `steven_ge@fas.harvard.edu`, Leo Cheng `leocheng@g.harvard.edu`.
- `ml_generated_plans`: stores training plans produced by the ML/RAG stack (this table is not filled by the CSV ingestion flow).

The script keeps all tables and seed data consistent across container rebuilds.

#### Ingest raw data into the database
```bash
curl -X POST http://localhost:8001/run-etl
```
This ingests CSV data from GCS into `exercise_catalog`, `exercise_tracking`, and `gym_recommendation`, then seeds demo rows into `users` so the rest of the platform has placeholder user records until real onboarding is wired up.

#### Run the code below to see what's in the `users` table
```bash
docker compose exec db psql -U fitai -d fitai_app
select * from users;
```
| id | full_name    | email                          | password  | height_cm | weight_kg | body_type | age_years | training_goal             | created_at              |
|----|--------------|--------------------------------|-----------|-----------|-----------|-----------|-----------|---------------------------|-------------------------|
| 1  | Avery Chen   | averychen@fas.harvard.edu      | 88888888  | 170.20    | 68.50     | mesomorph | 28        | build lean muscle        | 2025-11-07 03:39:56.686474 |
| 2  | Jordan Patel | jordanpatel@fas.harvard.edu    | 88888888  | 182.90    | 82.10     | ectomorph | 34        | increase strength        | 2025-11-07 03:39:56.686474 |
| 3  | Maya Lopez   | mayalopez@fas.harvard.edu      | 88888888  | 160.00    | 60.30     | endomorph | 41        | improve metabolic health | 2025-11-07 03:39:56.686474 |
| 4  | Xuan Zai     | steven_ge@fas.harvard.edu      | 88888888  | 179.00    | 66.00     | ectomorphic | 25        | increase strength        | 2025-11-07 03:39:56.686474 |
| 5  | Leo Cheng    | leocheng@g.harvard.edu         | 88888888  | 177.00    | 67.00     | mesomorphic | 24        | increase strength        | 2025-11-07 03:39:56.686474 |

#### Read a table into pandas
```python
import os
import pandas as pd
from sqlalchemy import create_engine

DB_USER = os.getenv("POSTGRES_USER", "fitai")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "fitai")
DB_NAME = os.getenv("POSTGRES_DB", "fitai_app")
DB_HOST = os.getenv("POSTGRES_HOST", "db")  # service name from docker-compose
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

engine = create_engine(
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

df = pd.read_sql("SELECT * FROM users", engine)
print(df.head())
```
