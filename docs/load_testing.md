# Load Testing — Autoscale Validation

## Overview

A Locust scenario fires **100 concurrent users** against the Container Apps ML API,
triggering autoscale from 0 to 3 replicas and generating Application Insights telemetry.

## Running the test

```bash
pip install locust==2.29.1

# Headless burst (100 users, 20/s spawn, 2 minutes)
locust -f tests/load_test.py \
       --host https://ca-mlapi.orangesky-cc1a99c3.switzerlandnorth.azurecontainerapps.io \
       --users 100 --spawn-rate 20 --run-time 2m --headless \
       --html docs/load_test_report.html

# Interactive web UI (open http://localhost:8089)
locust -f tests/load_test.py \
       --host https://ca-mlapi.orangesky-cc1a99c3.switzerlandnorth.azurecontainerapps.io
```

## What is tested

| Task | Weight | Description |
|------|--------|-------------|
| `/predict` (single) | 8 | One-record prediction — most common pattern |
| `/predict` (batch) | 3 | 5–20 records — simulates worker function calls |
| `/predict` (fixed) | 2 | Fixed sample — reproducible latency baseline |
| `/health` | 1 | Liveness probe |
| `/metrics` | 1 | Metrics scrape |

## Autoscale behaviour

Container Apps is configured with `minReplicas: 0 / maxReplicas: 3`.
Under burst load:

1. First request cold-starts the single replica (~5–15 s)
2. Concurrent HTTP requests trigger the scale-out rule
3. Replicas ramp up to 3 within ~30–60 s
4. After load ends, scale-in back to 0 within ~5 minutes

## KQL queries for analysing results

### Request throughput during load test
```kusto
requests
| where timestamp > ago(30m)
| summarize count() by bin(timestamp, 1m)
| render timechart
```

### p50 / p95 / p99 latency breakdown
```kusto
requests
| where timestamp > ago(30m) and name has "predict"
| summarize
    p50 = percentile(duration, 50),
    p95 = percentile(duration, 95),
    p99 = percentile(duration, 99)
  by bin(timestamp, 1m)
| render timechart
```

### Error rate during load
```kusto
requests
| where timestamp > ago(30m)
| summarize
    total = count(),
    errors = countif(success == false)
  by bin(timestamp, 1m)
| extend error_rate = round(100.0 * errors / total, 1)
| render timechart
```

## Screenshots

> Screenshots are captured after running the load test against the live Azure deployment.
> See `docs/load_test_report.html` for the full Locust HTML report.
