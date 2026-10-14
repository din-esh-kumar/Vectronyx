# Vectronyx AI Workbench — Getting Started Guide

This guide walks you through setting up, configuring, and launching the full **Vectronyx AI Workbench** stack on your local machine or server.

---

## 1. System Prerequisites

Ensure you have the following installed on your machine before starting:

| Tool | Minimum Version | Purpose |
| :--- | :--- | :--- |
| **Node.js** | `>= 20.x LTS` | Frontend runtime environment |
| **pnpm** | `>= 9.12.x` | Fast, disk-efficient package manager |
| **Python** | `3.10` or `3.11` | Backend runtime & AI pipeline |
| **Docker & Compose** | Docker 24+ / Compose v2 | Containerized local orchestration |
| **Git** | `2.x+` | Version control |

> [!NOTE]
> For Windows environments running native Python, ensure **Microsoft C++ Build Tools** (Visual Studio Installer) are installed if compiling native dependencies like `faiss-cpu`.

---

## 2. Repository Cloning & Structure

Clone the repository to your local workspace:

```bash
git clone https://github.com/din-esh-kumar/Vectronyx.git
cd Vectronyx
```

The workspace is organized into clear service boundaries:
```
Vectronyx/
├── backend/          # FastAPI server, AI modules, DB models, migrations
├── frontend/         # React 18, Vite, Tailwind CSS v4, TypeScript
├── infra/            # Docker Compose, Nginx reverse proxy configs
├── vector_store/     # Persistent FAISS vector indexes
├── data/             # Uploaded datasets and analytical scratchpads
└── docs/             # Technical guides and API specifications
```

---

## 3. Environment Configuration

### 3.1 Backend Configuration (`backend/.env`)

Duplicate the sample template into an active `.env` file:

```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` and supply your credentials:

```dotenv
# General Application
APP_NAME=Vectronyx AI Workbench
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=True
PORT=8000

# Database & Supabase
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
SUPABASE_KEY=your_supabase_service_role_key_here
SUPABASE_PUBLISHABLE_KEY=your_supabase_publishable_anon_key_here

# Supabase Cloud Storage & pgvector
SUPABASE_STORAGE_BUCKET=datasets
VECTOR_STORE_PROVIDER=supabase_pgvector
VECTOR_DIMENSION=768

# JWT Security
SECRET_KEY=your_super_secret_jwt_key_change_this_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Cloud LLM — Google Gemini (Primary for Reasoning & 1M Context)
GEMINI_API_KEY=your_free_google_ai_studio_key_here
GEMINI_MODEL=gemini-3.5-flash-lite

# Cloud LLM — Groq Cloud (Ultra-Fast LPU Chat & Tool Calling)
LLM_PROVIDER=gemini
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b

# Research Agent Parameters
MAX_SEARCH_RESULTS=5
MAX_SCRAPE_DEPTH=2

# CORS Whitelist
ALLOWED_ORIGINS=http://localhost:5173
```

### 3.2 Frontend Configuration (`frontend/.env`)

Inspect or update `frontend/.env`:

```dotenv
VITE_GRAPHQL_URL=http://localhost:8000/graphql
VITE_SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=[YOUR-SUPABASE-PUBLISHABLE-KEY]
```

---

## 4. Launching the Platform

### Method A: Docker Compose (Recommended)

Docker Compose orchestrates both services with volume mounts, enabling live code reload.

1. **Build and start all containers**:
   ```bash
   cd infra
   docker compose up --build
   ```

2. **Verify running containers**:
   ```bash
   docker compose ps
   ```

3. **Access Services**:
   - 🌐 **Frontend UI**: [http://localhost:5173](http://localhost:5173)
   - ⚡ **Backend API**: [http://localhost:8000](http://localhost:8000)
   - 🔍 **Interactive GraphQL Explorer**: [http://localhost:8000/graphql](http://localhost:8000/graphql)

---

### Method B: Native Local Development

If you prefer running services directly on your host machine without Docker:

#### 1. Start the Backend (FastAPI)

```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start Uvicorn development server
uvicorn app.middleware.app:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Start the Frontend (Vite)

In a separate terminal:

```bash
cd frontend

# Enable pnpm if not already active
corepack enable
corepack prepare pnpm@9.12.2 --activate

# Install npm dependencies
pnpm install

# Start Vite dev server
pnpm run dev
```

Navigate to `http://localhost:5173` in your browser.

---

## 5. Verification Checklist

Run these quick checks to ensure everything is operating smoothly:

1. **Backend Health Check**:
   ```bash
   curl http://localhost:8000/
   # Expected response: {"message": "Backend running "}
   ```

2. **Supabase Connection**:
   - Open `http://localhost:5173/login`.
   - Toggle to **Create account** and register a test user.
   - Confirm the user is created and redirected to the dashboard.

3. **Frontend Hot Module Replacement (HMR)**:
   - Edit any text in `frontend/src/features/dashboard/Dashboard.tsx`.
   - Observe instantaneous browser updates without page reloads.

---

## 6. Troubleshooting Common Pitfalls

| Issue | Probable Cause | Resolution |
| :--- | :--- | :--- |
| **`app.main:app` module not found in Docker** | `Dockerfile` points to `app.main:app` while app is in `app.middleware.app`. | Update `CMD` in `backend/Dockerfile` to `uvicorn app.middleware.app:app --host 0.0.0.0 --port 8000` or create `backend/app/main.py`. |
| **Supabase Client Initialisation Failure** | Missing or invalid `SUPABASE_URL` or keys in `.env`. | Verify keys in `backend/.env` and `frontend/.env`. Ensure you use the **anon/publishable** key in frontend and **service_role** key in backend. |
| **FAISS installation error on Windows** | Missing C++ build tools for native compilation. | Use `pip install faiss-cpu==1.8.0` with pre-compiled wheels, or run inside Docker. |
| **CORS blocked by browser** | Origin `http://localhost:5173` is not allowed. | Ensure `ALLOWED_ORIGINS` in `backend/.env` contains `http://localhost:5173` and backend CORS middleware is configured. |
| **`pnpm` command not found** | Node.js `corepack` is not enabled. | Run `npm install -g pnpm` or `corepack enable`. |
