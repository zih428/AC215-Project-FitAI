#!/bin/bash
set -e

echo "Container is running!!!"
echo "Architecture: $(uname -m)"

echo "Environment ready! Virtual environment activated."
echo "Python version: $(python --version)"
echo "UV version: $(uv --version)"

# Activate virtual environment
echo "Activating virtual environment..."
source /.venv/bin/activate

# Start FastAPI server
echo "Starting FastAPI server..."
exec python -m uvicorn app:app --host 0.0.0.0 --port 8002