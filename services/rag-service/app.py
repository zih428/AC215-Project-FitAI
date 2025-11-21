from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import rag_core

app = FastAPI(title="FitAI RAG Service", version="1.0.0")

# Enable CORS so the frontend can call this service
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
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
