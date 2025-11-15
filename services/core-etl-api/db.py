import os
from sqlalchemy import create_engine

DB_USER = os.getenv("POSTGRES_USER", "fitai")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "fitai")
DB_NAME = os.getenv("POSTGRES_DB", "fitai_app")
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

engine = create_engine(
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
