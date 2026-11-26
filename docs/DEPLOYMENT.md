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
| `NVIDIA_API_KEY` | NVIDIA NIM API key (`nvapi-...`) for multi-provider inference |
| `NVIDIA_BASE_URL` | `https://integrate.api.nvidia.com/v1` |
| `NVIDIA_MODEL` | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` |
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

#### B. Production GitHub Actions CI/CD & DevOps Pipeline Suite
The repository ships a complete production DevOps automation suite under [`.github/`](../.github/):

| Workflow | Trigger | Responsibilities |
| :--- | :--- | :--- |
| [**`ci-cd.yml`**](../.github/workflows/ci-cd.yml) | PR to `main`, Push to `main`, `workflow_dispatch` | Secret & manifest scan → Frontend CI (typecheck, Vite build, bundle size budget, JS secret audit) + Backend CI (Ruff static analysis, `compileall`, Alembic single-head check, offline `pytest` + coverage) → PR Vercel Preview deploy & comment → Optional Alembic DB migrations → Auto-Deploy Backend (HF Spaces + optional Render hook) & Staged Zero-Downtime Vercel Frontend (`--skip-domain` → smoke test → `vercel promote`) → Post-Deploy live contract verification ([`scripts/verify_deployment.py`](../scripts/verify_deployment.py)) → Optional Slack/Discord webhook alert. |
| [**`security.yml`**](../.github/workflows/security.yml) | PR, Push to `main`, Weekly Monday 04:00 UTC | Vectronyx secret scan + Gitleaks full history scan, CodeQL SAST (Python + JS/TS) uploaded to GitHub Security, `pip-audit` + `pnpm audit --prod`, and Trivy Dockerfile/IaC misconfiguration scan (SARIF). |
| [**`docker.yml`**](../.github/workflows/docker.yml) | PR (infra/deps), Push to `main`, `v*.*.*` tags | Multi-target Buildx verification & GHCR publishing (`vectronyx`, `vectronyx-backend`, `vectronyx-frontend`) with GHA layer caching, OCI metadata tags, SBOM + GitHub Build Provenance Attestations, and Trivy CVE container scans. |
| [**`uptime-monitor.yml`**](../.github/workflows/uptime-monitor.yml) | Every 6 hours (`cron: 0 */6 * * *`), manual | Synthetic live production probe (also keeps free HF Spaces warm before 48h sleep). Automatically opens/updates a `production` + `incident` GitHub Issue on outage and auto-closes it on recovery. |
| [**`rollback.yml`**](../.github/workflows/rollback.yml) | `workflow_dispatch` | One-click emergency rollback: restores HF Spaces backend to any Git SHA/tag, executes instant `vercel rollback` for the frontend, verifies live endpoints post-rollback, and writes an audit summary. |
| [**`release.yml`**](../.github/workflows/release.yml) | Push of `v*.*.*` tags, manual | Runs secret gate, builds frontend bundle tarball + SHA256 checksums, and creates a categorized GitHub Release (configured via [`.github/release.yml`](../.github/release.yml)). |
| [**`pr-hygiene.yml`**](../.github/workflows/pr-hygiene.yml) | Pull Requests | Enforces Conventional Commit PR titles, auto-labels PRs via [`.github/labeler.yml`](../.github/labeler.yml), and reports PR review size. |

Repository automation configs also include [`.github/dependabot.yml`](../.github/dependabot.yml) (weekly grouped updates for `pip`, `npm`, `github-actions`, and `docker`), [`.github/CODEOWNERS`](../.github/CODEOWNERS), PR template, and structured Issue templates.

**GitHub Repository Configuration** (**Settings → Secrets and variables → Actions**):
- **Required Secret for Backend Auto-Deploy**:
  - `HF_TOKEN` — Hugging Face Write access token for auto-deploying to HF Spaces.
- **Optional Secrets** *(enable additional DevOps automation as needed)*:
  - `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` — enables CI PR preview deployments, zero-downtime staged production promotes (`vercel deploy --prebuilt --prod --skip-domain` → verify → `vercel promote`), and one-click `rollback.yml` frontend rollbacks (when omitted, Vercel's native GitHub integration handles deploys automatically).
  - `VERCEL_AUTOMATION_BYPASS_SECRET` — allows post-deploy verification to probe Deployment Protection-gated preview/staged URLs.
  - `DATABASE_URL` — enables automated `alembic upgrade head` migrations before backend deploy (when `AUTO_RUN_MIGRATIONS=true` or manual `run_migrations` input is checked).
  - `RENDER_DEPLOY_HOOK_URL` — optionally triggers a secondary Render backend deploy on `main`.
  - `DEPLOY_WEBHOOK_URL` — Slack or Discord incoming webhook URL for deployment and outage alerts.
  - `NVIDIA_API_KEY` *(optional)* — NVIDIA NIM API key (`nvapi-...`), automatically synced to the HF Space during CI deploy.
  - `GEMINI_API_KEY`, `GROQ_API_KEY` *(optional)* — LLM keys automatically synced to the HF Space during CI deploy when configured in GitHub Secrets.
- **Optional Variables**:
  - `HF_SPACE_ID` *(defaults to `din-esh-kumar/vectronyx-backend`)*
  - `HF_SPACE_SDK` *(defaults to `gradio`; set `docker` for HF Pro Docker Spaces)*
  - `FRONTEND_URL` *(defaults to `https://vectronyx.vercel.app`)*
  - `AUTO_RUN_MIGRATIONS` *(set `true` to run Alembic migrations automatically on `main` pushes)*
  - `LLM_PROVIDER`, `NVIDIA_BASE_URL`, `NVIDIA_MODEL`, `GEMINI_MODEL`, `GROQ_MODEL` *(synced to HF Space during CI deploy)*
  - `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, `VITE_GEMINI_MODEL`, `VITE_GROQ_MODEL`

> [!TIP]
> Enable GitHub Branch Protection on `main` requiring **`Security & Secret Scan`**, **`Frontend CI (Typecheck, Build & Bundle Audit)`**, and **`Backend CI (Lint, Compile, Migrations & Tests)`**, and configure a **`production`** GitHub Environment under **Settings → Environments** if you want manual approval gates or deployment history tracking.

In Hugging Face Space **Settings → Variables and secrets**, ensure your runtime secrets (`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_PUBLISHABLE_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `NVIDIA_API_KEY`, `SECRET_KEY`) and variables (`LLM_PROVIDER`, `NVIDIA_BASE_URL`, `NVIDIA_MODEL`, `GEMINI_MODEL`, `GROQ_MODEL`) are configured.

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

