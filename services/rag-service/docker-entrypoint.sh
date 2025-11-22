#!/bin/bash
set -euo pipefail

echo "Container is running!!!"
echo "Architecture: $(uname -m)"

echo "Environment ready! Virtual environment activated."
echo "Python version: $(python --version)"
echo "UV version: $(uv --version)"

# Activate virtual environment
echo "Activating virtual environment..."
source /.venv/bin/activate

# Start FastAPI server in background
echo "Starting FastAPI server..."
python -m uvicorn app:app --host 0.0.0.0 --port 8002 &
UVICORN_PID=$!

# Wait for server health endpoint
echo "Waiting for service health..."
for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:8002/health > /dev/null; then
    echo "Service is healthy."
    break
  fi
  echo "Health check attempt ${attempt} failed, retrying..."
  sleep 2
  if [[ $attempt -eq 30 ]]; then
    echo "Service failed to become healthy, terminating." >&2
    kill "$UVICORN_PID"
    exit 1
  fi
done

# Trigger GCS processing once service is live
echo "Triggering /process-gcs ingestion..."
curl -fsS -X POST "http://127.0.0.1:8002/process-gcs" \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "fitai-data-bucket",
    "folder_path": "processed-literature",
    "method": "char-split"
  }'
echo "Ingestion request completed."

# Keep container alive by waiting on uvicorn
wait "$UVICORN_PID"
