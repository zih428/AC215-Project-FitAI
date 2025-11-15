from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, constr, Field, confloat, conint
from typing import Literal
from sqlalchemy import text
import logging
import etl
from db import engine

app = FastAPI()
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


BodyType = Literal["ectomorphic", "mesomorphic", "endomorphic"]


class UserProfilePayload(BaseModel):
    full_name: constr(strip_whitespace=True, min_length=1) = Field(..., alias="full_name")
    height_cm: confloat(gt=0)
    weight_kg: confloat(gt=0)
    body_type: BodyType
    age_years: conint(gt=0)
    training_goal: constr(strip_whitespace=True, min_length=1)

    class Config:
        allow_population_by_field_name = True


class UserProfileResponse(UserProfilePayload):
    id: int

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


USER_COLUMNS = (
    "id, full_name, height_cm, weight_kg, body_type, age_years, training_goal, created_at"
)


def serialize_user(row) -> dict:
    return {
        "id": row["id"],
        "full_name": row["full_name"],
        "height_cm": float(row["height_cm"]) if row["height_cm"] is not None else None,
        "weight_kg": float(row["weight_kg"]) if row["weight_kg"] is not None else None,
        "body_type": row["body_type"],
        "age_years": row["age_years"],
        "training_goal": row["training_goal"],
    }


def fetch_user(user_id: int) -> dict:
    query = text(f"SELECT {USER_COLUMNS} FROM users WHERE id = :user_id")
    with engine.connect() as conn:
        row = conn.execute(query, {"user_id": user_id}).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return serialize_user(row)


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
        raise HTTPException(
            status_code=500, detail={"status": "error", "message": str(exc)}
        )


@app.post("/users", response_model=UserProfileResponse)
def create_user(profile: UserProfilePayload):
    insert_stmt = text(
        "INSERT INTO users (full_name, height_cm, weight_kg, body_type, age_years, training_goal) "
        "VALUES (:full_name, :height_cm, :weight_kg, :body_type, :age_years, :training_goal) "
        f"RETURNING {USER_COLUMNS}"
    )

    payload = profile.dict()
    payload["body_type"] = payload["body_type"].lower()

    with engine.begin() as conn:
        row = conn.execute(insert_stmt, payload).mappings().first()

    return serialize_user(row)


@app.put("/users/{user_id}", response_model=UserProfileResponse)
def update_user(user_id: int, profile: UserProfilePayload):
    update_stmt = text(
        "UPDATE users SET "
        "full_name = :full_name, "
        "height_cm = :height_cm, "
        "weight_kg = :weight_kg, "
        "body_type = :body_type, "
        "age_years = :age_years, "
        "training_goal = :training_goal "
        "WHERE id = :user_id "
        f"RETURNING {USER_COLUMNS}"
    )

    payload = profile.dict()
    payload["body_type"] = payload["body_type"].lower()
    payload["user_id"] = user_id

    with engine.begin() as conn:
        row = conn.execute(update_stmt, payload).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

    return serialize_user(row)


@app.get("/users/{user_id}", response_model=UserProfileResponse)
def get_user(user_id: int):
    return fetch_user(user_id)
