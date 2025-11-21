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

RAG_SUGGESTION_PROMPT = """
You are a fitness knowledge assistant. Given the user's profile and/or schedule,
provide a concise set of training recommendations, exercise ideas, and guidance.
Do NOT return structured JSON. Do NOT return schemas. Output only natural text.

Focus on:
- main movement patterns useful for this user,
- suggested splits (push/pull/legs etc.),
- timing considerations if calendar is provided,
- exercise examples and rationale.

Keep the response short and concise, NOT formatted.
"""

PLAN_INSTRUCTIONS_w_CALENDAR = """
You are FitAIPlanner, a certified strength coach and nutrition consultant.
Your role is to generate a structured weekly training plan that respects the
user’s schedule, available energy, and training goals.

You will be provided with:
1. The user's profile
2. The user's calendar (if available)
3. The raw training suggestions produced by a RAG model

Your task is to transform these inputs into a complete, structured training plan.
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
- Extract all free windows from the user's calendar and list them in "available_time_blocks".
- Select exactly one training time block per training day and place it in "scheduled_time_block".
- Typical sessions are 45–75 minutes; infer the planned duration based on the exercise selection.
- If multiple free windows exist:
  - choose the most suitable one (e.g., adequate duration, lower conflict likelihood),
  - and provide a concise explanation in "schedule_reason".
- On days with many meetings or limited time, shorten the session accordingly.
- Movements must be specific (e.g., “Barbell Back Squat”, “Bent-Over Row”).
- When equipment availability is unclear, assume access to a commercial gym.
- Do not include Markdown, comments, or natural-language reasoning outside the JSON.

Preference adaptation:
- If the user later provides preferred workout times (morning/evening),
  energy patterns, or availability notes, incorporate these when picking
  "scheduled_time_block" and update "schedule_reason" accordingly.
"""

PLAN_INSTRUCTIONS_no_CALENDAR = """
training weeks by respecting a user's information and goals.

You are FitAIPlanner, a certified strength coach and nutrition consultant.
Your role is to craft structuredtraining weeks by respecting a user's information and goals.

You will be provided with:
1. The user's profile
2. The raw training suggestions produced by a RAG model

Your task is to transform these inputs into a complete, structured training plan.

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

from openai import OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def refine_with_openai(
    rag_output_text: str,
    user_profile: dict,
    calendar_payload: dict | None
) -> dict:
    if calendar_payload:
        schema_prompt = PLAN_INSTRUCTIONS_w_CALENDAR
    else:
        schema_prompt = PLAN_INSTRUCTIONS_no_CALENDAR
    
    schema_prompt += "\n\nEnsure the output is valid JSON matching the schema."
    

    messages = [
        {"role": "system", "content": schema_prompt},
        {"role": "user", "content": f"User profile:\n{json.dumps(user_profile, indent=2)}"},
        {"role": "user", "content": f"Calendar:\n{json.dumps(calendar_payload, indent=2) if calendar_payload else 'No calendar'}"},
        {"role": "user", "content": f"RAG model Suggestion:\n{rag_output_text}"}
    ]

    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=2000
    )

    cleaned = resp.choices[0].message.content.strip()
    return json.loads(cleaned)

def generate_fitness_plan(
    user_profile: Dict[str, Any], calendar_payload: Dict[str, Any] | None
) -> Dict[str, Any]:
    """Call internal RAG query endpoint with the planner prompt."""

    prompt = _build_prompt_for_rag(user_profile, calendar_payload)
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
    rag_text = outer["response"]
    if outer.get("status") != "success":
        raise HTTPException(
            status_code=502,
            detail=f"RAG service returned failure: {outer.get('status')}"
        )


    structured_plan = refine_with_openai(
    rag_output_text=rag_text,
    user_profile=user_profile,
    calendar_payload=calendar_payload)

    if type(structured_plan) is dict:
        return structured_plan
    else:
        try:
            repaired_text = repair_json(structured_plan)
            data = json.loads(repaired_text)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to parse fitness plan JSON from RAG service, raw text: {plan_raw}"
            ) from exc

        return data

def _build_prompt_for_rag(user_profile, calendar_payload):
    prompt = RAG_SUGGESTION_PROMPT
    prompt += "\n\nUser profile:\n" + json.dumps(user_profile, indent=2) 

    if calendar_payload:
        prompt += "\n\nCalendar:\n" + json.dumps(calendar_payload, indent=2)
    else:
        prompt += "\n\nNo calendar data provided."

    return prompt

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
