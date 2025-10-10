from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
import run_ocr_main
import traceback

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ocr_engine"}

@app.post("/perform-ocr")
def perform_ocr(full_process: bool = False):
    """
    Trigger OCR processing.
    - If full_process=True → process all PDFs in raw-literature.
    - Otherwise → process only unprocessed PDFs.
    """
    try:
        # Run OCR synchronously
        run_ocr_main.run_ocr(full_process)

        # run_ocr_main() itself handles logging and will print
        # "No more new files requiring OCR. OCR completed."
        # if there are no new files to process.
        return {"status": "completed", "message": "OCR process finished."}

    except Exception as e:
        # Log full traceback to container logs for debugging
        print("OCR execution failed:")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )