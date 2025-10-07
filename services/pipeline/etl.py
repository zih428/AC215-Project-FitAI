import os, re, io
import pandas as pd
from sqlalchemy import create_engine
from google.cloud import storage
from google.oauth2 import service_account

# ----------------------------
# Database connection settings
# ----------------------------
DB_USER = os.getenv("POSTGRES_USER", "fitai")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "fitai")
DB_NAME = os.getenv("POSTGRES_DB", "fitai_app")
DB_HOST = os.getenv("POSTGRES_HOST", "db")  # service name from docker-compose
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

engine = create_engine(
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

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
    print(f"✅ Loaded {len(df)} rows into {table_name}")


def run_etl():
    load_csv_to_table("raw-data/gym_recommendation.csv", "gym_recommendation")
    load_csv_to_table("raw-data/gym_members_exercise_tracking.csv", "exercise_tracking")
    load_csv_to_table("raw-data/exercise_catalog.csv", "exercise_catalog")


if __name__ == "__main__":
    run_etl()