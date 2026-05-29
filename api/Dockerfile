# ── Stage 1: build ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Non-root user for security
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code and model
COPY main.py .
COPY --chown=appuser:appuser . .

# Model is mounted via env var MODEL_PATH or baked in at /app/model_v1.0.0.pkl
# The COPY below includes it when building locally; in Azure it's injected via
# Container Apps environment variables pointing to Blob Storage.
COPY ../model/model_v1.0.0.pkl /app/model_v1.0.0.pkl

USER appuser

ENV MODEL_PATH=/app/model_v1.0.0.pkl \
    MODEL_VERSION=1.0.0 \
    API_VERSION=1.0.0 \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
