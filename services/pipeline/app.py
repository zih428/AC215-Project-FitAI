from fastapi import FastAPI, HTTPException
import logging
import etl

app = FastAPI()
logger = logging.getLogger(__name__)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "pipeline"}

@app.post("/run-etl")
def run_etl():
    try:
        etl.run_etl()
        return {"status": "ETL complete"}
    except Exception as exc:  # pragma: no cover - propagates failure to client
        logger.exception("ETL run failed")
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(exc)})
