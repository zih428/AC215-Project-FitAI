from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ocr_engine"}

# @app.post("/run-etl")
# def run_etl():
#     etl.run_etl()
#     return {"status": "ETL complete"}
