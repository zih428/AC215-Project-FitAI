import json
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response

from planner import fetch_user_profile, generate_fitness_plan, save_plan_record
from run_process_calendar import process_calendar
from ics_generator import generate_ics_calendar

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}

# One-step calendar pipeline
app.post("/process_calendar")(process_calendar)

@app.post("/planner")
async def planner_api(
    user_id: int = Form(...),
    file: Optional[UploadFile] = File(None),
    save_to_db: bool = Form(False)
):
    """Use OCR + planner LLM to craft a personalized training plan."""

    calendar_payload = None
    parsed_calendar = None 
    
    if file is not None:
        calendar_response = await process_calendar(file=file)
        parsed_calendar = calendar_response.get("parsed_calendar")
        if not parsed_calendar:
            raise HTTPException(status_code=502, detail="Calendar processing failed")

    if isinstance(parsed_calendar, dict):
        calendar_payload = parsed_calendar
    else:
        try:
            calendar_payload = json.loads(parsed_calendar) if parsed_calendar else None
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Calendar JSON invalid")

    user_profile = fetch_user_profile(user_id)
    fitness_plan = generate_fitness_plan(user_profile, calendar_payload)
    plan_record = None
    if save_to_db:
        plan_record = save_plan_record(user_id, fitness_plan)

    return {
        "user": user_profile,
        "calendar": calendar_payload,
        "fitness_plan": fitness_plan,
        "plan_record": plan_record,
    }

@app.post("/planner/ics")
async def planner_ics(user_id: int, plan: dict):
    """
    Generate .ics calendar file for the user's fitness plan.
    """

    if "training_days" not in plan:
        raise HTTPException(502, "Training plan missing training_days")

    ics_text = generate_ics_calendar(plan, user_id)

    filename = f"fitai_plan_{user_id}.ics"

    return Response(
        content=ics_text,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
