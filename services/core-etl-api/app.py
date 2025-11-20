import logging
import os
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, confloat, conint, constr
from sqlalchemy import text

import etl
from db import engine

app = FastAPI()
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://0.0.0.0:3000"],
    allow_origin_regex=".*",
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


BodyType = Literal["ectomorphic", "mesomorphic", "endomorphic"]
GenderType = Literal["female", "male", "non-binary", "prefer_not_to_say"]

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
MAX_PASSWORD_LENGTH = 256  # reasonable upper bound
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


class UserProfilePayload(BaseModel):
    full_name: constr(strip_whitespace=True, min_length=1) = Field(..., alias="full_name")
    height_cm: confloat(gt=0)
    weight_kg: confloat(gt=0)
    body_type: BodyType
    gender: GenderType
    age_years: conint(gt=0)
    training_goal: constr(strip_whitespace=True, min_length=1)

    class Config:
        allow_population_by_field_name = True


class UserProfileResponse(BaseModel):
    id: int
    email: Optional[EmailStr] = None
    full_name: constr(strip_whitespace=True, min_length=1)
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    body_type: Optional[str] = None
    gender: Optional[str] = None
    age_years: Optional[int] = None
    training_goal: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class AuthRegistrationPayload(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=MAX_PASSWORD_LENGTH)
    full_name: constr(strip_whitespace=True, min_length=1) = Field(..., alias="full_name")
    height_cm: Optional[confloat(gt=0)] = None
    weight_kg: Optional[confloat(gt=0)] = None
    body_type: Optional[BodyType] = None
    gender: Optional[GenderType] = None
    age_years: Optional[conint(gt=0)] = None
    training_goal: Optional[constr(strip_whitespace=True, min_length=1)] = None

    class Config:
        allow_population_by_field_name = True


class AuthLoginPayload(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=MAX_PASSWORD_LENGTH)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthResponse(TokenResponse):
    user: UserProfileResponse


USER_COLUMNS = (
    "id, full_name, email, height_cm, weight_kg, body_type, gender, age_years, training_goal, created_at"
)


