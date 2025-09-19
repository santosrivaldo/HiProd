# Backend Dockerfile
FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for psycopg2
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
     build-essential \
     libpq-dev \
     curl \
  && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy source
COPY . .

# Entrypoint with DB wait + migration
RUN chmod +x docker-entrypoint.sh || true

EXPOSE 8000

ENTRYPOINT ["/bin/bash", "-c", "./docker-entrypoint.sh"]

