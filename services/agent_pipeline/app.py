from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from run_process_calendar import process_calendar

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}

# One-step calendar pipeline
app.post("/process_calendar")(process_calendar)



@app.post("/planner")
async def planner_api(
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Hard-coded planner API for testing.
    """

    # You can print debug info
    print(f"Received user_id={user_id}, file={file.filename}, size={len(await file.read())} bytes")

    # Hard-coded output
    hardcoded_calendar = {
        "user_id": user_id,
        "events": [
            {
                "title": "Workout Session",
                "date": "2025-11-14",
                "start": "08:00",
                "end": "09:00",
                "location": "Gym",
                "notes": "Leg day"
            },
            {
                "title": "Team Meeting",
                "date": "2025-11-14",
                "start": "14:00",
                "end": "15:00",
                "location": "Office",
                "notes": None
            }
        ]
    }

    return hardcoded_calendar