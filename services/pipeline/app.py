from fastapi import FastAPI
import etl

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "pipeline"}

@app.post("/run-etl")
def run_etl():
    etl.run_etl()
    return {"status": "ETL complete"}
