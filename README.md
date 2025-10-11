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

## 📦 Container Structure
- `services/ocr_engine/` → OCR service that processes literatures from pdf to txt
- `services/rag_pipeline/` → RAG pipeline that handles literature chunking & Chroma insertion
- `services/chromadb/` → Chroma vector database
- (Optional for milestone 2) `services/db/` → main Postgres database (with initialization schema `init.sql`)
- (Optional for milestone 2) `services/pipeline/` → ETL service (loads raw CSVs into the Postgres)
- (Optional for milestone 2) `services/frontend/` → Next.js app (user interface)

---

## Raw datasets are stored on GCS

---

## 🚀 Quick Start

### Run all containers
```bash
docker compose up --build -d
```

---

## (Optional) Exercise catalog & tracking raw data pipeline
### (Optional, not needed for RAG or milestone 2) Ingest raw data into the database
```bash
curl -X POST http://localhost:8001/run-etl
```

---

## OCR engine service

### Use OCR to preprocess phyisology literature from pdf to txt
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

---

## RAG pipeline service

### Chunk txt files and insert into Chroma
```bash
curl -X POST "http://localhost:8002/process-gcs" \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "fitai-data-bucket",
    "folder_path": ~~"fitness-docs/"~~,
    "method": "char-split"
  }'
```
**Parameter Explaination**:
- `bucket_name`: GCS bucket name
- `folder_path`: （leave it empty '' means root path）
- `method`: chunking method (`char-split`, `recursive-split`, `semantic-split`)

### Check ChromaDB collections 
```bash
curl http://localhost:8002/collections
```

### 5. Chat
```bash
curl -X POST "http://localhost:8002/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main findings about resistance training progression?",
    "method": "char-split",
    "n_results": 10
  }'
```

### 6. Query
```bash
curl -X POST "http://localhost:8002/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "resistance training for beginners",
    "method": "char-split",
    "n_results": 5
  }'
```

---

### Shut down and remove containers (when finished)
```bash
docker compose down -v
```
