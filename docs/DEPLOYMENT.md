# 🚀 Vectronyx AI Workbench — Production Deployment Guide

This guide provides end-to-end instructions for deploying **Vectronyx AI Workbench** to production across multiple platforms.

---

## 📑 Deployment Options Overview

| Target Platform | Architecture | Free Tier Available? | Best For |
| :--- | :--- | :--- | :--- |
| **Hugging Face Spaces + Vercel** | Backend on HF Spaces (`space_app.py` Gradio/FastAPI mount), Frontend on Vercel Edge | ✅ Yes (Free HF Gradio Space + ZeroGPU) | **Primary recommended architecture** |
| **Render + Vercel** | Backend on Render, Frontend on Vercel Edge | ✅ Yes | Alternative PaaS deployment |
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

## Option 1: Hugging Face Spaces (Backend) + Vercel (Frontend) [Primary]

> [!IMPORTANT]
> **Supabase IPv4 Note for Hugging Face Spaces:** HF Spaces containers only support outbound IPv4 networking. In Supabase **Connect → Session Pooler** (or Transaction Pooler), copy the IPv4 Pooler connection string (e.g., `aws-0-<region>.pooler.supabase.com:5432`) for `DATABASE_URL` instead of the direct `db.<ref>.supabase.co` hostname.

### Step 1: Deploy Backend to Hugging Face Spaces

> [!NOTE]
> Free Hugging Face accounts cannot create `cpu-basic` Docker Spaces (`402 Payment Required`). Therefore, the HF Space deployment runs [`backend/space_app.py`](../backend/space_app.py) using `sdk: gradio` (mounting the full FastAPI API at `/`, `/health`, `/auth/*`, `/api/*`, and Gradio at `/ui`), while keeping [`backend/Dockerfile`](../backend/Dockerfile) for Docker/Render/Cloud Run deployments.

#### A. Instant CLI Deploy (Recommended)
1. Log in with the Hugging Face CLI:
   ```bash
   hf auth login
   ```
2. Run the deployment script from the repository root (targets the HF Gradio Space, uploads `backend/` without `Dockerfile`, and optionally syncs secrets from `.env`):
   ```bash
   python scripts/deploy_hf_space.py --space-id <your-hf-username>/vectronyx-backend --sync-env
   ```
   *(Pass `--sdk docker` if deploying to an HF Pro `cpu-basic` Docker Space.)*
3. Your backend builds automatically and goes live at:
   `https://<your-hf-username>-vectronyx-backend.hf.space`
   Verify health at `https://<your-hf-username>-vectronyx-backend.hf.space/health`.

#### B. Automatic GitHub Actions Sync
1. In your GitHub repo **Settings → Secrets and variables → Actions**:
   - Add Secret: `HF_TOKEN` (Hugging Face Write access token)
   - Add Variable: `HF_SPACE_ID` (e.g. `<your-hf-username>/vectronyx-api`)
2. Push to `main` (or manually trigger **Deploy Backend to Hugging Face Space** in GitHub Actions).
3. In the Hugging Face Space **Settings → Variables and secrets**, ensure your runtime secrets (`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_PUBLISHABLE_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `SECRET_KEY`) are configured.

### Step 2: Deploy Frontend to Vercel
1. Sign in to [Vercel](https://vercel.com) and click **Add New** → **Project**.
2. Import your `Vectronyx` GitHub repository.
3. Vercel automatically detects [`vercel.json`](../vercel.json) (or [`frontend/vercel.json`](../frontend/vercel.json) if you set **Root Directory** to `frontend`).
4. Add Environment Variables in Vercel Project Settings:
   - `VITE_API_URL` = `https://<your-hf-username>-vectronyx-backend.hf.space`
   - `VITE_SUPABASE_URL` = `https://your-project.supabase.co`
   - `VITE_SUPABASE_PUBLISHABLE_KEY` = `sb_publishable_...`
   - `VITE_GEMINI_MODEL` = `gemini-3.5-flash-lite`
   - `VITE_GROQ_MODEL` = `openai/gpt-oss-120b`
5. Click **Deploy**.
6. In Supabase **Authentication → URL Configuration**, add your production Vercel domain (`https://<your-app>.vercel.app/**`) to **Redirect URLs** and **Site URL**.

---

## Option 2: Render (Backend) + Vercel (Frontend)

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

## Option 3: Unified Single Container (Render / Railway / Google Cloud Run / Fly.io)

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

## Option 4: Self-Hosted / VPS with Docker Compose

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

