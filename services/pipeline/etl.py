import os, re, io
import pandas as pd
from sqlalchemy import text
from google.cloud import storage
from google.oauth2 import service_account
from db import engine

# ----------------------------
# GCS configuration
# ----------------------------
PROJECT_ID = "rich-access-471117-r0"
BUCKET_NAME = "fitai-data-bucket"
KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Setup GCS client
credentials = service_account.Credentials.from_service_account_file(KEY_PATH)
storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)
bucket = storage_client.bucket(BUCKET_NAME)


def load_csv_to_table(blob_name, table_name):
    print(f"Loading gs://{BUCKET_NAME}/{blob_name} into {table_name}...")

    # Read file directly from GCS into memory
    blob = bucket.blob(blob_name)
    csv_bytes = blob.download_as_bytes()
    df = pd.read_csv(io.BytesIO(csv_bytes))

    # Column mapping
    COLUMN_MAP = {
        "Workout_Frequency (days/week)": "workout_days_per_week",
        "# Primary Items": "primary_items_count",
        "# Secondary Items": "secondary_items_count",
        "Short YouTube Demonstration": "short_demo_url",
        "In-Depth YouTube Explanation": "long_demo_url",
        "Movement Pattern #1": "movement_pattern_1",
        "Movement Pattern #2": "movement_pattern_2",
        "Movement Pattern #3": "movement_pattern_3",
        "Plane Of Motion #1": "plane_of_motion_1",
        "Plane Of Motion #2": "plane_of_motion_2",
        "Plane Of Motion #3": "plane_of_motion_3",
        # add more as needed...
    }
    df.rename(columns=COLUMN_MAP, inplace=True)

    # Standardize column names: lowercase and underscores
    df.columns = [
        re.sub(r"[^\w]+", "_", c.strip().lower()).strip("_") for c in df.columns
    ]

    # Rename ID -> source_id if present
    if "id" in df.columns:
        df = df.rename(columns={"id": "source_id"})

    # Write to Postgres
    df.to_sql(table_name, engine, if_exists="append", index=False)
    print(f"Loaded {len(df)} rows into {table_name}")


def seed_users():
    """Insert a few demo users so the USER table always has baseline data."""
    demo_users = [
        {
            "full_name": "Avery Chen",
            "height_cm": 170.2,
            "weight_kg": 68.5,
            "body_type": "mesomorph",
            "age_years": 28,
            "training_goal": "build lean muscle",
        },
        {
            "full_name": "Jordan Patel",
            "height_cm": 182.9,
            "weight_kg": 82.1,
            "body_type": "ectomorph",
            "age_years": 34,
            "training_goal": "increase strength",
        },
        {
            "full_name": "Maya Lopez",
            "height_cm": 160.0,
            "weight_kg": 60.3,
            "body_type": "endomorph",
            "age_years": 41,
            "training_goal": "improve metabolic health",
        },
    ]

    insert_stmt = text(
        "INSERT INTO users (full_name, height_cm, weight_kg, body_type, age_years, training_goal) "
        "VALUES (:full_name, :height_cm, :weight_kg, :body_type, :age_years, :training_goal)"
    )

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
        conn.execute(insert_stmt, demo_users)

    print(f"Seeded {len(demo_users)} demo rows into users")


def run_etl():
    load_csv_to_table("raw-data/gym_recommendation.csv", "gym_recommendation")
    load_csv_to_table("raw-data/gym_members_exercise_tracking.csv", "exercise_tracking")
    load_csv_to_table("raw-data/exercise_catalog.csv", "exercise_catalog")
    seed_users()


if __name__ == "__main__":
    run_etl()
