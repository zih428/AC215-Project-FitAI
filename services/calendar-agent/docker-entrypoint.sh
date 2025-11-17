#!/bin/bash
set -e

echo "Starting Calendar Agent container..."
echo "Architecture: $(uname -m)"
echo "Python version: $(python --version)"
echo "UV version: $(uv --version)"

# Activate virtual environment
source /.venv/bin/activate
echo "Virtual environment activated."

# Check Google credentials
if [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
  echo "Error: Google credentials not found at $GOOGLE_APPLICATION_CREDENTIALS"
  exit 1
else
  echo "Google credentials found."
fi

# Start FastAPI server
echo "Starting FastAPI server on port 8004..."
exec uvicorn app:app --host 0.0.0.0 --port 8004 --reload
