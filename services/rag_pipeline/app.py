from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import rag_core

app = FastAPI(title="FitAI RAG Pipeline", version="1.0.0")

# 定义API请求的格式
class GCSProcessRequest(BaseModel):
    bucket_name: str
    folder_path: str = ""
    method: str = "char-split" #可以不提供，默认用char-split

class QueryRequest(BaseModel):
    query: str
    method: str = "char-split"
    n_results: int = 5

class ChatRequest(BaseModel):
    query: str
    method: str = "char-split"
    n_results: int = 10


# API 端点
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "rag_pipeline"}

@app.post("/process-gcs")
def process_gcs_to_chromadb(request: GCSProcessRequest):
    """一键处理: 从GCS下载文件 -> 分块 -> 生成嵌入 -> 存储到ChromaDB"""
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
        return rag_core.api_chat_with_llm(request.query, request.method, request.n_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/collections")
def list_collections():
    """List all available collections"""
    try:
        return rag_core.api_list_collections()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
