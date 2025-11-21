from google.cloud import storage
import os

# Path to your service account
KEY_PATH = "secrets/sa.json"

# Local file to upload
LOCAL_FILE = "sft/sft_v1.jsonl"

# Where to upload in GCS
BUCKET_NAME = "fitai-data-bucket"
DEST_PATH = "sft/sft_v1.jsonl"

def upload_file():
    # Authenticate
    client = storage.Client.from_service_account_json(KEY_PATH)

    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(DEST_PATH)

    blob.upload_from_filename(LOCAL_FILE)

    print(f"Upload complete: gs://{BUCKET_NAME}/{DEST_PATH}")

if __name__ == "__main__":
    upload_file()