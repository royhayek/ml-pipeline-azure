"""
Dispatcher Azure Function — triggered by Event Grid on BlobCreated events.

Validates the uploaded blob (extension, size, CSV schema) and either:
  - Enqueues a processing message to the Storage Queue, or
  - Moves the file to the rejected/ container and logs the reason.

Environment variables (Application Settings):
    STORAGE_CONNECTION_STRING   Azure Storage connection string
    QUEUE_NAME                  Target queue name (default: ml-inference-queue)
    MAX_BLOB_SIZE_MB            Max allowed file size in MB (default: 10)
    ALLOWED_EXTENSIONS          Comma-separated list (default: csv)
    APPINSIGHTS_INSTRUMENTATIONKEY
"""

import json
import logging
import os

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueClient, BinaryBase64EncodePolicy

logger = logging.getLogger(__name__)

REQUIRED_CSV_COLUMNS = {
    "temperature_c",
    "humidity",
    "wind_speed_kmh",
    "wind_bearing_deg",
    "visibility_km",
    "pressure_mb",
    "is_rain",
    "hour",
    "month",
}

STORAGE_CONN = os.environ["STORAGE_CONNECTION_STRING"]
QUEUE_NAME = os.environ.get("QUEUE_NAME", "ml-inference-queue")
MAX_SIZE_MB = float(os.environ.get("MAX_BLOB_SIZE_MB", "10"))
ALLOWED_EXTS = {e.strip().lower() for e in os.environ.get("ALLOWED_EXTENSIONS", "csv").split(",")}


def _reject(blob_name: str, reason: str) -> None:
    """Move blob to the rejected/ container."""
    try:
        svc = BlobServiceClient.from_connection_string(STORAGE_CONN)
        src_blob = svc.get_blob_client(container="input", blob=blob_name)
        dst_blob = svc.get_blob_client(container="rejected", blob=blob_name)

        dst_blob.start_copy_from_url(src_blob.url)
        src_blob.delete_blob()
        logger.warning("Blob rejected and moved. blob=%s reason=%s", blob_name, reason)
    except Exception as exc:
        logger.error("Failed to move rejected blob. blob=%s error=%s", blob_name, exc)


def _validate_csv_header(blob_data: bytes) -> tuple[bool, str]:
    """Check that the CSV first line contains all required columns."""
    try:
        first_line = blob_data.split(b"\n")[0].decode("utf-8", errors="replace")
        columns = {c.strip().lower() for c in first_line.split(",")}
        missing = REQUIRED_CSV_COLUMNS - columns
        if missing:
            return False, f"Missing columns: {missing}"
        return True, ""
    except Exception as exc:
        return False, f"Could not parse CSV header: {exc}"


def main(event: func.EventGridEvent) -> None:
    data = event.get_json()
    blob_url: str = data.get("url", "")
    content_length: int = data.get("contentLength", 0)
    blob_name: str = blob_url.split("/input/")[-1] if "/input/" in blob_url else ""

    logger.info("Dispatcher triggered. blob=%s size=%d bytes", blob_name, content_length)

    # --- Extension check ---
    ext = blob_name.rsplit(".", 1)[-1].lower() if "." in blob_name else ""
    if ext not in ALLOWED_EXTS:
        _reject(blob_name, f"Invalid extension: .{ext}")
        return

    # --- Size check ---
    size_mb = content_length / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        _reject(blob_name, f"File too large: {size_mb:.1f} MB > {MAX_SIZE_MB} MB")
        return

    # --- Schema check (download first few bytes) ---
    try:
        svc = BlobServiceClient.from_connection_string(STORAGE_CONN)
        blob_client = svc.get_blob_client(container="input", blob=blob_name)
        # Read only enough for the header line (up to 2 KB)
        header_bytes = blob_client.download_blob(offset=0, length=2048).readall()
        valid, reason = _validate_csv_header(header_bytes)
        if not valid:
            _reject(blob_name, reason)
            return
    except Exception as exc:
        logger.error("Schema validation error. blob=%s error=%s", blob_name, exc)
        _reject(blob_name, f"Schema validation error: {exc}")
        return

    # --- Enqueue ---
    message = {
        "blob_name": blob_name,
        "blob_url": blob_url,
        "content_type": data.get("contentType", "text/csv"),
        "size_bytes": content_length,
        "enqueued_at": event.event_time.isoformat() if event.event_time else "",
    }
    try:
        queue_client = QueueClient.from_connection_string(
            STORAGE_CONN,
            QUEUE_NAME,
            message_encode_policy=BinaryBase64EncodePolicy(),
        )
        queue_client.send_message(json.dumps(message).encode("utf-8"))
        logger.info("Message enqueued. blob=%s queue=%s", blob_name, QUEUE_NAME)
    except Exception as exc:
        logger.error("Failed to enqueue message. blob=%s error=%s", blob_name, exc)
        raise
