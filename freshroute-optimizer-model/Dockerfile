# FreshRoute Optimizer — Containerized deployment (spec 7 Phase 2, plan P6)
# Build: docker build -t freshroute-optimizer-api:1.0-rc -f Dockerfile .
# Run:   docker run -p 8000:8000 freshroute-optimizer-api:1.0-rc
# Digest recorded in environment.lock at gate.

FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="FreshRoute Food Redistribution Optimizer"
LABEL org.opencontainers.image.description="Arrhenius + Pareto matcher + VRPTW + forecaster FastAPI service"
LABEL org.opencontainers.image.source="https://github.com/anomalyco/freshroute"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.version="1.0.0-RC"

WORKDIR /app

# System deps for ortools/lightgbm and ge
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# App: copy only optimizer subproject content
COPY api /app/api
COPY core /app/core
COPY data /app/data
COPY tests /app/tests

ENV PYTHONPATH=/app
ENV PYTHONHASHSEED=0
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
