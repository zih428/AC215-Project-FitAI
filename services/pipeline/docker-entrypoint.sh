#!/bin/bash
set -euo pipefail

echo "[pipeline] Bootstrapping database via ETL..."
python - <<'PY'
from etl import run_etl

run_etl()
PY
echo "[pipeline] ETL completed successfully."

exec "$@"
