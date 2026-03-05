# Backend Dockerfile
FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps para psycopg2 e SSL (certificados para HTTPS com Google APIs)
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
     build-essential \
     libpq-dev \
     curl \
     ca-certificates \
     openssl \
  && update-ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Garantir que Python/httplib2 usem o bundle de CAs do sistema
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Install Python deps
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy source
COPY . .

# Entrypoint with DB wait + migration
RUN chmod +x docker-entrypoint.sh || true

EXPOSE 8000

ENTRYPOINT ["/bin/bash", "-c", "./docker-entrypoint.sh"]

