import os, re, io, time
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from passlib.context import CryptContext
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
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def wait_for_db(max_attempts: int = 10, delay_seconds: int = 3):
    """Block until the database is reachable or attempts are exhausted."""
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"Database is up (attempt {attempt}/{max_attempts}).")
            return
        except OperationalError:
            if attempt == max_attempts:
                raise
            print(f"Database not ready (attempt {attempt}/{max_attempts}), retrying in {delay_seconds}s...")
            time.sleep(delay_seconds)


def table_has_rows(table_name: str) -> bool:
    """Return True if the given table already has at least one row."""
    with engine.connect() as conn:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar() or 0
        return count > 0


def load_csv_to_table(blob_name, table_name):
    # Avoid duplicate ingestion when tables already have data
    if table_has_rows(table_name):
        print(f"Skipping load for {table_name}: table already has data.")
        return

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
    """Insert demo users idempotently; skip any already-present emails."""

    demo_password = "88888888"
    demo_password_hash = pwd_context.hash(demo_password)
    demo_users = [
        {
            "full_name": "Avery Chen",
            "email": "averychen@fas.harvard.edu",
            "password_hash": demo_password_hash,
            "height_cm": 170.2,
            "weight_kg": 68.5,
            "body_type": "mesomorph",
            "gender": "female",
            "age_years": 28,
            "training_goal": "build lean muscle",
        },
        {
            "full_name": "Jordan Patel",
            "email": "jordanpatel@fas.harvard.edu",
            "password_hash": demo_password_hash,
            "height_cm": 182.9,
            "weight_kg": 82.1,
            "body_type": "ectomorph",
            "gender": "male",
            "age_years": 34,
            "training_goal": "increase strength",
        },
        {
            "full_name": "Maya Lopez",
            "email": "mayalopez@fas.harvard.edu",
            "password_hash": demo_password_hash,
            "height_cm": 160.0,
            "weight_kg": 60.3,
            "body_type": "endomorph",
            "gender": "female",
            "age_years": 41,
            "training_goal": "improve metabolic health",
        },
        {
            "full_name": "Xuan Zai",
            "email": "steven_ge@fas.harvard.edu",
            "password_hash": demo_password_hash,
            "height_cm": 179.0,
            "weight_kg": 66,
            "body_type": "ectomorphic",
            "gender": "male",
            "age_years": 25,
            "training_goal": "increase strength",
        },
        {
            "full_name": "Leo Cheng",
            "email": "leocheng@g.harvard.edu",
            "password_hash": demo_password_hash,
            "height_cm": 177.0,
            "weight_kg": 67,
            "body_type": "mesomorphic",
            "gender": "male",
            "age_years": 24,
            "training_goal": "increase strength",
        },
    ]

    insert_stmt = text(
        "INSERT INTO users (full_name, email, password_hash, height_cm, weight_kg, body_type, gender, age_years, training_goal) "
        "VALUES (:full_name, :email, :password_hash, :height_cm, :weight_kg, :body_type, :gender, :age_years, :training_goal) "
        "ON CONFLICT (email) DO NOTHING"
    )

    with engine.begin() as conn:
        conn.execute(insert_stmt, demo_users)

    print(f"Seeded up to {len(demo_users)} demo rows into users (skips existing emails)")


def run_etl():
    wait_for_db()
    load_csv_to_table("raw-data/gym_recommendation.csv", "gym_recommendation")
    load_csv_to_table("raw-data/gym_members_exercise_tracking.csv", "exercise_tracking")
    load_csv_to_table("raw-data/exercise_catalog.csv", "exercise_catalog")
    seed_users()


if __name__ == "__main__":
    run_etl()
