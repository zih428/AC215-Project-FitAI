"""Planner module for generating personalized training plans using Gemini."""

from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any, Dict

import psycopg
from google import genai
from fastapi import HTTPException
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from json_repair import repair_json
from google.genai import types



# ---------------------------------------------------------------------------
# Environment and client setup
# ---------------------------------------------------------------------------
POSTGRES_USER = os.getenv("POSTGRES_USER", "fitai")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "fitai")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "fitai_app")

DB_CONNINFO = (
    f"dbname={POSTGRES_DB} user={POSTGRES_USER} password={POSTGRES_PASSWORD} "
    f"host={POSTGRES_HOST} port={POSTGRES_PORT}"
)

# Gemini Setup
_raw_gemini_key = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_KEY = _raw_gemini_key.strip()

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is required for planner agent")

client = genai.Client(api_key=GEMINI_API_KEY)

USER_COLUMNS = """
    id, full_name, height_cm, weight_kg,
    body_type, gender, age_years, training_goal
"""

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

PLAN_INSTRUCTIONS_w_CALENDAR = """
You are FitAIPlanner, a certified strength coach and nutrition consultant.
Your role is to generate a structured weekly training plan that respects the
user’s schedule, available energy, and training goals.

You will be provided with:
1. The user's profile
2. The user's calendar

Your task is to use your expert knowledge of exercise science to create a complete, structured training plan.
Return ONLY valid JSON matching the schema below:
{
  "plan_summary": "string",
  "training_days": [
    {
      "date": "YYYY-MM-DD",
      "day_of_week": "string",
      "available_time_blocks": ["HH:MM-HH:MM"],
      "scheduled_time_block": "HH:MM-HH:MM",
      "schedule_reason": "string",
      "workout_focus": "string",
      "movements": [
        {
          "name": "string",
          "sets_reps": "ex: 4x8 @ RPE 8",
          "equipment": "string or null",
          "coaching_notes": "string"
        }
      ],
      "conditioning_or_cardio": "string or null",
      "recovery": "string"
    }
  ],
  "recovery_notes": "string",
  "nutrition_notes": "string"
}

Scheduling rules:
- **IGNORE SYSTEM HOLIDAYS:** Do not treat public holiday markers (e.g., "Veterans Day", "Labor Day", "Thanksgiving") as busy times or conflicts. Assume the user is free on these days unless there is a specific personal conflicting event.
- Extract all free windows from the user's calendar and list them in "available_time_blocks".
- Select exactly one training time block per training day and place it in "scheduled_time_block".
- **CRITICAL: The start time of the training session MUST be at least 30 minutes after the end of any preceding calendar event. Do not schedule workouts back-to-back with prior commitments.**
- Typical sessions are 45–75 minutes; infer the planned duration based on the exercise selection.
- If multiple free windows exist:
  - choose the most suitable one (e.g., adequate duration, lower conflict likelihood),
  - and provide a concise explanation in "schedule_reason".
- On days with many meetings or limited time, shorten the session accordingly.
- Movements must be specific (e.g., “Barbell Back Squat”, “Bent-Over Row”).
- When equipment availability is unclear, assume access to a commercial gym.
- Do not include Markdown, comments, or natural-language reasoning outside the JSON.
"""

PLAN_INSTRUCTIONS_no_CALENDAR = """
You are FitAIPlanner, a certified strength coach and nutrition consultant.
Your role is to craft structured training weeks by respecting a user's information and goals.

You will be provided with:
1. The user's profile

Your task is to use your expert knowledge of exercise science to create a complete, structured training plan.

Return ONLY a valid JSON object matching this schema:
{
  "plan_summary": "string",
  "training_days": [
    {
      "day_of_week": "string",
      "workout_focus": "string",
      "movements": [
        {
          "name": "string",
          "sets_reps": "ex: 4x8 @ RPE 8",
          "equipment": "string or null",
          "coaching_notes": "string"
        }
      ],
      "conditioning_or_cardio": "string or null",
      "recovery": "string"
    }
  ],
  "recovery_notes": "string",
  "nutrition_notes": "string"
}

Rules:
- Movements must be specific (e.g., "Barbell Back Squat", "Bent-Over Row").
- When unsure about equipment, assume commercial gym availability.
- Do not emit Markdown or commentary—JSON only.
"""


