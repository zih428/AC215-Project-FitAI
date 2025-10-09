from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
import run_ocr_main
import traceback

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ocr_engine"}

@app.post("/perform-ocr")
def perform_ocr(background_tasks: BackgroundTasks, full_process: bool = False):
    """
    Trigger OCR processing via API.
    If full_process=True → process all PDFs in raw-literature.
    Otherwise → process only unprocessed PDFs.
    """
    try:
        background_tasks.add_task(run_ocr_main.run_ocr, full_process)
        return {"status": "started", "message": "OCR job running in background"}
    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )