"""pytest unit tests for the FastAPI inference service."""

import pytest
from fastapi.testclient import TestClient

VALID_RECORD = {
    "humidity": 0.72,
    "wind_speed_kmh": 14.3,
    "wind_bearing_deg": 180.0,
    "visibility_km": 9.5,
    "pressure_mb": 1012.4,
    "is_rain": 0,
}


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------
def test_health_ok(api_client):
    resp = api_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "model_load_time_ms" in data


# ---------------------------------------------------------------------------
# /version
# ---------------------------------------------------------------------------
def test_version_fields(api_client):
    resp = api_client.get("/version")
    assert resp.status_code == 200
    data = resp.json()
    assert "api_version" in data
    assert "model_version" in data


# ---------------------------------------------------------------------------
# /predict - success path
# ---------------------------------------------------------------------------
def test_predict_single_record(api_client):
    resp = api_client.post("/predict", json={"records": [VALID_RECORD]})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["predictions"]) == 1
    assert isinstance(data["predictions"][0], float)
    assert "processing_time_ms" in data
    assert data["model_version"] is not None


def test_predict_batch(api_client):
    resp = api_client.post("/predict", json={"records": [VALID_RECORD] * 5})
    assert resp.status_code == 200
    assert len(resp.json()["predictions"]) == 5


# ---------------------------------------------------------------------------
# /predict - invalid input
# ---------------------------------------------------------------------------
def test_predict_humidity_out_of_range(api_client):
    bad = {**VALID_RECORD, "humidity": 1.5}
    resp = api_client.post("/predict", json={"records": [bad]})
    assert resp.status_code == 422


def test_predict_pressure_too_low(api_client):
    bad = {**VALID_RECORD, "pressure_mb": 500.0}
    resp = api_client.post("/predict", json={"records": [bad]})
    assert resp.status_code == 422


def test_predict_negative_wind(api_client):
    bad = {**VALID_RECORD, "wind_speed_kmh": -5.0}
    resp = api_client.post("/predict", json={"records": [bad]})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /predict - missing payload
# ---------------------------------------------------------------------------
def test_predict_empty_body(api_client):
    resp = api_client.post("/predict", json={})
    assert resp.status_code == 422


def test_predict_missing_field(api_client):
    incomplete = {k: v for k, v in VALID_RECORD.items() if k != "pressure_mb"}
    resp = api_client.post("/predict", json={"records": [incomplete]})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /metrics
# ---------------------------------------------------------------------------
def test_metrics_after_predict(api_client):
    api_client.post("/predict", json={"records": [VALID_RECORD]})
    resp = api_client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["inference_count"] >= 1
    assert "average_latency_ms" in data
    assert "error_rate" in data
