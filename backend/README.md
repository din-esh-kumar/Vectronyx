---
title: Vectronyx AI Workbench API
emoji: ⚡
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: FastAPI AI Workbench API (Gemini + Groq + pgvector)
---

# Vectronyx AI Workbench — Backend API (Hugging Face Space)

Production FastAPI backend for **Vectronyx AI Workbench**, deployed via Docker on Hugging Face Spaces.

## Health & Docs Endpoints
- `GET /health` — Service health probe
- `GET /docs` — Interactive OpenAPI / Swagger documentation
- `POST /api/analyst/generate-dashboard/stream` — SSE Data Analyst Engine
- `POST /api/research/stream` — SSE Autonomous ReAct Research Agent
- `GET /api/memory/health` — Contextual Vector Memory Engine

## Required Space Secrets
Configure the following in **Space Settings → Variables and secrets**:
- `DATABASE_URL` (Use Supabase IPv4 Supavisor Pooler URI for HF Spaces compatibility)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_PUBLISHABLE_KEY`
- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `SECRET_KEY`

