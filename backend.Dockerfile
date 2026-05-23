# ── Stage 1: build dependencies ──
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install --prefix=/install -r requirements.txt

# ── Stage 2: runtime ──
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.12/site-packages"

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /install

# Copy application code
COPY backend ./backend
COPY analytics ./analytics
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY requirements.txt ./requirements.txt

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser \
    && chown -R appuser:appuser /app /install
USER appuser

ENV PORT=8000
EXPOSE 8000

# Gunicorn with Uvicorn workers for production
# Workers = (2 × CPUs) + 1; adjust based on deployment resources
CMD ["uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--timeout-keep-alive", "120", \
     "--log-level", "info", \
     "--access-log", \
     "--proxy-headers"]
