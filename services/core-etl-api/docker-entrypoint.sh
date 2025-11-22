#!/bin/bash
set -euo pipefail

# Activate project virtualenv (created by uv)
if [ -d "/.venv" ]; then
  source "/.venv/bin/activate"
fi

echo "[core-etl-api] Bootstrapping database via ETL..."
python - <<'PY'
from etl import run_etl

run_etl()
PY
echo "[core-etl-api] ETL completed successfully."

exec "$@"
