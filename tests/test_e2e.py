"""
End-to-end integration tests for the ML Pipeline.

These tests are designed to run against a fully deployed Azure environment.
They are skipped automatically when the required environment variables are not set.

Required environment variables:
    ML_API_URL              URL of the deployed Container App ML API
    STORAGE_CONNECTION_STRING   Azure Storage connection string
    COSMOS_CONNECTION_STRING    Cosmos DB connection string
    COSMOS_DATABASE             (default: mlpipeline)
    COSMOS_CONTAINER            (default: inferences)

Run:
    ML_API_URL=https://... STORAGE_CONNECTION_STRING=... pytest tests/test_e2e.py -v
"""

import csv
import io
import json
import os
import time
import uuid

import pytest
import requests

ML_API_URL = os.environ.get("ML_API_URL", "").rstrip("/")
STORAGE_CONN = os.environ.get("STORAGE_CONNECTION_STRING", "")
COSMOS_CONN = os.environ.get("COSMOS_CONNECTION_STRING", "")
COSMOS_DB = os.environ.get("COSMOS_DATABASE", "mlpipeline")
COSMOS_CONTAINER = os.environ.get("COSMOS_CONTAINER", "inferences")

needs_azure = pytest.mark.skipif(
    not all([ML_API_URL, STORAGE_CONN, COSMOS_CONN]),
    reason="Azure environment variables not set — skipping E2E tests",
)

VALID_RECORD = {
    "humidity": 0.75,
    "wind_speed_kmh": 12.0,
    "wind_bearing_deg": 200.0,
    "visibility_km": 8.5,
    "pressure_mb": 1015.0,
    "is_rain": 0,
}


# ---------------------------------------------------------------------------
# ML API E2E tests
# ---------------------------------------------------------------------------
@needs_azure
class TestMLApiE2E:
    def test_health_endpoint(self):
        resp = requests.get(f"{ML_API_URL}/health", timeout=10)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_version_endpoint(self):
        resp = requests.get(f"{ML_API_URL}/version", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert "model_version" in data
        assert "api_version" in data

    def test_predict_single_record(self):
        resp = requests.post(
            f"{ML_API_URL}/predict",
            json={"records": [VALID_RECORD]},
            timeout=15,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["predictions"]) == 1
        assert -50 < data["predictions"][0] < 60, "Prediction out of physically plausible range"

    def test_predict_rejects_invalid_input(self):
        bad = {**VALID_RECORD, "humidity": 2.0}
        resp = requests.post(
            f"{ML_API_URL}/predict",
            json={"records": [bad]},
            timeout=10,
        )
        assert resp.status_code == 422

    def test_metrics_endpoint(self):
        resp = requests.get(f"{ML_API_URL}/metrics", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert "inference_count" in data


# ---------------------------------------------------------------------------
# Full pipeline E2E: upload CSV → wait → check Cosmos DB
# ---------------------------------------------------------------------------
@needs_azure
class TestPipelineE2E:
    def _make_csv(self) -> tuple[str, bytes]:
        """Returns (blob_name, csv_bytes)."""
        blob_name = f"e2e_test_{uuid.uuid4().hex[:8]}.csv"
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(VALID_RECORD.keys()))
        writer.writeheader()
        for _ in range(5):
            writer.writerow(VALID_RECORD)
        return blob_name, buf.getvalue().encode("utf-8")

    def test_full_pipeline(self):
        from azure.storage.blob import BlobServiceClient
        from azure.cosmos import CosmosClient

        blob_name, csv_bytes = self._make_csv()

        # Upload to input/ container
        svc = BlobServiceClient.from_connection_string(STORAGE_CONN)
        blob_client = svc.get_blob_client(container="input", blob=blob_name)
        blob_client.upload_blob(csv_bytes, overwrite=True)

        # Poll Cosmos DB for up to 90 seconds
        cosmos = CosmosClient.from_connection_string(COSMOS_CONN)
        container = (cosmos
                     .get_database_client(COSMOS_DB)
                     .get_container_client(COSMOS_CONTAINER))

        doc = None
        for _ in range(18):
            time.sleep(5)
            try:
                doc = container.read_item(item=blob_name, partition_key=blob_name)
                break
            except Exception:
                continue

        assert doc is not None, f"Inference document not found in Cosmos DB after 90s for {blob_name}"
        assert doc["record_count"] == 5
        assert doc["model_version"] is not None
        assert doc["latency_ms"] > 0

        # Cleanup
        blob_client.delete_blob()
        container.delete_item(item=blob_name, partition_key=blob_name)

    def test_invalid_csv_is_rejected(self):
        """A CSV with wrong columns should land in rejected/, not trigger inference."""
        from azure.storage.blob import BlobServiceClient

        blob_name = f"e2e_bad_{uuid.uuid4().hex[:8]}.csv"
        bad_csv = b"wrong_col1,wrong_col2\n1,2\n3,4\n"

        svc = BlobServiceClient.from_connection_string(STORAGE_CONN)
        blob_client = svc.get_blob_client(container="input", blob=blob_name)
        blob_client.upload_blob(bad_csv, overwrite=True)

        time.sleep(15)

        rejected_client = svc.get_blob_client(container="rejected", blob=blob_name)
        assert rejected_client.exists(), "Invalid blob should have been moved to rejected/"

        # Cleanup
        rejected_client.delete_blob()
