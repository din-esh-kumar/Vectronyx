# Vectronyx AI Workbench — Documentation Center

Welcome to the official technical documentation for **Vectronyx AI Workbench**. This documentation suite provides an exhaustive, production-grade guide to the architecture, codebase, AI modules, API contracts, database schemas, and deployment workflows powering the platform.

---

## 📚 Master Documentation Index

| Guide | Description | Target Audience |
| :--- | :--- | :--- |
| [**System Design & Principal Engineering**](./SYSTEM_DESIGN.md) | In-depth engineering manual: concurrency models, vector search IR theory, isolation forest math, SSRF defenses, and circuit breakers. | Principal Architects, Staff AI Leads |
| [**Architecture Blueprint**](./ARCHITECTURE.md) | High-level system architecture, data flow diagrams, module interactions, and core design patterns. | Systems Architects, Tech Leads |
| [**Getting Started**](./GETTING_STARTED.md) | Prerequisites, environment setup, local installation (native & Docker), and verification steps. | All Contributors |
| [**AI Modules Deep Dive**](./AI_MODULES.md) | Detailed breakdown of the 3 core AI systems: Memory System, Research Agent, and Data Analyst. | AI Engineers, Data Scientists |
| [**API Reference**](./API_REFERENCE.md) | GraphQL schema, Strawberry resolvers, REST endpoints, request/response payloads, and authentication. | Full-Stack & API Developers |
| [**Database & Vector Store Schema**](./DATABASE_SCHEMA.md) | PostgreSQL / Supabase relational models, SQLAlchemy ORM, Alembic migrations, and FAISS indexing. | Backend & Database Engineers |
| [**Docker & Infrastructure**](./DOCKER_AND_INFRA.md) | Container architecture, multi-container Docker Compose, live development volumes, and CI/CD ready specs. | DevOps & Infrastructure |
| [**Frontend Guide**](./FRONTEND_GUIDE.md) | React 18, Vite, TypeScript, Tailwind CSS v4, responsive layout (Desktop + Mobile drawer), and Apollo/Supabase integration. | Frontend Developers |
| [**Development Roadmap**](./ROADMAP.md) | Implementation matrix, release milestones (v0.1.0 to v1.0.0), and contribution standards. | Project Planners & Contributors |
| [**Code of Conduct**](../CODE_OF_CONDUCT.md) | Community pledge, acceptable behaviors, responsible AI ethics, and incident escalation protocols. | Entire Community |

---

## 🧭 System At A Glance

```
                                  +-------------------------------------------------+
                                  |            Vectronyx UI (Port 5173)            |
                                  |     React 18 • Vite • TypeScript • Tailwind v4    |
                                  +------------------------+------------------------+
                                                           |
                                      HTTP / GraphQL / Auth| (Supabase Session)
                                                           v
                                  +-------------------------------------------------+
                                  |          FastAPI Backend (Port 8000)            |
                                  |        Strawberry GraphQL • Uvicorn • Pydantic  |
                                  +----+-------------------+-------------------+----+
                                       |                   |                   |
               +-----------------------+                   |                   +-----------------------+
               v                                           v                                           v
    +----------------------+                   +----------------------+                    +----------------------+
    |    Memory System     |                   |    Research Agent    |                    |     Data Analyst     |
    |----------------------|                   |----------------------|                    |----------------------|
    | • all-MiniLM-L6-v2   |                   | • LangChain ReAct    |                    | • Pandas & NumPy     |
    | • FAISS Vector Store |                   | • DuckDuckGo Search  |                    | • Scikit-learn (ML)  |
    | • Supabase / PG Base |                   | • Trafilatura / BS4  |                    | • Matplotlib/Seaborn |
    | • Semantic Recall    |                   | • Groq / LLaMA 3.3   |                    | • Chart Generation   |
    +----------------------+                   +----------------------+                    +----------------------+
               |                                           |                                           |
               +-------------------------------------------+-------------------------------------------+
                                                           |
                                                           v
                                  +-------------------------------------------------+
                                  |       PostgreSQL / Supabase + File Storage      |
                                  |   Tables: users, memories, query_logs, FAISS    |
                                  +-------------------------------------------------+
```

---

## ⚡ Quick Navigation Links

- **Need the deep architectural rationale and failure mode analysis?** Read [System Design & Principal Engineering](./SYSTEM_DESIGN.md).
- **Need to spin up the app right away?** Head over to [Getting Started](./GETTING_STARTED.md).
- **Need to understand how the AI research or memory works?** Check out [AI Modules Deep Dive](./AI_MODULES.md).
- **Working on the GraphQL API?** Consult the [API Reference](./API_REFERENCE.md).
- **Reviewing community and AI safety standards?** Visit [Code of Conduct](../CODE_OF_CONDUCT.md).
