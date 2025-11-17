# Frontend (Next.js)

FitAI Smart Fitness Platform - Frontend application built with Next.js 14, TypeScript, and Tailwind CSS.

## Features

- **Dashboard**: Overview of fitness journey and progress
- **AI Coach**: Chat interface powered by RAG pipeline for personalized fitness advice
- **Calendar**: Schedule and manage workouts
- **Sidebar Navigation**: Easy access to all platform features

## Getting Started

### Install Dependencies

```bash
npm install
```

### Development Mode

```bash
npm run dev
```

The application will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── app/
│   ├── ai-coach/      # AI Coach chat interface
│   ├── calendar/      # Calendar and workout scheduling
│   ├── layout.tsx     # Root layout with sidebar
│   ├── page.tsx       # Dashboard page
│   └── globals.css    # Global styles
├── components/
│   └── Sidebar.tsx    # Navigation sidebar component
└── package.json
```

## API Integration

The AI Coach page integrates with the RAG service at `http://localhost:8002/chat` endpoint.

## Docker

To run with Docker:

```bash
docker build -t fitai-frontend .
docker run -p 3000:3000 fitai-frontend
```
