# Vectronyx AI Workbench — Development Roadmap & Milestones

This document outlines the current progress, implementation milestones, and contribution guidelines for **Vectronyx AI Workbench**.

---

## 1. Project Implementation Matrix

| Module / Feature | Status | Priority | Notes |
| :--- | :--- | :--- | :--- |
| **Project Setup & Base Architecture** | ✅ Completed | High | Clean service split (`frontend/`, `backend/`, `infra/`). |
| **Docker Compose Orchestration** | ✅ Completed | High | Multi-container setup with live volume mounts for rapid dev. |
| **Frontend Shell & Responsive Layout** | ✅ Completed | High | Collapsible desktop sidebar + mobile slide-over drawer with overlay. |
| **Supabase Authentication UI** | ✅ Completed | High | Google OAuth, GitHub OAuth, and Email/Password flows. |
| **Relational Database Schema (SQLAlchemy)** | ✅ Completed | High | `users`, `datasets`, `memories`, and `query_logs` models defined. |
| **Cloud Storage & pgvector Integration** | ✅ Completed | Critical | `datasets` bucket configured on Supabase Storage + `pgvector` enabled. |
| **Core AI Engines (Data Analyst, Memory, Research)** | 🟡 In Progress | Critical | In-memory Pandas profiler, IsolationForest, and ReAct agent. |
| **Strawberry GraphQL Resolvers** | 🟡 In Progress | Critical | Binding backend AI engines to frontend Apollo Client. |
| **CSV Tabular Uploader & Visualizer** | ⚪ Planned | Medium | Drag-and-drop CSV parser with interactive Recharts charts. |
| **Research Report Markdown Renderer** | ⚪ Planned | Medium | Rich markdown synthesis viewer with citations and source pills. |
| **Test Suites & CI/CD Pipeline** | ⚪ Planned | Medium | Pytest backend suites, Vitest frontend tests, and GitHub Actions. |

---

## 2. Release Milestones

### Milestone 1: Foundations & Infrastructure (v0.1.0) — ✅ Complete
- [x] Initial repository structure and dependency management (`requirements.txt`, `package.json`, `pnpm-lock.yaml`).
- [x] Dockerfile for backend (`python:3.11-slim`) and frontend (`node:20-slim`).
- [x] Multi-service `docker-compose.yml` with port mapping (`8000` and `5173`).
- [x] Supabase integration for authentication and PostgreSQL connection.
- [x] Desktop and mobile navigation layout with smooth responsive behavior.

### Milestone 2: Cloud AI Engines & Inference (v0.2.0) — 🟡 Active
- [x] Configure cloud dataset storage in Supabase Storage (`datasets` bucket).
- [ ] Connect Supabase `pgvector` for semantic dataset memory in `backend/app/modules/memory/`.
- [ ] Implement in-memory Pandas statistical profiler and Isolation Forest anomaly detector in `backend/app/modules/data_analyst/`.
- [ ] Enable dual-cloud inference with Google Gemini (`gemini-3.5-flash-lite`, 1M context) and Groq Cloud (`openai/gpt-oss-120b`).
- [ ] Implement ReAct loop with DuckDuckGo Search and Trafilatura web scraping in `backend/app/modules/research_agent/`.

### Milestone 3: GraphQL API Integration (v0.3.0) — ⚪ Planned
- [ ] Implement Strawberry GraphQL schema in `backend/app/api/schema.py`.
- [ ] Implement resolvers for `data_resolver.py`, `memory_resolver.py`, and `research_resolver.py`.
- [ ] Connect Apollo Client in frontend to execute queries and mutations.

### Milestone 4: Enhanced Workstation UI (v0.4.0) — ⚪ Planned
- [ ] Full CSV analysis screen with column histograms, correlation matrices, and dynamic filters.
- [ ] Streaming research logs showing real-time agent thoughts and actions.
- [ ] Memory explorer to view, filter, and delete stored contextual memories.

---

## 3. Contribution Workflow

We welcome contributions! Please follow standard Git practices:

1. **Branching Naming Convention**:
   - `feature/<feature-name>` (e.g., `feature/research-agent-tools`)
   - `fix/<bug-description>` (e.g., `fix/docker-entrypoint`)
   - `docs/<doc-topic>` (e.g., `docs/api-examples`)

2. **Commit Message Format**:
   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat(memory): add FAISS persistence layer`
   - `fix(auth): correct token refresh handling`
   - `docs(readme): add docker setup instructions`

3. **Submitting Pull Requests**:
   - Verify both frontend and backend start clean without errors.
   - Reference open issue numbers in your PR description.
