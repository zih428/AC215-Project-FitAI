"""Planner module for generating personalized training plans."""

from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any, Dict

import httpx
import psycopg
from fastapi import HTTPException
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from json_repair import repair_json


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


RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://rag-service:8002")
RAG_QUERY_METHOD = os.getenv("RAG_QUERY_METHOD", "char-split")
RAG_QUERY_RESULTS = int(os.getenv("RAG_QUERY_RESULTS", "5"))
RAG_TIMEOUT = float(os.getenv("RAG_TIMEOUT_SECONDS", "30"))


USER_COLUMNS = """
    id, full_name, height_cm, weight_kg,
    body_type, gender, age_years, training_goal
"""


PLAN_INSTRUCTIONS_w_CALENDAR = """
You are FitAIPlanner, a certified strength coach and nutrition consultant.
Your role is to generate a structured weekly training plan that respects the
user’s schedule, available energy, and training goals.

Return ONLY a valid JSON object matching this schema:
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
- Extract all free windows from the user's calendar and list them in "available_time_blocks".
- Select exactly one training time block per training day and place it in "scheduled_time_block".
- Typical sessions are 45–75 minutes; infer the planned duration based on the exercise selection.
- If multiple free windows exist:
  - choose the most suitable one (e.g., adequate duration, lower conflict likelihood),
  - and provide a concise explanation in "schedule_reason".
- On days with many meetings or limited time, shorten the session accordingly.
- Populate at least 3 training days if the calendar provides at least 3 free days.
- Movements must be specific (e.g., “Barbell Back Squat”, “Bent-Over Row”).
- When equipment availability is unclear, assume access to a commercial gym.
- Do not include Markdown, comments, or natural-language reasoning outside the JSON.

Preference adaptation:
- If the user later provides preferred workout times (morning/evening),
  energy patterns, or availability notes, incorporate these when picking
  "scheduled_time_block" and update "schedule_reason" accordingly.
"""

PLAN_INSTRUCTIONS_no_CALENDAR = """
You are FitAIPlanner, a certified strength coach and nutrition consultant. Craft
training weeks by respecting a user's information and goals.

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
    user_profile: Dict[str, Any], calendar_payload: Dict[str, Any] | None
) -> Dict[str, Any]:
    """Call internal RAG query endpoint with the planner prompt."""

    prompt = _build_prompt(user_profile, calendar_payload)
    payload = {
        "query": prompt,
        "method": RAG_QUERY_METHOD,
        "n_results": RAG_QUERY_RESULTS,
    }

    try:
        response = httpx.post(
            f"{RAG_SERVICE_URL.rstrip('/')}/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=RAG_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="RAG service timeout") from exc
    except httpx.HTTPStatusError as exc:
        detail = (
            f"RAG service error {exc.response.status_code}: {exc.response.text}"
        )
        raise HTTPException(status_code=502, detail=detail) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    outer = response.json()
    plan_raw = outer["response"]

    try:
        repaired_text = repair_json(plan_raw)
        data = json.loads(repaired_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse fitness plan JSON from RAG service, raw text: {plan_raw}"
        ) from exc

    # --- Validate success flag ---
    if outer.get("status") != "success":
        raise HTTPException(
            status_code=502,
            detail=f"RAG service returned failure: {outer.get('status')}"
        )

    return data

def _build_prompt(user_profile: Dict[str, Any], calendar_payload: Dict[str, Any] | None) -> str:
    user_json = json.dumps(user_profile, indent=2)
    if calendar_payload:
        calendar_json = json.dumps(calendar_payload, indent=2) 
        return (
            PLAN_INSTRUCTIONS_w_CALENDAR
            + "\n\nUser profile:\n"
            + f"{user_json}\n\n"
            + "Calendar events extracted from screenshot:\n"
            + f"{calendar_json}\n\n"
            + "Guidelines:\n"
            + "1. Respect existing events when choosing training slots.\n"
            + "2. Prefer strength splits relevant to the stated goal.\n"
            + "3. Always output exact exercise names and loading prescriptions."
        )
    else:
        return (
            PLAN_INSTRUCTIONS_no_CALENDAR
            + "\n\nUser profile:\n"
            + f"{user_json}\n\n"
            + "No calendar data provided.\n\n"
            + "Guidelines:\n"
            + "1. Choose training days based on common patterns for the goal.\n"
            + "2. Prefer strength splits relevant to the stated goal.\n"
            + "3. Always output exact exercise names and loading prescriptions."
        )


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


__all__ = ["fetch_user_profile", "generate_fitness_plan", "save_plan_record"]
