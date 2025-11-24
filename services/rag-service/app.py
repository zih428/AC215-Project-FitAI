from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import rag_core

app = FastAPI(title="FitAI RAG Service", version="1.0.0")

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def get_cors_settings():
    raw_origins = os.getenv("CORS_ALLOW_ORIGINS")
    allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    origins = list(DEFAULT_CORS_ORIGINS)

    if raw_origins:
        extra = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        if extra:
            origins.extend(extra)

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for origin in origins:
        if origin not in seen:
            seen.add(origin)
            deduped.append(origin)

    if "*" in deduped:
        deduped = ["*"]
        allow_credentials = False  # FastAPI restriction when allowing all origins

    return deduped, allow_credentials


cors_origins, cors_allow_credentials = get_cors_settings()

# Enable CORS so the frontend can call this service
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request schemas
class GCSProcessRequest(BaseModel):
    bucket_name: str
    folder_path: str = ""
    method: str = "char-split"  # optional; defaults to char-split

class QueryRequest(BaseModel):
    query: str
    method: str = "char-split"
    n_results: int = 5

class UserProfile(BaseModel):
    id: int
    full_name: str
    height_cm: float
    weight_kg: float
    body_type: str
    gender: str
    age_years: int
    training_goal: str

class ChatRequest(BaseModel):
    query: str
    method: str = "char-split"
    n_results: int = 10
    user_profile: Optional[UserProfile] = None


# API endpoints
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "rag-service"}

@app.post("/process-gcs")
def process_gcs_to_chromadb(request: GCSProcessRequest):
    """Download from GCS, chunk, embed, and persist to ChromaDB in one call."""
    try:
        return rag_core.api_process_gcs_to_chromadb(
            request.bucket_name, 
            request.folder_path, 
            request.method
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
def query_vector_db(request: QueryRequest):
    """Query vector database for similar chunks"""
    try:
        return rag_core.api_query_vector_db(request.query, request.method, request.n_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
def chat_with_llm(request: ChatRequest):
    """Chat with LLM using retrieved context"""
    try:
        return rag_core.api_chat_with_llm(
            request.query,
            request.method,
            request.n_results,
            request.user_profile.dict() if request.user_profile else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/collections")
def list_collections():
    """List all available collections"""
    try:
        return rag_core.api_list_collections()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
