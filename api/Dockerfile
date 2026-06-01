# Build context: project root  (docker build -f api/Dockerfile .)
# ── Stage 1: build ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

COPY api/requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY --from=builder /install /usr/local

COPY api/main.py .
COPY model/model_v1.0.0.pkl /app/model_v1.0.0.pkl

RUN chown -R appuser:appuser /app

USER appuser

ENV MODEL_PATH=/app/model_v1.0.0.pkl \
    MODEL_VERSION=1.0.0 \
    API_VERSION=1.0.0 \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
