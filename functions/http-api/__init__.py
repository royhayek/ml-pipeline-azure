"""
HTTP API Function - GET /api/recent

Returns the 20 most recent inference records from Cosmos DB.
Used by the Static Web App dashboard.

Rate-limited to 60 requests/minute per client IP (in-memory, best-effort).
Includes read latency measurement to demonstrate multi-region Cosmos DB benefit.

Environment variables:
    COSMOS_CONNECTION_STRING
    COSMOS_DATABASE     (default: mlpipeline)
    COSMOS_CONTAINER    (default: inferences)
"""

import json
import logging
import os
import time
from collections import defaultdict

import azure.functions as func
from azure.cosmos import CosmosClient

logger = logging.getLogger(__name__)

COSMOS_CONN = os.environ["COSMOS_CONNECTION_STRING"]
COSMOS_DB = os.environ.get("COSMOS_DATABASE", "mlpipeline")
COSMOS_CONTAINER = os.environ.get("COSMOS_CONTAINER", "inferences")
COSMOS_REGION = os.environ.get("COSMOS_PREFERRED_REGION", "Switzerland North")
RATE_LIMIT = 60  # requests per minute per IP

# In-memory rate limiter: {ip: [timestamps]}
_rate_store: dict[str, list[float]] = defaultdict(list)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Content-Type": "application/json",
}


def _is_rate_limited(client_ip: str) -> bool:
    now = time.monotonic()
    window = now - 60.0
    timestamps = [t for t in _rate_store[client_ip] if t > window]
    _rate_store[client_ip] = timestamps
    if len(timestamps) >= RATE_LIMIT:
        return True
    _rate_store[client_ip].append(now)
    return False


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=CORS_HEADERS)

    client_ip = req.headers.get("X-Forwarded-For", "unknown").split(",")[0].strip()
    if _is_rate_limited(client_ip):
        return func.HttpResponse(
            json.dumps({"error": "Rate limit exceeded (60 req/min)"}),
            status_code=429,
            headers=CORS_HEADERS,
        )

    try:
        t0 = time.monotonic()
        cosmos = CosmosClient.from_connection_string(
            COSMOS_CONN,
            preferred_locations=[COSMOS_REGION],
        )
        container = cosmos.get_database_client(COSMOS_DB).get_container_client(COSMOS_CONTAINER)

        query = """
            SELECT TOP 20
                c.id, c.blob_name, c.timestamp, c.model_version,
                c.record_count, c.latency_ms, c.confidence_score,
                c.hf_summary
            FROM c
            ORDER BY c.timestamp DESC
        """
        items = list(container.query_items(query=query, enable_cross_partition_query=True))
        read_latency_ms = round((time.monotonic() - t0) * 1000, 1)

        return func.HttpResponse(
            json.dumps({
                "data": items,
                "count": len(items),
                "meta": {
                    "read_region": COSMOS_REGION,
                    "read_latency_ms": read_latency_ms,
                },
            }),
            status_code=200,
            headers=CORS_HEADERS,
        )
    except Exception as exc:
        logger.error("Cosmos query failed: %s", exc)
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            headers=CORS_HEADERS,
        )
