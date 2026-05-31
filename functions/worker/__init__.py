"""
Worker Azure Function — Queue trigger.

Reads a message from the Storage Queue, downloads the CSV blob,
calls the ML API /predict endpoint, writes the JSON result to output/,
and stores inference metadata in Cosmos DB.

Idempotency: uses blob_name as the Cosmos DB document ID.
Dead-letter: after 5 failed attempts, the message moves to the poison queue.

Environment variables (Application Settings):
    STORAGE_CONNECTION_STRING   Azure Storage connection string
    ML_API_URL                  Base URL of the Container Apps ML API
    COSMOS_CONNECTION_STRING    Cosmos DB connection string
    COSMOS_DATABASE             Database name (default: mlpipeline)
    COSMOS_CONTAINER            Container name (default: inferences)
    QUEUE_NAME                  Source queue name
    APPINSIGHTS_INSTRUMENTATIONKEY
"""

import csv
import io
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

import azure.functions as func
import requests
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient, PartitionKey, exceptions as cosmos_exc
from opencensus.ext.azure import metrics_exporter
from opencensus.stats import aggregation, measure, stats, view

logger = logging.getLogger(__name__)

STORAGE_CONN = os.environ["STORAGE_CONNECTION_STRING"]
ML_API_URL = os.environ["ML_API_URL"].rstrip("/")
COSMOS_CONN = os.environ["COSMOS_CONNECTION_STRING"]
COSMOS_DB = os.environ.get("COSMOS_DATABASE", "mlpipeline")
COSMOS_CONTAINER = os.environ.get("COSMOS_CONTAINER", "inferences")

# ---------------------------------------------------------------------------
# Custom Application Insights metrics
# ---------------------------------------------------------------------------
_APPINSIGHTS_KEY = os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY", "")

if _APPINSIGHTS_KEY:
    _exporter = metrics_exporter.new_metrics_exporter(
        connection_string=f"InstrumentationKey={_APPINSIGHTS_KEY}"
    )
    _stats = stats.Stats()
    _view_manager = _stats.view_manager
    _stats_recorder = _stats.stats_recorder

    m_inference_count = measure.MeasureInt("inference_count", "Number of inferences", "1")
    m_model_latency = measure.MeasureFloat("model_latency_ms", "Model inference latency", "ms")
    m_api_error = measure.MeasureInt("api_error", "ML API call errors", "1")

    inference_view = view.View("inference_count", "Total inferences",
                               [], m_inference_count, aggregation.SumAggregation())
    latency_view = view.View("model_latency_ms", "Model latency distribution",
                             [], m_model_latency, aggregation.LastValueAggregation())
    error_view = view.View("api_error", "API error count",
                           [], m_api_error, aggregation.SumAggregation())

    _view_manager.register_view(inference_view)
    _view_manager.register_view(latency_view)
    _view_manager.register_view(error_view)
    _view_manager.register_exporter(_exporter)


def _record_metric(m, value):
    if not _APPINSIGHTS_KEY:
        return
    mmap = _stats_recorder.new_measurement_map()
    mmap.measure_put(m, value)
    mmap.record()


# ---------------------------------------------------------------------------
# Cosmos DB helpers
# ---------------------------------------------------------------------------
def _get_cosmos_container():
    client = CosmosClient.from_connection_string(COSMOS_CONN)
    db = client.get_database_client(COSMOS_DB)
    return db.get_container_client(COSMOS_CONTAINER)


def _upsert_inference(doc: dict) -> None:
    container = _get_cosmos_container()
    try:
        container.upsert_item(doc)
    except cosmos_exc.CosmosHttpResponseError as exc:
        logger.error("Cosmos upsert failed. id=%s error=%s", doc.get("id"), exc)
        raise


# ---------------------------------------------------------------------------
# CSV → predict request conversion
# ---------------------------------------------------------------------------
def _csv_to_records(csv_bytes: bytes) -> list[dict]:
    reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8")))
    records = []
    for row in reader:
        records.append({
            "temperature_c": float(row["temperature_c"]),
            "humidity": float(row["humidity"]),
            "wind_speed_kmh": float(row["wind_speed_kmh"]),
            "wind_bearing_deg": float(row["wind_bearing_deg"]),
            "visibility_km": float(row["visibility_km"]),
            "pressure_mb": float(row["pressure_mb"]),
            "is_rain": int(row["is_rain"]),
            "hour": int(row["hour"]),
            "month": int(row["month"]),
        })
    return records


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------
def main(msg: func.QueueMessage) -> None:
    payload = json.loads(msg.get_body().decode("utf-8"))
    blob_name: str = payload["blob_name"]
    blob_url: str = payload["blob_url"]

    logger.info("Worker triggered. blob=%s dequeue_count=%d", blob_name, msg.dequeue_count)

    # --- Download blob ---
    try:
        svc = BlobServiceClient.from_connection_string(STORAGE_CONN)
        blob_client = svc.get_blob_client(container="input", blob=blob_name)
        csv_bytes = blob_client.download_blob().readall()
    except Exception as exc:
        logger.error("Blob download failed. blob=%s error=%s", blob_name, exc)
        raise

    # --- Call ML API ---
    t0 = time.monotonic()
    try:
        records = _csv_to_records(csv_bytes)
        response = requests.post(
            f"{ML_API_URL}/predict",
            json={"records": records},
            timeout=30,
        )
        response.raise_for_status()
        api_result = response.json()
        latency_ms = round((time.monotonic() - t0) * 1000, 2)
        _record_metric(m_model_latency, latency_ms)
        _record_metric(m_inference_count, 1)
    except Exception as exc:
        latency_ms = round((time.monotonic() - t0) * 1000, 2)
        _record_metric(m_api_error, 1)
        logger.error("ML API call failed. blob=%s error=%s", blob_name, exc)
        raise

    predictions = api_result.get("predictions", [])
    model_version = api_result.get("model_version", "unknown")

    # --- Write result to output/ blob ---
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_name = f"{blob_name.rsplit('.', 1)[0]}_{timestamp}.json"
    result_doc = {
        "blob_name": blob_name,
        "predictions": predictions,
        "model_version": model_version,
        "latency_ms": latency_ms,
        "record_count": len(predictions),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        output_client = svc.get_blob_client(container="output", blob=output_name)
        output_client.upload_blob(json.dumps(result_doc, indent=2), overwrite=True)
        logger.info("Result written to output. blob=%s", output_name)
    except Exception as exc:
        logger.error("Output blob write failed. blob=%s error=%s", output_name, exc)
        raise

    # --- Persist metadata to Cosmos DB (idempotent upsert) ---
    cosmos_doc = {
        "id": blob_name,  # idempotency key
        "blob_name": blob_name,
        "output_blob": output_name,
        "timestamp": result_doc["timestamp"],
        "model_version": model_version,
        "record_count": len(predictions),
        "latency_ms": latency_ms,
        "confidence_score": round(sum(predictions) / len(predictions), 4) if predictions else None,
    }
    _upsert_inference(cosmos_doc)
    logger.info("Cosmos DB upsert complete. id=%s", cosmos_doc["id"])
