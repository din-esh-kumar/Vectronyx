# Vectronyx AI Workbench ⚡

<p align="center">
  <strong>An autonomous, privacy-conscious AI workstation integrating contextual semantic memory, deep research agents, and tabular data intelligence.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React-18.3.1-61DAFB?logo=react&logoColor=black" alt="React 18" />
  <img src="https://img.shields.io/badge/TypeScript-5.5-3178C6?logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC?logo=tailwindcss&logoColor=white" alt="Tailwind CSS v4" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/GraphQL-Strawberry-E10098?logo=graphql&logoColor=white" alt="Strawberry GraphQL" />
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white" alt="Python 3.11" />
  <img src="https://img.shields.io/badge/Vector_Store-FAISS-blue" alt="FAISS" />
  <img src="https://img.shields.io/badge/LLM-Groq_%2F_Ollama-FF6B6B" alt="LLM" />
  <img src="https://img.shields.io/badge/Database-Supabase_%2F_PostgreSQL-3ECF8E?logo=supabase&logoColor=white" alt="Supabase" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker" />
  <a href="./CODE_OF_CONDUCT.md"><img src="https://img.shields.io/badge/Contributor_Covenant-v2.1-orange.svg" alt="Contributor Covenant" /></a>
</p>

---

## 📑 Table of Contents

