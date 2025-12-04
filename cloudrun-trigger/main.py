import requests

RAG_URL = "http://34.63.130.184:8002"

payload = {
    "bucket_name": "fitai-data-bucket",
    "folder_path": "processed-literature",
    "method": "char-split"
}

resp = requests.post(
    f"{RAG_URL}/process-gcs",
    json=payload,
    timeout=600 
)

print("Status code:", resp.status_code)
print("Response:", resp.text)