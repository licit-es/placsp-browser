FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# System packages needed by schema-init (psql) and etl-cron (cron)
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client cron jq curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ src/
COPY schema/ schema/
COPY deploy/crontab /etc/cron.d/etl
COPY deploy/etl-run.sh /app/deploy/etl-run.sh

ENV PYTHONPATH=src
