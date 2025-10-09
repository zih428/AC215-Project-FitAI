## USES GOOGLE OCR API ##
import os
import sys
from google.cloud import storage
from google.oauth2 import service_account
import shutil

# Add local import path for OCR class
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from OCR import OCR

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

# ----------------------------
# TMP folder setup
# ----------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
TMP_INPUT = os.path.join(script_dir, "tmp", "input")
TMP_OUTPUT = os.path.join(script_dir, "tmp", "output")

os.makedirs(TMP_INPUT, exist_ok=True)
os.makedirs(TMP_OUTPUT, exist_ok=True)


# ----------------------------
# Load OCR from GCS
# ----------------------------

def load_file_from_gcs(blob_name, local_folder_path=TMP_INPUT):
    """
    Download a file from GCS to local path.
    """
    blob = bucket.blob(blob_name)
    local_path = os.path.join(local_folder_path, os.path.basename(blob_name))
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    blob.download_to_filename(local_path)
    print(f"Downloaded gs://{BUCKET_NAME}/{blob_name} → {local_path}")
    return local_path


def load_all_files_from_gcs(folder_in_bucket, local_folder_path=TMP_INPUT):
    """
    Download all files from a GCS folder to local path.
    """
    blobs = bucket.list_blobs(prefix=folder_in_bucket)
    local_paths = []
    for blob in blobs:
        if not blob.name.endswith("/"):
            local_path = os.path.join(local_folder_path, os.path.basename(blob.name))
            blob.download_to_filename(local_path)
            local_paths.append(local_path)
            print(f"Downloaded gs://{BUCKET_NAME}/{blob.name} → {local_path}")
    return local_paths

# ----------------------------
# OCR Processing Single File
# ----------------------------

def run_ocr_main(file_name, input_folder_path=TMP_INPUT, output_folder_path=TMP_OUTPUT):
    """
    Perform OCR on the PDF and export extracted text to a .txt file.
    """
    ocr_engine = OCR()
    input_path = os.path.join(input_folder_path, os.path.basename(file_name))
    extracted_text = ocr_engine.perform_ocr(input_path)

    # Save to text file
    output_file_name = os.path.basename(file_name).replace(".pdf", ".txt")
    output_path = os.path.join(output_folder_path, output_file_name)
    with open(output_path, "w") as f:
        f.write(extracted_text)
    print(f"OCR output saved to {output_path}")

# ----------------------------
# Upload Processed Files to GCS
# ----------------------------
def upload_files_to_gcs(local_folder_path= TMP_OUTPUT, folder_in_bucket ='processed-literature'):
    """
    Upload all files from local folder to GCS folder.
    """
    for file_name in os.listdir(local_folder_path):
        local_path = os.path.join(local_folder_path, file_name)
        if os.path.isfile(local_path):
            blob = bucket.blob(f"{folder_in_bucket}/{file_name}")
            blob.upload_from_filename(local_path)
            print(f"Uploaded {local_path} → gs://{BUCKET_NAME}/{folder_in_bucket}/{file_name}")

def upload_single_file_to_gcs(local_file_path, destination_blob_name):
    """
    Upload a single file to GCS.
    """
    if os.path.isfile(local_file_path):
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(local_file_path)
        print(f"Uploaded {local_file_path} → gs://{BUCKET_NAME}/{destination_blob_name}")


# ----------------------------
# Check Unprocessed Files
# ----------------------------
def list_unprocessed_files(raw_folder='raw-literature', processed_folder='processed-literature'):
    """
    Return basenames of PDFs in raw_folder that do not have a corresponding .txt in processed_folder.
    """
    raw_blobs = bucket.list_blobs(prefix=raw_folder)
    processed_blobs = bucket.list_blobs(prefix=processed_folder)

    processed_pdf_basenames = {
        os.path.splitext(os.path.basename(b.name))[0].lower()  # "foo"
        for b in processed_blobs
        if b.name.lower().endswith('.txt')
    }

    unprocessed_basenames = [
        os.path.basename(b.name)  # "foo.pdf"
        for b in raw_blobs
        if b.name.lower().endswith('.pdf')
        and os.path.splitext(os.path.basename(b.name))[0].lower() not in processed_pdf_basenames
    ]
    return unprocessed_basenames


# ----------------------------
# Main OCR Runner
# ----------------------------
def run_ocr(full_folder_process=False):
    if full_folder_process:
        load_all_files_from_gcs("raw-literature")
        for file in os.listdir(TMP_INPUT):
            if file.lower().endswith(".pdf"):
                run_ocr_main(file)  # uses basename internally
        upload_files_to_gcs()
    else:
        unprocessed_files = list_unprocessed_files()  # returns ["foo.pdf", ...] (basenames)
        for base_pdf in unprocessed_files:
            raw_blob = f"raw-literature/{base_pdf}"
            # 1) download
            local_pdf = load_file_from_gcs(raw_blob)
            # 2) OCR (run_ocr_main uses basename; passing base name or local path both OK)
            run_ocr_main(base_pdf)
            # 3) upload single
            base_txt = os.path.splitext(base_pdf)[0] + ".txt"
            local_txt_path = os.path.join(TMP_OUTPUT, base_txt)  # this exists
            dest_blob = f"processed-literature/{base_txt}"
            upload_single_file_to_gcs(local_txt_path, dest_blob)

    # Delete the local tmp folders to save space
    for folder in [TMP_INPUT, TMP_OUTPUT]:
        shutil.rmtree(folder, ignore_errors=True)

# ----------------------------
if __name__ == "__main__":
    if os.getenv("START_ON_BOOT", "false").lower() == "true":
        run_ocr(os.getenv("PROCESS_FULL_FOLDER", "false").lower() == "true")
    else:
        print("START_ON_BOOT=false → idle. (Nothing processed.)")