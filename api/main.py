"""
FastAPI ML inference service for apparent-temperature prediction.

Environment variables:
    MODEL_PATH      Path to the joblib model file (default: model_v1.0.0.pkl next to main.py)
    MODEL_VERSION   Semantic version string (default: read from metrics.json or "1.0.0")
    API_VERSION     API version string (default: "1.0.0")
"""

import os
import time
import threading
from contextlib import asynccontextmanager
from typing import List

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# In-memory metrics (thread-safe)
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_metrics = {
    "inference_count": 0,
    "error_count": 0,
    "total_latency_ms": 0.0,
}


def _record(latency_ms: float, error: bool = False):
    with _lock:
        _metrics["inference_count"] += 1
        _metrics["total_latency_ms"] += latency_ms
        if error:
            _metrics["error_count"] += 1


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------
_MODEL_PATH = os.environ.get(
    "MODEL_PATH",
    os.path.join(os.path.dirname(__file__), "..", "model", "model_v1.0.0.pkl"),
)
_API_VERSION = os.environ.get("API_VERSION", "1.0.0")
_MODEL_VERSION = os.environ.get("MODEL_VERSION", "1.0.0")
_model = None
_model_load_time_ms: float = 0.0


def _load_model():
    global _model, _model_load_time_ms
    t0 = time.monotonic()
    _model = joblib.load(_MODEL_PATH)
    _model_load_time_ms = round((time.monotonic() - t0) * 1000, 2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_model()
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Weather ML API",
    description="Predicts apparent temperature (°C) from weather sensor readings.",
    version=_API_VERSION,
    lifespan=lifespan,
)

FEATURE_ORDER = [
    "humidity",
    "wind_speed_kmh",
    "wind_bearing_deg",
    "visibility_km",
    "pressure_mb",
    "is_rain",
]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class WeatherRecord(BaseModel):
    humidity: float = Field(..., ge=0.0, le=1.0, description="Relative humidity [0-1]")
    wind_speed_kmh: float = Field(..., ge=0.0, description="Wind speed in km/h")
    wind_bearing_deg: float = Field(..., ge=0.0, le=360.0, description="Wind bearing in degrees")
    visibility_km: float = Field(..., ge=0.0, description="Visibility in km")
    pressure_mb: float = Field(..., ge=900.0, le=1100.0, description="Sea-level pressure in mbar")
    is_rain: int = Field(..., ge=0, le=1, description="1 if precipitation type is rain, else 0")

    @field_validator("humidity")
    @classmethod
    def humidity_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("humidity must be between 0 and 1")
        return v


class PredictRequest(BaseModel):
    records: List[WeatherRecord] = Field(..., min_length=1, max_length=1000)


class PredictResponse(BaseModel):
    predictions: List[float]
    model_version: str
    processing_time_ms: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", tags=["ops"])
def health():
    status = "ok" if _model is not None else "model_not_loaded"
    return {
        "status": status,
        "model_load_time_ms": _model_load_time_ms,
    }


@app.get("/version", tags=["ops"])
def version():
    return {
        "api_version": _API_VERSION,
        "model_version": _MODEL_VERSION,
    }


@app.get("/metrics", tags=["ops"])
def metrics():
    with _lock:
        count = _metrics["inference_count"]
        errors = _metrics["error_count"]
        total_lat = _metrics["total_latency_ms"]
    avg_lat = round(total_lat / count, 2) if count > 0 else 0.0
    error_rate = round(errors / count, 4) if count > 0 else 0.0
    return {
        "inference_count": count,
        "error_count": errors,
        "error_rate": error_rate,
        "average_latency_ms": avg_lat,
    }


@app.post("/predict", response_model=PredictResponse, tags=["inference"])
def predict(body: PredictRequest, request: Request):
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    t0 = time.monotonic()
    try:
        X = np.array([[getattr(r, col) for col in FEATURE_ORDER] for r in body.records])
        preds = _model.predict(X).tolist()
        latency = round((time.monotonic() - t0) * 1000, 2)
        _record(latency)
        return PredictResponse(
            predictions=[round(p, 4) for p in preds],
            model_version=_MODEL_VERSION,
            processing_time_ms=latency,
        )
    except Exception as exc:
        latency = round((time.monotonic() - t0) * 1000, 2)
        _record(latency, error=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