- [Executive Summary](#-executive-summary)
- [System Architecture & Core Mechanics](#-system-architecture--core-mechanics)
- [Principal Engineering Highlights](#-principal-engineering-highlights)
- [Core AI Engines](#-core-ai-engines)
  - [1. Contextual Memory System](#1-contextual-memory-system)
  - [2. Autonomous Research Agent](#2-autonomous-research-agent)
  - [3. Intelligent Data Analyst](#3-intelligent-data-analyst)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [Method 1: Docker Compose (Recommended)](#method-1-docker-compose-recommended)
  - [Method 2: Native Local Development](#method-2-native-local-development)
- [Environment Configuration](#-environment-configuration)
- [Documentation Center](#-documentation-center)
- [Security & Threat Mitigation](#-security--threat-mitigation)
- [Roadmap & Release Milestones](#-roadmap--release-milestones)
- [Code of Conduct](#-code-of-conduct)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Executive Summary

**Vectronyx AI Workbench** is an enterprise-grade, local-first artificial intelligence workstation engineered for high-throughput, private, and deterministic knowledge workflows. It synthesizes three distinct pillars of modern artificial intelligence into a cohesive user experience:

1. **Episodic & Semantic Vector Recall**: Persistent long-term memory indexed in sub-millisecond local vector stores (`faiss-cpu`) backed by normalized embeddings (`all-MiniLM-L6-v2`) and relational Postgres metadata.
2. **Autonomous ReAct Web Exploration**: Self-directed multi-hop investigation agents combining zero-cost search (DuckDuckGo), noise-free markdown extraction (`trafilatura`), and dual-tier inference (Groq Cloud LPU acceleration with local Ollama offline failover).
3. **Tabular Mathematical & Anomaly Intelligence**: In-memory analytical data querying running on Pandas and Scikit-learn (`IsolationForest`), producing statistical distributions and automated Matplotlib/Seaborn figures.

---

## 🏗 System Architecture & Core Mechanics

```mermaid
flowchart TB
    subgraph ClientLayer["Presentation Tier (Port 5173)"]
        UI[React 18 SPA + Tailwind CSS v4]
        Router[React Router DOM v7]
        ApolloClient[Apollo GraphQL Client]
        SupaClient[Supabase Auth Client]
    end

    subgraph APILayer["API Gateway & Middleware Tier (Port 8000)"]
        FastAPI[FastAPI ASGI Core]
        AuthRouter["REST Auth (/auth/login, /auth/signup)"]
        Strawberry["Strawberry GraphQL (/graphql)"]
        CORS[CORS Middleware]
        Threadpool["anyio / Worker Threadpool\n(Offloads CPU Tasks)"]
    end

    subgraph AgentLayer["Autonomous Intelligence Tier"]
        Mem["Memory System\n(MiniLM Embedder + FAISS)"]
        Res["Research Agent\n(LangChain ReAct + Scraper)"]
        Data["Data Analyst\n(Pandas + IsolationForest + Plots)"]
    end

    subgraph InferenceLayer["Dual-Tier Inference Engine"]
        Groq["Groq Cloud API\n(LLaMA 3.3 70B • ~250 tok/s)"]
        Ollama["Local Ollama Daemon\n(LLaMA 3 • Offline Fallback)"]
    end

    subgraph StorageLayer["Data & Persistence Tier"]
        PG[(Supabase PostgreSQL\nusers, memories, query_logs)]
        FAISSStore[("FAISS Vector Store\nFlatL2 Index in vector_store/")]
    end

    UI --> Router
    Router --> ApolloClient
    Router --> SupaClient

    ApolloClient -->|Typed Queries / Mutations| Strawberry
    UI -->|Session Auth| AuthRouter
    SupaClient -->|Client Token Exchange| PG

    FastAPI --> CORS
    CORS --> Strawberry
    CORS --> AuthRouter

    Strawberry --> Threadpool
    Threadpool --> Mem
    Threadpool --> Res
    Threadpool --> Data

    Mem --> FAISSStore
    Mem --> PG

    Res --> Groq
    Res -.->|Circuit Breaker Fallback| Ollama

    Data --> Groq
    Data --> Ollama
    Data --> PG
```

---

## 🧠 Principal Engineering Highlights

Architected with lessons drawn from production-scale distributed systems and high-throughput ML pipelines:

### 1. Concurrency Segregation (Non-Blocking Event Loop)
- **Problem**: Python's Global Interpreter Lock (GIL) freezes asynchronous coroutines when CPU-bound calculations (e.g., Sentence-Transformer vector encoding or FAISS distance computations) execute directly in `async def` routes.
- **Architectural Solution**: Vectronyx strictly segregates I/O-bound coroutines (`httpx`, `asyncpg`, Supabase REST calls) from CPU-bound computation by delegating tensor generation and analytical profiling to worker threadpools (`anyio.to_thread.run_sync`).

### 2. Information Retrieval (IR) Vector Mathematics
- **Embedding Space**: Continuous vector space $\mathbb{R}^{384}$ using `all-MiniLM-L6-v2`.
- **Metric Formulation**: With $L_2$-normalized embeddings ($\|\mathbf{u}\|_2 = \|\mathbf{v}\|_2 = 1$), Euclidean distance and Cosine similarity are monotonically linked:
  $$D_{L2}^2(\mathbf{u}, \mathbf{v}) = 2 - 2 \cdot \cos(\theta)$$
- **Index Selection**: Vectronyx utilizes `IndexFlatL2` for datasets up to 500,000 vectors, ensuring **100% exact recall** without quantization distortion.
- **Memory Consumption**: Strictly $N \times 384 \times 4 \text{ bytes} \approx 1.53 \text{ KB}$ per vector ($10,000$ memories consume merely $\approx 15.3 \text{ MB}$ of RAM).

### 3. Agentic Halting Bounds & Circuit Breakers
- **Problem**: Autonomous ReAct agents risk infinite looping and runaway token consumption on ambiguous or adversarial web prompts.
- **Architectural Solution**: Enforces a strict triple halting boundary:
  1. Maximum step count limiter ($N \le 6$ tool iterations).
  2. Cumulative token budget ceiling ($32,000$ tokens per session).
  3. Action deduping cache: Hashes tool invocations (`hash(tool + args)`) to detect and abort cyclical queries.

### 4. Dual-Inference Resilience Pattern
- **Primary**: Cloud-accelerated Groq Cloud inference (LLaMA 3.3 70B Versatile) for sub-second agent reasoning.
- **Failover**: Automated circuit breaker fallback to internal Ollama daemon (`http://localhost:11434`) on HTTP 429 (rate-limit) or upstream 5xx outages, guaranteeing zero downtime.

---

## 🚀 Core AI Engines

### 1. Contextual Memory System
- **Dense Vector Encoding**: Text snippets are embedded into 384-dimensional dense vectors.
- **Hybrid Retrieval**: Pairs FAISS semantic nearest-neighbor search with PostgreSQL relational filtering and temporal recency decay scoring.
- **Context Injection**: Automatically surfaces the top-$K$ most contextually relevant memories into active agent prompts.

### 2. Autonomous Research Agent
- **ReAct Execution Engine**: Dispatches autonomous thoughts, actions, and observations using `langchain`.
- **Zero-Cost Web Discovery**: Queries DuckDuckGo for live global web findings without commercial search API fees.
- **Noise-Free Content Scraping**: Strips cookie banners, tracking scripts, and HTML chrome using `trafilatura` and `beautifulsoup4` with `lxml`, feeding clean markdown directly to the reasoning engine.

### 3. Intelligent Data Analyst
- **Tabular Ingestion**: Parses CSV, TSV, and JSON formats into optimized Pandas DataFrames.
- **Unsupervised Anomaly Detection**: Employs Scikit-learn's `IsolationForest` to isolate multi-dimensional outliers mathematically via path length scoring:
  $$s(x, n) = 2^{-\frac{\mathbb{E}(h(x))}{c(n)}}$$
- **Automated Visualization**: Generates distribution plots, correlation heatmaps, and scatter plots via Matplotlib and Seaborn, streaming base64 images directly to the client UI.

---

## 🛠 Technology Stack

| Tier | Component | Technology | Rationale |
| :--- | :--- | :--- | :--- |
| **Frontend** | Framework | React 18 + Vite 5 + TypeScript | Instant HMR, static type verification, optimized bundle chunks. |
| **Frontend** | Styling | Tailwind CSS v4 (`@tailwindcss/vite`) | Modern CSS variables, zero runtime CSS injection overhead. |
| **Frontend** | Data Fetching | Apollo Client 4 + Supabase JS | Typed GraphQL in-memory cache + persistent client auth sessions. |
| **Backend** | API Engine | FastAPI 0.115 + Uvicorn 0.30 | High-performance ASGI framework with Pydantic v2 data validation. |
| **Backend** | GraphQL Engine | Strawberry GraphQL | Code-first typed Python GraphQL with native FastAPI dependency injection. |
| **AI / LLM** | Cloud Engine | Groq Cloud (`groq`, `langchain-groq`) | Sub-second token delivery on LLaMA 3.3 70B for agentic loops. |
| **AI / LLM** | Local Engine | Ollama Client (`ollama`) | Air-gapped, offline fallback inference with zero API billing. |
| **Embeddings** | Embedder | Sentence-Transformers (`all-MiniLM-L6-v2`) | Balanced 384d semantic fidelity with minimal CPU encoding latency. |
| **Vector DB**| Similarity Search | FAISS CPU (`faiss-cpu`) | Exact $L_2$ distance nearest-neighbor queries without external network overhead. |
| **Database** | Relational Store | PostgreSQL (Supabase) + SQLAlchemy 2.0 | ACID compliance, declarative models, Alembic migration tracking. |
| **Containers**| Orchestration | Docker + Docker Compose | Isolated multi-service environment with host volume mounts for live dev. |

---

## 📁 Project Structure

```
Vectronyx/
├── backend/                      # FastAPI Application & AI Engines
│   ├── alembic/                  # Database migration scripts
│   ├── app/
│   │   ├── api/                  # Strawberry GraphQL schemas & resolvers
│   │   ├── core/                 # Configuration, dependencies & constants
│   │   ├── db/                   # SQLAlchemy models & Supabase database client
│   │   ├── middleware/           # App initialization, CORS & auth router
│   │   ├── modules/
│   │   │   ├── data_analyst/     # Tabular parsing, scikit-learn & plotting
│   │   │   ├── memory/           # Sentence Transformers & FAISS store
│   │   │   └── research_agent/   # LangChain ReAct, DuckDuckGo & scraping
│   │   └── services/             # LLM clients (Groq/Ollama) & vector stores
│   ├── Dockerfile                # Python 3.11 slim container specification
│   └── requirements.txt          # Pinned Python package dependencies
├── frontend/                     # React 18 + Vite Application
│   ├── src/
│   │   ├── app/                  # Router & route definitions
│   │   ├── components/           # Layout, Header & Responsive Sidebar
│   │   ├── features/             # Auth, Dashboard, Data Analyst, Memory, Research
│   │   ├── lib/                  # Apollo & Supabase client initialization
│   │   └── pages/                # 404 & standalone pages
│   ├── Dockerfile                # Node 20 slim container with pnpm
│   └── package.json              # Frontend packages & scripts
├── infra/                        # Orchestration & Infrastructure
│   ├── docker-compose.yml        # Development multi-container compose
│   ├── nginx/                    # Reverse proxy configs
│   └── k8s/                      # Kubernetes deployment manifests
├── vector_store/                 # Local FAISS index binary files
├── data/                         # Uploaded datasets and scratch files
├── docs/                         # Comprehensive Technical Documentation
│   ├── README.md                 # Master documentation index
│   ├── SYSTEM_DESIGN.md          # Principal engineering & architecture manual
│   ├── ARCHITECTURE.md           # Architectural blueprint & diagrams
│   ├── GETTING_STARTED.md        # Installation & setup guide
│   ├── AI_MODULES.md             # Deep dive into Memory, Research & Analyst
│   ├── API_REFERENCE.md          # GraphQL schema & REST endpoint specs
│   ├── DATABASE_SCHEMA.md        # PostgreSQL models & vector indexing
│   ├── DOCKER_AND_INFRA.md       # Containerization & deployment manual
│   ├── FRONTEND_GUIDE.md         # Component tree & design system
│   └── ROADMAP.md                # Release milestones & contribution guide
├── CODE_OF_CONDUCT.md            # Contributor Covenant v2.1 + AI Safety Standards
└── README.md                     # Primary project manual (this file)
```

---

## ⚡ Quick Start

### Prerequisites
- **Node.js**: `>= 20.x LTS` and **pnpm**: `>= 9.x`
- **Python**: `3.10` or `3.11`
- **Docker & Compose**: (Optional, recommended)

---

### Method 1: Docker Compose (Recommended)

Run the full stack with hot-reloading in one command:

```bash
# 1. Clone repository
git clone https://github.com/din-esh-kumar/Vectronyx.git
cd Vectronyx

# 2. Configure environment
cp backend/.env.example backend/.env

# 3. Launch containers
cd infra
docker compose up --build
```

- 🌐 **Frontend UI**: [http://localhost:5173](http://localhost:5173)
- ⚡ **Backend API**: [http://localhost:8000](http://localhost:8000)
- 🔍 **Interactive GraphQL Explorer**: [http://localhost:8000/graphql](http://localhost:8000/graphql)

---

### Method 2: Native Local Development

#### 1. Backend Setup
```bash
cd backend
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start API server
uvicorn app.middleware.app:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Setup
In a new terminal:
```bash
cd frontend
corepack enable
pnpm install
pnpm run dev
```

Visit [http://localhost:5173](http://localhost:5173).

---

## 🔑 Environment Configuration

Key configuration parameters in `backend/.env`:

| Variable | Sample Value | Purpose |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://postgres:...@db...` | Supabase PostgreSQL direct connection string |
| `SUPABASE_URL` | `https://[ref].supabase.co` | Supabase API project URL |
| `SUPABASE_SERVICE_ROLE_KEY`| `eyJhbGciOi...` | Elevated backend key for administrative DB queries |
| `SUPABASE_PUBLISHABLE_KEY` | `sb_publishable_...` | Anon public key for auth handshakes |
| `LLM_PROVIDER` | `groq` | Active inference provider: `groq` or `ollama` |
| `GROQ_API_KEY` | `gsk_...` | Groq Cloud API authentication key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model selection |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama daemon URL |
| `VECTOR_STORE_PATH` | `./vector_store` | Path for serialized FAISS index |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-Transformers embedding model |

---

## 🛡 Security & Threat Mitigation

| Threat Vector | Mitigation Strategy in Vectronyx |
| :--- | :--- |
| **Server-Side Request Forgery (SSRF)** | The web scraper pre-flights URLs to ensure target IPs do not resolve to loopback (`127.0.0.0/8`), private networks (`10.0.0.0/8`, `192.168.0.0/16`), or cloud metadata endpoints (`169.254.0.0/16`). |
| **Indirect Prompt Injection** | Web scraped inputs are quarantined inside `<external_untrusted_data>` XML blocks with explicit system boundaries instructing the LLM to treat scraped content as data, never as executable instructions. |
| **BOLA / IDOR Authorization Flaws** | GraphQL resolvers resolve `user_id` strictly from cryptographically verified JWT claims, never from user-supplied query arguments. |
| **Arbitrary Code Execution** | Data Analyst queries execute safe, parameterized Pandas/Scipy transformations; raw `eval()` or `exec()` calls on client inputs are strictly prohibited. |

---

## 📚 Documentation Center

For exhaustive technical guides, explore the [`docs/`](./docs/README.md) directory:

- 🏛️ [**System Design & Principal Engineering Manual**](./docs/SYSTEM_DESIGN.md) — Staff-level guide to concurrency, vector IR math, agent bounds, and resilience.
- 📐 [**Architecture Blueprint**](./docs/ARCHITECTURE.md) — Architectural design, data flows, and component interaction.
- 🚀 [**Getting Started Guide**](./docs/GETTING_STARTED.md) — Comprehensive developer setup and troubleshooting.
- 🧠 [**AI Modules Deep Dive**](./docs/AI_MODULES.md) — Mechanics of Memory, Research Agent, and Data Analyst.
- 📡 [**API & GraphQL Reference**](./docs/API_REFERENCE.md) — Complete GraphQL query/mutation and REST specs.
- 🗄️ [**Database & Vector Store Schema**](./docs/DATABASE_SCHEMA.md) — Relational models, Alembic migrations, and FAISS.
- 🐳 [**Docker & Infrastructure**](./docs/DOCKER_AND_INFRA.md) — Multi-container Docker Compose and production hardening.
- 🎨 [**Frontend Architecture Guide**](./docs/FRONTEND_GUIDE.md) — React 18, Tailwind v4, navigation, and auth state.
- 🗺️ [**Development Roadmap**](./docs/ROADMAP.md) — Feature status, milestones, and contribution standards.
- 📜 [**Code of Conduct**](./CODE_OF_CONDUCT.md) — Contributor Covenant v2.1, AI ethics, and responsible agentic standards.

---

## 🗺 Roadmap & Release Milestones

- [x] **v0.1.0 — Platform Foundations**: Service architecture split, Docker Compose orchestration, responsive UI shell, and Supabase auth.
- [ ] **v0.2.0 — Core AI Engines**: Full implementation of Sentence-Transformers + FAISS memory, LangChain ReAct research agent, and Pandas data analyzer.
- [ ] **v0.3.0 — GraphQL API Binding**: Strawberry GraphQL schema and resolvers fully wired to Apollo Client.
- [ ] **v0.4.0 — Workstation Visualizations**: Interactive CSV uploader, Recharts dynamic charts, and streaming agent execution logs.
- [ ] **v1.0.0 — Production Hardening**: Automated test coverage (pytest + Vitest), CI/CD pipelines, and multi-tenant memory isolation.

---

## 📜 Code of Conduct

All contributors and participants in the Vectronyx project are expected to adhere to our [Code of Conduct](./CODE_OF_CONDUCT.md). We maintain a zero-tolerance policy towards harassment, discrimination, insecure tool modifications, and data poisoning.

---

## 🤝 Contributing

Contributions are welcomed! Please read our [Contribution Guidelines](./docs/ROADMAP.md#3-contribution-workflow), ensure your branch follows conventional naming (`feature/`, `fix/`, `docs/`), and submit PRs with descriptive commit messages following the Conventional Commits specification.

---

## 📄 License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.
