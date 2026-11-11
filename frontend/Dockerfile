# ==============================================================================
# Vectronyx AI Workbench - Production Frontend Dockerfile
# ==============================================================================
FROM node:20-slim AS builder

WORKDIR /app

# Enable corepack and prepare pnpm
RUN corepack enable && corepack prepare pnpm@9.12.2 --activate

# Copy dependency manifests
COPY package.json pnpm-lock.yaml ./

# Install dependencies strictly from lockfile
RUN pnpm install --frozen-lockfile

# Copy application source
COPY . .

# Build-time environment variable arguments (optional)
ARG VITE_API_URL
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_PUBLISHABLE_KEY
ARG VITE_GEMINI_MODEL
ARG VITE_GROQ_MODEL

ENV VITE_API_URL=${VITE_API_URL} \
    VITE_SUPABASE_URL=${VITE_SUPABASE_URL} \
    VITE_SUPABASE_PUBLISHABLE_KEY=${VITE_SUPABASE_PUBLISHABLE_KEY} \
    VITE_GEMINI_MODEL=${VITE_GEMINI_MODEL} \
    VITE_GROQ_MODEL=${VITE_GROQ_MODEL}

# Build production bundle
RUN pnpm run build

# ------------------------------------------------------------------------------
# Production Nginx Stage
# ------------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runner

COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/nginx-health || exit 1

CMD ["nginx", "-g", "daemon off;"]

