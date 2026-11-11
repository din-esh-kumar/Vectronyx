# ==============================================================================
# Vectronyx AI Workbench - Production Backend Dockerfile (HF Spaces & Docker)
# ==============================================================================
FROM python:3.10-slim AS builder

WORKDIR /build

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

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------------------------
# Production Runtime Stage (HF Spaces UID 1000 Compatible)
# ------------------------------------------------------------------------------
FROM python:3.10-slim AS runner

# Hugging Face Spaces runs containers with UID 1000
RUN useradd -m -u 1000 user

ENV HOME=/home/user \
    PATH="/opt/venv/bin:/home/user/.local/bin:$PATH" \
    PYTHONPATH="/home/user/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    FASTEMBED_CACHE_PATH=/tmp/fastembed_cache \
    HF_HOME=/tmp/huggingface

WORKDIR /home/user/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /tmp/fastembed_cache /tmp/huggingface \
    && chmod -R 777 /tmp/fastembed_cache /tmp/huggingface

COPY --from=builder /opt/venv /opt/venv
COPY --chown=user:user . /home/user/app

USER user

EXPOSE 7860

HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT:-7860}/health || exit 1

CMD ["sh", "-c", "uvicorn app.middleware.app:app --host 0.0.0.0 --port ${PORT:-7860} --workers ${UVICORN_WORKERS:-1}"]
