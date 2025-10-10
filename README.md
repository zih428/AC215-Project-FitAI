# AC215-Project-FitAI

Fall 2025 **AC 215** course project.  
FitAI is a containerized system for generating personalized fitness recommendations using LLM & RAG.

---

## 👩‍💻 Authors
- Leo Cheng
- Faye Fang  
- Steven Ge  
- Harry Hu

---

## 📦 Project Structure
- `services/db/` → main Postgres database (with initialization schema `init.sql`)
- `services/pipeline/` → ETL service (loads raw CSVs into the database & scientific literature into vector db)
- `services/ml/` → ML service (model + plan generation API)
- `services/frontend/` → Next.js app (user interface)
- `services/rag_pipeline/` → Rag service (with ChromaDB volume track)

---

## Raw datasets are stored on GCS

---

## 🚀 Quick Start

### 1. Run all containers
```bash
docker compose up --build -d
```

### 2. Ingest raw data into the database
```bash
curl -X POST http://localhost:8001/run-etl
```

### 3. Using OCR Preprocessed Literature pdfs
**Default mode (process only unprocessed PDFs):**
```bash
curl -X POST "http://localhost:8003/perform-ocr"
# equivalent (explicit):
# curl -X POST "http://localhost:8003/perform-ocr?full_process=false"
```
**Full-process mode (re-process all PDFs in raw-literature):**
```bash
curl -X POST "http://localhost:8003/perform-ocr?full_process=true"
```
You should get a quick acknowledgement while the job runs in the background:
```json
{"status":"started","message":"OCR job running in background"}
```

### Shut down and remove containers (when finished)
```bash
docker compose down -v
```




---

## 📊 Process txt from GCS and load to ChromaDB 

---
```bash
docker-compose up -d
```

```bash
docker-compose ps # Check service status
```
### 🧐 API 1 & 2  -> Test Health  & Check ChromaDB collections 
```bash
curl http://localhost:8002/health

curl http://localhost:8002/collections
```
### ⚙️ API 3 Process txt file in GCS
```bash
curl -X POST "http://localhost:8002/process-gcs" \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "fitai-data-bucket",
    "folder_path": "fitness-docs/",
    "method": "char-split"
  }'
```
**Parameter Explaination**:
- `bucket_name`: GCS bucket name
- `folder_path`: （leave it empty '' means root path）
- `method`: chunking method (`char-split`, `recursive-split`, `semantic-split`)

---

## 💬 Interaction with it through chat or query 

---

### 🤖 API 4 Chat
```bash
curl -X POST "http://localhost:8002/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main findings about resistance training progression?",
    "method": "char-split",
    "n_results": 10
  }'
```

### 🔍 API 5 Query
```bash
curl -X POST "http://localhost:8002/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "resistance training for beginners",
    "method": "char-split",
    "n_results": 5
  }'
```
