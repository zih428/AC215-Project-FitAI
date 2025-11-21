# FitAI Application Design Document

## Overview
- FitAI delivers evidence-backed fitness guidance through a containerized stack spanning ingestion (OCR), storage (GCS + Postgres), retrieval (Chroma + RAG service), modeling (Vertex AI fine-tuned Gemini), and user experience (Next.js frontend).
- Core user flows: upload or browse literature → chunk/embed into Chroma → chat via RAG-backed AI Coach → optionally sync calendar availability and save personalized plans to Postgres.

## Solution Architecture
- User flows
  - Web client (Next.js) calls `rag-service` for chat/query and `core-etl-api` for authentication, profile, and saved plans. Calendar uploads are sent to `calendar-agent`.
  - `rag-service` retrieves literature text from Chroma, composes prompts with optional user profile, and calls the tuned Gemini endpoint hosted on Vertex.
  - `ocr-engine` streams PDFs from GCS (`raw-literature/`), performs OCR, and writes cleaned text back to GCS (`processed-literature/`).
  - `core-etl-api` exposes CRUD/auth for user profiles and interacts with Postgres; the same profiles can be reused by `calendar-agent` and passed into RAG.
  - `calendar-agent` OCRs a schedule image (GPT-4o Vision) or uses stored availability, fuses it with a user profile, and generates a training plan via OpenAI; optionally persists the plan to Postgres.
- Data flow (literature/RAG)
  1) PDFs land in GCS → 2) OCR text saved in `processed-literature/` → 3) `rag-service` chunks text (character/recursive/semantic) → 4) embeddings generated with Vertex text-embedding-004 → 5) stored in Chroma collections (per chunking method) → 6) queries embed user input → 7) top-k context passed to tuned Gemini endpoint for grounded answers.
- Data flow (user/calendars)
  1) Profile/auth via `core-etl-api` (Postgres) → 2) optional calendar image to `calendar-agent` → 3) availability + goals drive plan generation → 4) optional persistence back to Postgres.

## Component Responsibilities
- `services/frontend` (Next.js 14, TypeScript, Tailwind): AI Coach chat UI, profile loading, local message caching, connectivity checks to RAG and pipeline APIs, sidebar navigation to dashboard/calendar.
- `services/rag-service` (FastAPI): GCS text ingest, configurable chunking, embedding generation via Vertex, Chroma persistence/query, chat orchestration with tuned Gemini endpoint (`GENERATIVE_MODEL` in `rag_core.py`).
- `services/ocr-engine` (FastAPI): incremental or full-batch OCR of GCS PDFs using a custom `OCR` class; streams bytes, avoids local disk writes.
- `services/core-etl-api` (FastAPI + SQLAlchemy): JWT auth, user CRUD, ETL runners, and typed payload validation; uses Postgres for persistence.
- `services/calendar-agent` (FastAPI): calendar OCR + planning endpoints that combine Postgres user profiles with OpenAI model calls; supports optional persistence of generated plans.
- Data stores: Postgres (`services/db`) for users/plans; Chroma for vector search; GCS bucket `gs://fitai-data-bucket` for raw/processed literature and SFT datasets.

## Technical Architecture
High-level architecture overview:

![Technical architecture overview](technical-architecture.jpeg)

- APIs & patterns: REST over HTTP between services; Pydantic models for validation; modular “api_*” functions in `rag_core.py` for testability; JWT-based auth in `core-etl-api`.
- ML stack: Vertex AI text-embedding-004 for vectorization; Gemini 2.0 Flash fine-tuned via Vertex SFT as the RAG generator; optional OpenAI GPT-4o in `calendar-agent` for vision + plan generation.
- Data processing: LangChain splitters (character/recursive) and custom semantic splitter; SHA256-based deterministic IDs for Chroma docs; exponential backoff on embedding calls.
- Frontend: Next.js App Router, client-side storage for chat history/profile cache, and environment-driven API endpoints; Tailwind styling with shared layout/sidebar.
- Deployment: Docker images per service orchestrated by `docker-compose.yml`; service account credentials mounted read-only; CORS configured for localhost dev; persistent volumes for Postgres and Chroma.
- Observability & durability: container logs for diagnostics; Chroma persisted on host volume; GCS + DVC maintain literature and SFT dataset lineage.

## User Interface & Features
- Authentication & session state: `/login` supports login/register against `core-etl-api` (`/auth/login`, `/auth/register`); tokens cached in localStorage + cookie, and prior chat/plan caches are cleared on account switch to avoid cross-user leakage.
- Profile management: `/profile` loads/saves the typed fitness profile (name, height/weight, body type, gender, age, goal) via `/users/me` with JWT; optimistic caching, form validation, and lock/unlock toggle prevent accidental edits.
- RAG chatbot (AI Coach): `/ai-coach` chats against `rag-service` `/chat`, shows connection/collections status, caches message history locally, and injects the saved profile when available for personalized answers; debug toggles expose method/context metadata.
- Personalized planning with calendar context: `/training-plan` calls `calendar-agent` `/planner` with optional PNG/JPG calendar upload; shows parsed calendar JSON, allows saving plans (`/planner/save`), and reloads history (`/planner/history`) while guarding against unsaved-plan loss. `/weekly-plan` pulls saved plans from `core-etl-api` (`/training-plans`), generates new weeks via `calendar-agent`, and supports ICS download/preview plus user instructions for the planner.
