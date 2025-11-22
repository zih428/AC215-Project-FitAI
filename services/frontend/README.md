# FitAI Frontend (Next.js 14 + Tailwind)

Next.js 14 / TypeScript UI for the FitAI platform. It handles user auth/profile management, chat with the RAG backend, and planner flows powered by the calendar agent.

## Key screens and dependencies
- `/ai-coach` (default landing): Chat UI that pings `rag-service` at `http://localhost:8002/health`, `.../collections`, and `.../chat`. Requires at least one RAG collection and a saved profile to send messages.
- `/login`: Register/login against `core-etl-api` and cache the JWT + profile in `localStorage` and a cookie.
- `/profile`: View/update the authenticated profile via `core-etl-api` (`/users/me`). Profile data is also cached for other pages.
- `/training-plan`: Upload an optional calendar image to `calendar-agent` (`/planner`), generate a plan, and view/save history (`/planner/history`).
- `/weekly-plan`: Fetch and download weekly ICS plans from `calendar-agent`.
- `/workouts`: Static sample cards.
- `/` redirects to `/ai-coach`.

## Prerequisites
- Node 18+ (matches the Dockerfile).
- Backend services reachable (default ports from `docker-compose.yml`): `core-etl-api` (8001), `rag-service` (8002), `calendar-agent` (8004). CORS is already open for localhost.

## Environment variables
Create `.env.local` or export before running:
```
NEXT_PUBLIC_PIPELINE_URL=http://localhost:8001      # core-etl-api for auth/profile
NEXT_PUBLIC_CALENDAR_AGENT_URL=http://localhost:8004 # calendar-agent for plans
```

The AI Coach endpoints for `rag-service` are currently hardcoded to `http://localhost:8002` in `app/ai-coach/page.tsx`; adjust there if deploying to a different host/port.

## Local development
```bash
cd services/frontend
npm install
npm run dev
# app runs at http://localhost:3000
```

Lint/build:
```bash
npm run lint
npm run build
npm start   # serves the production build
```

## Run with Docker (from repo root)
```bash
docker compose up -d frontend          # starts frontend (depends on other services already running)
# or bring up everything
docker compose up -d
```
Image-only flow:
```bash
docker build -t fitai-frontend .
docker run -p 3000:3000 fitai-frontend
```

## Project structure
```
app/
  ai-coach/        # RAG chat UI
  login/           # auth/register flow
  profile/         # profile editor (requires JWT)
  training-plan/   # calendar upload + planner history
  weekly-plan/     # ICS downloads / weekly view
  workouts/        # placeholder workouts
  layout.tsx       # shell + sidebar
  globals.css      # Tailwind/global styles
components/
  Sidebar.tsx
public/            # favicon, assets
```