def fetch_user_profile(user_id: int) -> Dict[str, Any]:
    """Retrieve user attributes from Postgres or raise 404 if missing."""

    query = f"SELECT {USER_COLUMNS} FROM users WHERE id = %s"
    with psycopg.connect(conninfo=DB_CONNINFO, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id,))
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User profile not found")

    return {
        "id": row["id"],
        "full_name": row["full_name"],
        "height_cm": _to_float(row["height_cm"]),
        "weight_kg": _to_float(row["weight_kg"]),
        "body_type": row["body_type"],
        "gender": row["gender"],
        "age_years": row["age_years"],
        "training_goal": row["training_goal"],
    }


def generate_fitness_plan(
    user_profile: dict,
    calendar_payload: dict | None
) -> dict:
    """
    Uses Google Gemini via client.models.generate_content to synthesize
    a structured JSON training plan.
    """

    # Pick correct system instructions
    if calendar_payload:
        system_instruction = PLAN_INSTRUCTIONS_w_CALENDAR
    else:
        system_instruction = PLAN_INSTRUCTIONS_no_CALENDAR

    # Build full prompt
    prompt_content = f"""
    {system_instruction}

    Here is the data context for the user you are assisting:

    --- USER PROFILE ---
    {json.dumps(user_profile, indent=2)}

    --- CALENDAR DATA ---
    {json.dumps(calendar_payload, indent=2) if calendar_payload else 'No calendar provided.'}

    Return ONLY the JSON required by the schema. No explanations.
    """

    try:
        # ❗ Use the same style as your step1/step2/step3 pipeline
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt_content,
            config=types.GenerateContentConfig(
                    response_mime_type="text/plain",
                    temperature=0.3
        )
        )

        # Validate content
        if not response.text:
            raise ValueError("Gemini response was empty or blocked.")

        return json.loads(response.text)

    except json.JSONDecodeError:
        # Auto-repair common LLM mistakes
        repaired = repair_json(response.text)
        return json.loads(repaired)

    except Exception as e:
        print(f"Gemini generation error: {e}")
        raise HTTPException(status_code=502, detail="Error generating plan with Gemini")


def _to_float(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def save_plan_record(
    user_id: int, plan: Dict[str, Any], citations: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """
    Persist the generated plan JSON to Postgres so we can reference it later.
    """
    insert_sql = """
        INSERT INTO ml_generated_plans (user_id, plan_json, citations)
        VALUES (%s, %s, %s)
        RETURNING id, created_at
    """

    with psycopg.connect(conninfo=DB_CONNINFO) as conn:
        with conn.cursor() as cur:
            cur.execute(
                insert_sql,
                (
                    user_id,
                    Jsonb(plan),
                    Jsonb(citations) if citations is not None else None,
                ),
            )
            row = cur.fetchone()
        conn.commit()

    return {
        "id": row[0],
        "created_at": row[1].isoformat() if row[1] else None,
    }


def fetch_plan_history(user_id: int) -> list[Dict[str, Any]]:
    """
    Retrieve saved plans for a user, newest first.
    """
    query = """
        SELECT id, plan_json, citations, created_at
        FROM ml_generated_plans
        WHERE user_id = %s
        ORDER BY created_at DESC, id DESC
    """
    with psycopg.connect(conninfo=DB_CONNINFO, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id,))
            rows = cur.fetchall()

    history: list[Dict[str, Any]] = []
    for row in rows:
        history.append(
            {
                "id": row["id"],
                "plan_json": row["plan_json"],
                "citations": row["citations"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
        )
    return history


__all__ = ["fetch_user_profile", "generate_fitness_plan", "save_plan_record", "fetch_plan_history"]