# OCR Engine Service

FastAPI microservice that converts PDF research papers stored in Google Cloud Storage (GCS) into plain text using Google Cloud Vision. The service exposes a simple HTTP API for on-demand OCR runs and is containerized for deployment alongside the rest of the FitAI stack (RAG Pipline).

- **Language / Runtime:** Python 3.12 (managed with `uv`)
- **Endpoints:** `/health`, `/perform-ocr`
- **External services:** Google Cloud Vision API, Google Cloud Storage

## How It Works

1. `run_ocr_main.py` queries the `fitai-data-bucket` GCS bucket.
2. For every PDF selected, `OCR.perform_ocr` streams pages through PyMuPDF, renders them as PNGs, and submits them to Google Cloud Vision.
3. The extracted text is written back to `processed-literature/<file>.txt` in the same bucket.
4. The FastAPI route `/perform-ocr` lets callers choose between incremental processing (default) or a full reprocess of the entire `raw-literature/` prefix.

Incremental runs only touch PDFs that do **not** yet have a matching `.txt` output. Full runs ignore previous outputs and reprocess everything.

## Prerequisites

- Google Cloud project with Vision and Storage APIs enabled.
- Service account key with `roles/storage.objectAdmin` (or narrower read/write pair) and `roles/vision.user`.
- Local copy of the JSON key file mounted or copied into the container.
- Docker (for container usage) **or** Python 3.12 with [`uv`](https://github.com/astral-sh/uv) for local development.

### Required Environment Variables

| Variable | Description | Example |
| --- | --- | --- |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to the service account JSON key file (inside the container or host). | `/secrets/rich-access-471117-r0-f17d92fbf298.json` |

When not set, `run_ocr_main.py` falls back to the baked-in defaults above.

## Running With Docker Compose

```bash
docker compose up ocr_engine
```

The root `docker-compose.yml` mounts the credentials JSON into `/secrets` and publishes the API on `localhost:8003`. Logs stream to the terminal; the OCR run output is visible there.

To run the whole FitAI stack (database, pipelines, OCR, RAG, etc.) at once:

```bash
docker compose up
```

Stop the stack with `Ctrl+C`. Containers can be removed using `docker compose down`.

## Local Development (without Docker)

1. **Install uv (once):**
   ```bash
   pip install uv
   ```

2. **Create the virtual environment and sync dependencies:**
   ```bash
   cd services/ocr_engine
   uv sync
   ```

   This creates a `.venv/` directory and installs the packages listed in `pyproject.toml`.

3. **Export credentials:**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/key.json
   ```

4. **Run the API locally:**
   ```bash
   uv run uvicorn app:app --host 0.0.0.0 --port 8003 --reload
   ```

   Visit <http://localhost:8003/health> to confirm the service is ready.

## API Reference

- `GET /health`  
  Returns basic service and status information. Useful for readiness checks.

- `POST /perform-ocr?full_process=false`  
  Triggers an OCR job.
  - `full_process=false` (default): only PDFs that are missing `.txt` outputs are processed.
  - `full_process=true`: reprocesses every PDF under `raw-literature/`.

Example call:

```bash
curl -X POST "http://localhost:8003/perform-ocr?full_process=false"
```

Successful responses return:

```json
{
  "status": "completed",
  "message": "OCR process finished."
}
```

If the run fails, the endpoint responds with HTTP 500 and the error message for quick troubleshooting; check container logs for full stack traces.

## File Layout

- `app.py` – FastAPI application exposing the OCR endpoints.
- `run_ocr_main.py` – Orchestrates bucket discovery, streaming downloads, OCR, and uploads.
- `OCR.py` – Wraps PyMuPDF rendering and Google Cloud Vision document OCR.
- `docker-entrypoint.sh` – Container startup script, activates the virtualenv and launches Uvicorn.
- `Dockerfile` – Builds the Python 3.12 image with pinned dependencies via `uv`.

## Troubleshooting

- **`GOOGLE_APPLICATION_CREDENTIALS` missing:** Ensure the JSON file exists at the configured path and is mounted read-only in Docker (`:ro`).
- **Vision API quota / permissions errors:** Confirm the service account has Vision and Storage permissions and quotas are sufficient.
- **Blank OCR output:** Google Vision sometimes omits text for low-resolution scans; raise the DPI conversion in `OCR.py` if needed.
- **Stale dependencies:** Re-run `uv sync` after updating `pyproject.toml` or `uv.lock` and restart the service.


