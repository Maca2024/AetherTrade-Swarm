# ORACLE SWARM — Backend Dockerfile
# Build context: repo root (to access both backend/ and prompt-stack/)

FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Production stage ---
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash aethertrade
USER aethertrade

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy backend application code
COPY --chown=aethertrade:aethertrade backend/ .

# Copy prompt stack (referenced by chat endpoint)
COPY --chown=aethertrade:aethertrade prompt-stack/ ./prompt-stack/

EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8888/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8888", "--workers", "1"]