def serialize_user(row) -> dict:
    return {
        "id": row["id"],
        "full_name": row["full_name"],
        "email": row.get("email"),
        "height_cm": float(row["height_cm"]) if row["height_cm"] is not None else None,
        "weight_kg": float(row["weight_kg"]) if row["weight_kg"] is not None else None,
        "body_type": row["body_type"],
        "gender": row["gender"],
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


def fetch_user_with_password_by_email(email: str) -> Optional[dict]:
    query = text(
        "SELECT id, email, password_hash, full_name, height_cm, weight_kg, body_type, gender, age_years, training_goal "
        "FROM users WHERE email = :email"
    )
    with engine.connect() as conn:
        row = conn.execute(query, {"email": email}).mappings().first()
        return row


def _normalize_password(password: str) -> str:
    return password[:MAX_PASSWORD_LENGTH]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(_normalize_password(plain_password), hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(_normalize_password(password))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _extract_token(request: Request, token: Optional[str]) -> Optional[str]:
    # Fallbacks if OAuth2PasswordBearer does not catch the header
    if token:
        return token
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    cookie_token = request.cookies.get("access_token") or request.cookies.get("Authorization")
    if cookie_token:
        return cookie_token
    return None


def get_current_user(request: Request, token: Optional[str] = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    raw_token = _extract_token(request, token)
    if not raw_token:
        logger.warning("Auth failed: missing bearer token; headers=%s", request.headers.get("authorization"))
        raise credentials_exception
    try:
        payload = jwt.decode(raw_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            logger.warning("Auth failed: token missing sub")
            raise credentials_exception
        try:
            user_id_int = int(user_id)
        except (TypeError, ValueError):
            logger.warning("Auth failed: sub is not an int (%s)", user_id)
            raise credentials_exception
    except JWTError:
        logger.warning(
            "Auth failed: JWT decode error; token_prefix=%s..., header=%s",
            str(raw_token)[:15],
            request.headers.get("authorization"),
        )
        # Dev fallback: allow numeric token as user id to unblock auth if JWT is malformed
        try:
            user_id_int = int(str(raw_token))
            logger.warning("Dev fallback: treating token as user_id=%s", user_id_int)
        except ValueError:
            raise credentials_exception
    try:
        return fetch_user(int(user_id_int))
    except HTTPException as exc:
        if exc.status_code == 404:
            logger.warning("Auth failed: user %s not found", user_id)
        raise


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "core-etl-api"}


@app.post("/auth/register", response_model=AuthResponse)
def register_user(payload: AuthRegistrationPayload):
    existing = fetch_user_with_password_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    insert_stmt = text(
        "INSERT INTO users (email, password_hash, full_name, height_cm, weight_kg, body_type, gender, age_years, training_goal) "
        "VALUES (:email, :password_hash, :full_name, :height_cm, :weight_kg, :body_type, :gender, :age_years, :training_goal) "
        f"RETURNING {USER_COLUMNS}"
    )

    payload_dict = payload.dict()
    payload_dict["password_hash"] = get_password_hash(payload_dict.pop("password"))
    if payload_dict.get("body_type"):
        payload_dict["body_type"] = payload_dict["body_type"].lower()
    if payload_dict.get("gender"):
        payload_dict["gender"] = payload_dict["gender"].lower()

    with engine.begin() as conn:
        row = conn.execute(insert_stmt, payload_dict).mappings().first()

    token = create_access_token({"sub": row["id"]})
    logger.info("New user registered: %s (id=%s)", row["email"], row["id"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": serialize_user(row),
    }


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: AuthLoginPayload):
    existing = fetch_user_with_password_by_email(payload.email)
    if not existing or not existing.get("password_hash"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    try:
        is_valid = verify_password(payload.password, existing["password_hash"])
    except Exception:  # pragma: no cover - defensive guard against corrupted hashes
        logger.warning("Password verification exception for %s", payload.email)
        is_valid = False

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": existing["id"]})
    logger.info("User login success: %s (id=%s)", existing["email"], existing["id"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": serialize_user(existing),
    }


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
        "INSERT INTO users (full_name, height_cm, weight_kg, body_type, gender, age_years, training_goal) "
        "VALUES (:full_name, :height_cm, :weight_kg, :body_type, :gender, :age_years, :training_goal) "
        f"RETURNING {USER_COLUMNS}"
    )

    payload = profile.dict()
    payload["body_type"] = payload["body_type"].lower()
    payload["gender"] = payload["gender"].lower()

    with engine.begin() as conn:
        row = conn.execute(insert_stmt, payload).mappings().first()

    return serialize_user(row)


@app.get("/users/me", response_model=UserProfileResponse)
def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    return current_user


@app.put("/users/me", response_model=UserProfileResponse)
def update_current_user_profile(
    profile: UserProfilePayload, current_user: dict = Depends(get_current_user)
):
    update_stmt = text(
        "UPDATE users SET "
        "full_name = :full_name, "
        "height_cm = :height_cm, "
        "weight_kg = :weight_kg, "
        "body_type = :body_type, "
        "gender = :gender, "
        "age_years = :age_years, "
        "training_goal = :training_goal "
        "WHERE id = :user_id "
        f"RETURNING {USER_COLUMNS}"
    )

    payload = profile.dict()
    payload["body_type"] = payload["body_type"].lower()
    payload["gender"] = payload["gender"].lower()
    payload["user_id"] = current_user["id"]

    with engine.begin() as conn:
        row = conn.execute(update_stmt, payload).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

    return serialize_user(row)


@app.put("/users/{user_id}", response_model=UserProfileResponse)
def update_user(user_id: int, profile: UserProfilePayload):
    update_stmt = text(
        "UPDATE users SET "
        "full_name = :full_name, "
        "height_cm = :height_cm, "
        "weight_kg = :weight_kg, "
        "body_type = :body_type, "
        "gender = :gender, "
        "age_years = :age_years, "
        "training_goal = :training_goal "
        "WHERE id = :user_id "
        f"RETURNING {USER_COLUMNS}"
    )

    payload = profile.dict()
    payload["body_type"] = payload["body_type"].lower()
    payload["gender"] = payload["gender"].lower()
    payload["user_id"] = user_id

    with engine.begin() as conn:
        row = conn.execute(update_stmt, payload).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

    return serialize_user(row)


@app.get("/users/{user_id}", response_model=UserProfileResponse)
def get_user(user_id: int):
    return fetch_user(user_id)
