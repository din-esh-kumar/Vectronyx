---
title: Vectronyx AI Workbench API
emoji: ⚡
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 6.30.0
python_version: "3.11"
app_file: space_app.py
pinned: false
license: mit
short_description: FastAPI AI Workbench API (Gemini + Groq + pgvector)
---

# Vectronyx AI Workbench — Backend API (Hugging Face Space)

Production FastAPI backend for **Vectronyx AI Workbench**, served on Hugging Face Spaces via `space_app.py` (with Gradio mounted at `/ui` and Docker support in `Dockerfile`).

## Health & Docs Endpoints
- `GET /health` — Service health probe
- `GET /docs` — Interactive OpenAPI / Swagger documentation
- `GET /ui` — Gradio status panel
- `POST /api/analyst/generate-dashboard/stream` — SSE Data Analyst Engine
- `POST /api/research/stream` — SSE Autonomous ReAct Research Agent
- `GET /api/memory/status` — Contextual Vector Memory & Embedding Diagnostics

## Required Space Secrets
Configure the following in **Space Settings → Variables and secrets**:
- `DATABASE_URL` (Use Supabase IPv4 Supavisor Pooler URI for HF Spaces compatibility)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_PUBLISHABLE_KEY`
- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `SECRET_KEY`

