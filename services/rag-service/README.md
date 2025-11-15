# FitAI RAG Service - Quick Start Guide

## 🚀 Overview

**FitAI RAG Service** is a cloud-based Retrieval-Augmented Generation (RAG) service built on **Google Cloud Storage (GCS)** that provides intelligent Q&A for **fitness** and **nutrition** knowledge.

### ✨ Core Features
- **Cloud Storage**: Reads and processes `.txt` files directly from GCS  
- **Smart Chunking**: Supports character, recursive, and semantic splitting  
- **Vector Search**: Uses Google Vertex AI for embeddings  
- **LLM Conversation**: Powered by Gemini 2.0 Flash for intelligent Q&A  
- **Persistence**: Stores vector embeddings in ChromaDB for long-term access  

## 🏗️ Architecture Overview

```
GCS File → Loaded into Memory → Chunking → Embedding Generation → Stored in ChromaDB → Intelligent Q&A
```

### 📊 Data Flow
1. **GCS Storage**: Raw `.txt` files are stored in Google Cloud Storage  
2. **In-Memory Processing**: Files are downloaded into memory for chunking and embedding  
3. **Vector Storage**: Embeddings are stored in ChromaDB  
4. **Semantic Retrieval**: Retrieves documents based on semantic similarity  
5. **LLM Generation**: Generates professional answers using retrieved context  

### 🔧 Tech Stack
- **FastAPI** – RESTful API service  
- **ChromaDB** – Vector database  
- **Google Vertex AI** – Embedding and LLM services  
- **Google Cloud Storage** – File storage  
- **Docker** – Containerized deployment  

## 📡 API Endpoints Overview

| Endpoint | Method | Description | Purpose |
|-----------|--------|-------------|----------|
| `/health` | GET | Health check | Check service status |
| `/process-gcs` | POST | One-click GCS file processing | Download → Chunk → Embed → Store |
| `/query` | POST | Vector search | Retrieve relevant documents |
| `/chat` | POST | LLM conversation | Context-based dialogue |
| `/collections` | GET | List collections | View available datasets |

---

## ⚡ Quick Start

### 1. Start All Services
```bash
# Run in project root
docker compose up -d
```

### 2. Check Service Status
```bash
docker compose ps

# Check RAG service logs
docker compose logs rag-service
```

### 3. Test APIs
```bash
# Check service health
curl http://localhost:8002/health

# View available collections
curl http://localhost:8002/collections
```

---

## 🚀 Interaction Flow

### Step 1: Prepare GCS Data
Ensure that your `.txt` files are uploaded to your **Google Cloud Storage bucket**.

### Step 2: One-Click Process GCS Files
```bash
# Process files from GCS to ChromaDB
curl -X POST "http://localhost:8002/process-gcs"   -H "Content-Type: application/json"   -d '{
    "bucket_name": "fitai-data-bucket",
    "folder_path": "fitness-docs/",
    "method": "char-split"
  }'
```

**Parameters:**
- `bucket_name`: Name of the GCS bucket  
- `folder_path`: Folder path (optional; empty = root directory)  
- `method`: Chunking method (`char-split`, `recursive-split`, `semantic-split`)  

### Step 3: Intelligent Q&A
```bash
# Fitness knowledge Q&A
curl -X POST "http://localhost:8002/chat"   -H "Content-Type: application/json"   -d '{
    "query": "What are the main findings about resistance training progression?",
    "method": "char-split",
    "n_results": 10
  }'
```

### Step 4: Vector Search
```bash
# Search relevant document chunks
curl -X POST "http://localhost:8002/query"   -H "Content-Type: application/json"   -d '{
    "query": "resistance training for beginners",
    "method": "char-split",
    "n_results": 5
  }'
```
