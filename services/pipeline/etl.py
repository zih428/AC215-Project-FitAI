import os, re
import pandas as pd
from sqlalchemy import create_engine

DB_USER = os.getenv("POSTGRES_USER", "fitai")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "fitai")
DB_NAME = os.getenv("POSTGRES_DB", "fitai_app")
DB_HOST = os.getenv("POSTGRES_HOST", "db")  # service name from docker-compose
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

RAW_DIR = "/data/raw"

def load_csv_to_table(filename, table_name):
    filepath = os.path.join(RAW_DIR, filename)
    print(f"Loading {filepath} into {table_name}...")
    df = pd.read_csv(filepath)
    COLUMN_MAP = {
    "Workout_Frequency (days/week)": "workout_days_per_week",
    "# Primary Items": "primary_items_count",
    "# Secondary Items": "secondary_items_count",
    "Short YouTube Demonstration": "short_demo_url",
    "In-Depth YouTube Explanation": "long_demo_url",
    "Movement Pattern #1": "movement_pattern_1",
    "Movement Pattern #2": "movement_pattern_2",
    "Movement Pattern #3": "movement_pattern_3",
    'Plane Of Motion #1': 'plane_of_motion_1',
    'Plane Of Motion #2': 'plane_of_motion_2',
    'Plane Of Motion #3': 'plane_of_motion_3',
    # add more as needed...
    }

    # apply mapping
    df.rename(columns=COLUMN_MAP, inplace=True)

    # Standardize column names: lowercase and underscores
    df.columns = [
        re.sub(r'[^\w]+', '_', c.strip().lower()).strip('_')
        for c in df.columns
]

    # Rename ID -> source_id
    if "id" in df.columns:
        df = df.rename(columns={"id": "source_id"})

    df.to_sql(table_name, engine, if_exists="append", index=False)
    print(f"✅ Loaded {len(df)} rows into {table_name}")

def run_etl():
    load_csv_to_table("gym_recommendation.csv", "gym_recommendation")
    load_csv_to_table("gym_members_exercise_tracking.csv", "exercise_tracking")
    load_csv_to_table("exercise_catalog.csv", "exercises")

if __name__ == "__main__":
    run_etl()
