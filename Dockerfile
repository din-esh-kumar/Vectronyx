# ==============================================================================
# Vectronyx AI Workbench - Unified Full-Stack Dockerfile (Single Container)
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Frontend (React + Vite)
# ------------------------------------------------------------------------------
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

RUN corepack enable && corepack prepare pnpm@9.12.2 --activate

COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend/ .
RUN pnpm run build

# ------------------------------------------------------------------------------
# Stage 2: Build Python Backend Virtualenv
# ------------------------------------------------------------------------------
FROM python:3.10-slim AS backend-builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 3: Unified Production Runtime
# ------------------------------------------------------------------------------
FROM python:3.10-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/backend"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies
COPY --from=backend-builder /opt/venv /opt/venv

# Create non-root user
RUN addgroup --system --gid 1001 vectronyx && \
    adduser --system --uid 1001 --gid 1001 vectronyx

# Copy backend application
COPY --chown=vectronyx:vectronyx backend/ /app/backend/

# Copy compiled frontend static assets
COPY --chown=vectronyx:vectronyx --from=frontend-builder /app/frontend/dist /app/frontend/dist

USER vectronyx

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD ["sh", "-c", "cd /app/backend && uvicorn app.middleware.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
