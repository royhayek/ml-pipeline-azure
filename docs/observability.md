# Observability — Application Insights

## Architecture

All active components (Dispatcher Function, Worker Function, Container Apps ML API)
are connected to the same **Application Insights** workspace via the
`APPINSIGHTS_INSTRUMENTATIONKEY` environment variable.

The ingestion cap is set to **1 GB/day** to stay within the free 5 GB/month quota.

---

## Custom metrics emitted by the Worker Function

| Metric name | Type | Description |
|---|---|---|
| `inference_count` | Counter | Incremented once per successfully processed CSV file |
| `model_latency_ms` | Gauge | End-to-end latency of the POST /predict call in milliseconds |
| `api_error` | Counter | Incremented when the ML API call fails (any exception) |

---

## Alerts

### Alert 1 — High API error rate

| Field | Value |
|---|---|
| Signal | Custom metric `api_error` |
| Condition | Sum > 5 % of `inference_count` over a **5-minute** sliding window |
| Severity | 2 (Warning) |
| Action | Email to team |

```bash
az monitor metrics alert create \
  --name "alert-high-error-rate" \
  --resource-group $RG \
  --scopes "/subscriptions/{sub}/resourceGroups/$RG/providers/Microsoft.Insights/components/appi-mlpipeline" \
  --condition "count customMetrics/api_error > 0" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --severity 2 \
  --description "API error rate exceeded 5% over 5 minutes"
```

### Alert 2 — p95 model latency > 2 s

| Field | Value |
|---|---|
| Signal | Custom metric `model_latency_ms` |
| Condition | p95 > 2000 ms over a **5-minute** sliding window |
| Severity | 2 (Warning) |
| Action | Email to team |

```bash
az monitor metrics alert create \
  --name "alert-high-latency" \
  --resource-group $RG \
  --scopes "/subscriptions/{sub}/resourceGroups/$RG/providers/Microsoft.Insights/components/appi-mlpipeline" \
  --condition "P95 customMetrics/model_latency_ms > 2000" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --severity 2 \
  --description "P95 model latency exceeded 2s over 5 minutes"
```

---

## KQL queries

### Query 1 — Inference count per hour

```kusto
customEvents
| where name == "inference_completed"
| summarize count() by bin(timestamp, 1h)
| render timechart
```

> Screenshot: `docs/kql/inference_per_hour.png`

### Query 2 — Top 5 slowest files (p95 latency)

```kusto
customMetrics
| where name == "model_latency_ms"
| summarize p95 = percentile(value, 95) by tostring(customDimensions["blob_name"])
| top 5 by p95 desc
| project blob_name = Column1, p95_latency_ms = p95
```

> Screenshot: `docs/kql/top5_slowest.png`

### Query 3 — HTTP status code distribution

```kusto
requests
| where cloud_RoleName has "ca-mlapi"
| summarize count() by resultCode
| render piechart
```

> Screenshot: `docs/kql/http_status_distribution.png`

---

## Azure dashboard setup

```bash
# Create a shared dashboard with the 3 key charts
az portal dashboard create \
  --resource-group $RG \
  --name "mlpipeline-dashboard" \
  --input-path docs/dashboard_definition.json
```

The dashboard includes:
- Inference count over time (line chart)
- Model latency histogram
- API error rate gauge
- Recent requests table
