# run_ocr_main.py
import os
import sys
from typing import List

from google.cloud import storage
from google.oauth2 import service_account

# Make OCR importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from OCR import OCR  # noqa: E402

# ----------------------------
# GCS configuration
# ----------------------------
PROJECT_ID = "rich-access-471117-r0"
BUCKET_NAME = "fitai-data-bucket"
KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

credentials = service_account.Credentials.from_service_account_file(KEY_PATH)
storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)
bucket = storage_client.bucket(BUCKET_NAME)

# ----------------------------
# Helpers
# ----------------------------
def list_unprocessed_files(raw_folder: str = "raw-literature",
                           processed_folder: str = "processed-literature") -> List[str]:
    """
    Return basenames of PDFs in raw_folder that do NOT have a corresponding .txt in processed_folder.
    """
    raw_blobs = bucket.list_blobs(prefix=raw_folder)
    processed_blobs = bucket.list_blobs(prefix=processed_folder)

    processed_basenames = {
        os.path.splitext(os.path.basename(b.name))[0].lower()
        for b in processed_blobs
        if b.name.lower().endswith(".txt")
    }

    unprocessed = [
        os.path.basename(b.name)
        for b in raw_blobs
        if b.name.lower().endswith(".pdf")
        and os.path.splitext(os.path.basename(b.name))[0].lower() not in processed_basenames
    ]
    return unprocessed

def upload_text_to_gcs(text: str, destination_blob_name: str):
    blob = bucket.blob(destination_blob_name)
    # upload purely from memory (no temp file)
    blob.upload_from_string(text, content_type="text/plain; charset=utf-8")
    print(f"Uploaded text → gs://{BUCKET_NAME}/{destination_blob_name}")

# ----------------------------
# Main OCR Runner (streaming)
# ----------------------------
def run_ocr(full_folder_process: bool = False):
    """
    - If full_folder_process:
        OCR every PDF under raw-literature/ (streams bytes; no local disk writes).
      Else:
        Only OCR PDFs that don't yet have a corresponding .txt under processed-literature/.
    """
    ocr = OCR()

    if full_folder_process:
        # Stream every PDF under raw-literature/
        blobs = bucket.list_blobs(prefix="raw-literature")
        for b in blobs:
            if not b.name.lower().endswith(".pdf"):
                continue
            base = os.path.splitext(os.path.basename(b.name))[0]
            print(f"Processing {b.name} (streaming) ...")
            pdf_bytes = b.download_as_bytes()   # <- in memory
            text = ocr.perform_ocr(pdf_bytes)   # <- in memory
            dest = f"processed-literature/{base}.txt"
            upload_text_to_gcs(text, dest)
    else:
        # Incremental mode — stream only unprocessed
        unprocessed_files = list_unprocessed_files()
        if not unprocessed_files:
            print("No more new files requiring OCR. OCR completed.")
            return

        for base_pdf in unprocessed_files:
            raw_blob = f"raw-literature/{base_pdf}"
            print(f"Processing {raw_blob} (streaming)...")
            pdf_bytes = bucket.blob(raw_blob).download_as_bytes()
            text = ocr.perform_ocr(pdf_bytes)
            base = os.path.splitext(base_pdf)[0]
            dest = f"processed-literature/{base}.txt"
            upload_text_to_gcs(text, dest)

        print(f"OCR completed. {len(unprocessed_files)} file(s) processed.")