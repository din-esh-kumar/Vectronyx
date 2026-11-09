# 🚀 Vectronyx AI Workbench — Production Deployment Guide

This guide provides end-to-end instructions for deploying **Vectronyx AI Workbench** to production across multiple platforms.

---

## 📑 Deployment Options Overview

| Target Platform | Architecture | Free Tier Available? | Best For |
| :--- | :--- | :--- | :--- |
| **Render + Vercel** | Backend on Render, Frontend on Vercel Edge | ✅ Yes | **Recommended for production & teams** |
| **Railway** | Single or dual service from repo | ✅ Yes (Trial/Hobby) | Fast 1-click Git deployment |
| **Docker Compose** | Multi-container with Nginx reverse proxy | Self-hosted | VPS, AWS EC2, DigitalOcean, Hetzner |
| **Unified Single Container**| Unified FastAPI + React SPA (`Dockerfile`) | Cloud Run / Fly.io / Render | Zero-CORS, single URL deployment |

---

## 📋 Pre-Deployment Checklist

Ensure your cloud accounts and environment variables are ready:

### 1. Supabase (Database & Storage)
- Ensure your Supabase project is active.
- Verify the `datasets` storage bucket is created with appropriate access policies.
- Run database migrations:
  ```bash
  cd backend
  alembic upgrade head
  ```

### 2. Required Production Environment Variables

| Variable | Description |
| :--- | :--- |
| `DATABASE_URL` | Supabase PostgreSQL direct connection string |
| `SUPABASE_URL` | Supabase project URL (`https://<ref>.supabase.co`) |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role secret |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase anon public key |
| `SUPABASE_STORAGE_BUCKET` | `datasets` |
| `SECRET_KEY` | Secure random string (e.g., `openssl rand -hex 32`) |
| `GEMINI_API_KEY` | Google Gemini API key |
| `GROQ_API_KEY` | Groq Cloud API key |
| `ALLOWED_ORIGINS` | Your frontend production URL (or `*`) |
| `VITE_API_URL` | Production backend URL (e.g. `https://vectronyx-api.onrender.com`) |
| `VITE_SUPABASE_URL` | Same as `SUPABASE_URL` |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Same as `SUPABASE_PUBLISHABLE_KEY` |

---

## Option 1: Render (Backend) + Vercel (Frontend) [Recommended]

### Step 1: Deploy Backend to Render
1. Push your repository to GitHub.
2. Sign in to [Render](https://render.com) and click **New +** → **Blueprint** (or **Web Service**).
3. Connect your `Vectronyx` repository.
4. Render will automatically detect [`render.yaml`](../render.yaml):
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.middleware.app:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`
5. Supply your secret environment variables in the Render Dashboard (`DATABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`).
6. Click **Deploy**. Once finished, copy your Render backend URL (e.g. `https://vectronyx-backend.onrender.com`).

### Step 2: Deploy Frontend to Vercel
1. Sign in to [Vercel](https://vercel.com) and click **Add New** → **Project**.
2. Select your `Vectronyx` repository.
3. Configure project settings:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Vite`
   - **Build Command**: `pnpm run build`
   - **Output Directory**: `dist`
4. Add Environment Variables:
   - `VITE_API_URL` = `https://your-render-backend.onrender.com`
   - `VITE_SUPABASE_URL` = `https://your-project.supabase.co`
   - `VITE_SUPABASE_PUBLISHABLE_KEY` = `sb_publishable_...`
   - `VITE_GEMINI_MODEL` = `gemini-3.5-flash-lite`
   - `VITE_GROQ_MODEL` = `openai/gpt-oss-120b`
5. Click **Deploy**. Vercel will build and serve your app globally with instant edge cache.

---

## Option 2: Unified Single Container (Render / Railway / Google Cloud Run / Fly.io)

Vectronyx includes a root [`Dockerfile`](../Dockerfile) that builds both the React frontend and FastAPI backend into a single container. The backend automatically serves the compiled SPA at `/` with SPA route fallback, `/api` for REST, and `/health` for monitoring.

### Deploy to Railway
1. Sign in to [Railway](https://railway.app).
2. Click **New Project** → **Deploy from GitHub repo** → select `Vectronyx`.
3. Railway automatically detects `Dockerfile` or `railway.json`.
4. In the service settings, add your `.env` variables.
5. Railway assigns a public domain with automatic SSL.

### Deploy to Google Cloud Run
```bash
# 1. Build and push to Google Artifact Registry
gcloud builds submit --tag gcr.io/[PROJECT_ID]/vectronyx:latest .

# 2. Deploy to Cloud Run
gcloud run deploy vectronyx \
  --image gcr.io/[PROJECT_ID]/vectronyx:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production,PORT=8000
```

---

## Option 3: Self-Hosted / VPS with Docker Compose

For deploying to your own server (Ubuntu / Debian / AWS EC2 / DigitalOcean Droplet):

1. Clone the repository onto your server:
   ```bash
   git clone https://github.com/din-esh-kumar/Vectronyx.git
   cd Vectronyx
   ```

2. Copy and configure `.env`:
   ```bash
   cp .env.example .env
   nano .env
   ```

3. Start services in detached mode:
   ```bash
   docker compose up -d --build
   ```

4. Check running containers and health status:
   ```bash
   docker compose ps
   ```
   Both `vectronyx-backend` and `vectronyx-frontend` will report `healthy`.

5. Access the application:
   - Frontend UI: `http://<server-ip>:5173` (or `http://<server-ip>:80` if mapped)
   - Backend API: `http://<server-ip>:8000`
   - Healthcheck: `http://<server-ip>:8000/health`
