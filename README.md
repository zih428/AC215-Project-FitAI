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
- `data/raw/` → raw CSV datasets

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

### Shut down and remove containers (when finished)
```bash
docker compose down -v
```
