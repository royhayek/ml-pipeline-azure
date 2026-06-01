# Demonstration — End-to-End Pipeline Walkthrough

This document satisfies **deliverable D3** of the project: annotated screenshots
demonstrating the full pipeline running on Microsoft Azure.

Live environment (`switzerlandnorth`, resource group `rg-mlpipeline-prod`):

| Component | URL / Identifier |
|-----------|------------------|
| ML API (direct) | `https://ca-mlapi.orangesky-cc1a99c3.switzerlandnorth.azurecontainerapps.io` |
| ML API (via APIM) | `https://apim-mlpipeline-aa8229.azure-api.net/mlapi` |
| Function App | `https://func-mlpipeline-aa8229.azurewebsites.net` |
| Blob input container | `stmlpipeaa8229.blob.core.windows.net/input/` |
| Cosmos DB | `cosmos-mlpipeline.documents.azure.com` (Free Tier) |
| Application Insights | `appi-mlpipeline` + `func-mlpipeline-aa8229` (Function-bound) |

---

## Scenario 1 — Full CI/CD GitHub Actions deployment

The repository contains two workflows under `.github/workflows/`:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Every push and PR | flake8 lint, pytest, Docker image smoke build, Vite frontend build |
| `deploy.yml` | Push to `main` | Build/push image to ACR, deploy Container Apps + Functions, run smoke tests |

### What the CI workflow runs (`ci.yml`)

```
jobs:
  test-and-lint:     # Python: pytest + flake8 + docker build
  build-frontend:    # Node: npm ci + tsc + vite build
```

### What the CD workflow runs (`deploy.yml`)

```
jobs:
  build-and-push:    # docker build -> push to ACR
  deploy-staging:    # az containerapp update + func azure functionapp publish
  deploy-prod:       # Manual approval gate -> same steps for production
```

### Screenshots to capture

> **Screenshot 1.1** — GitHub Actions tab showing a successful `ci.yml` run
> with all jobs green. File: `docs/demo/ci_run_success.png`

> **Screenshot 1.2** — GitHub Actions tab showing the `deploy.yml` run with
> the manual approval gate before the `prod` environment.
> File: `docs/demo/deploy_run_with_approval.png`

> **Screenshot 1.3** — The "Environments" page in GitHub repo settings showing
> both `staging` and `prod` environments configured.
> File: `docs/demo/github_environments.png`

---

## Scenario 2 — File upload propagating to Cosmos DB

This is the core event-driven flow:

```
Blob upload (input/) -> Event Grid -> Dispatcher Function -> Storage Queue
                                                         |
                                                         v
                                       Worker Function -> ML API (APIM -> Container Apps)
                                                         |
                                                         v
                                    output/ JSON  +  HuggingFace summary
                                                         |
                                                         v
                                                    Cosmos DB
```

### Step 1 — Upload a CSV to Blob Storage

Open Storage Explorer or Azure Portal, navigate to `stmlpipeaa8229 -> Containers -> input/`,
upload a CSV file with the required schema (see `model/data/sample_weather.csv`).

> **Screenshot 2.1** — Azure Portal showing the file `weather_demo.csv` uploaded
> to the `input/` container with timestamp visible.
> File: `docs/demo/blob_upload.png`

### Step 2 — Event Grid fires, dispatcher validates

Within seconds, Event Grid invokes the dispatcher. Open **Application Insights**
of the Function App, run this query in Logs:

```kusto
requests
| where timestamp > ago(15m) and name == "dispatcher"
| project timestamp, success, duration, resultCode
| order by timestamp desc
```

> **Screenshot 2.2** — App Insights Logs showing dispatcher invocations
> succeeding with `success=True`.
> File: `docs/demo/dispatcher_invocations.png`

### Step 3 — Queue message picked up by worker

```kusto
requests
| where timestamp > ago(15m) and name == "worker"
| project timestamp, success, duration
| order by timestamp desc
```

> **Screenshot 2.3** — App Insights Logs showing worker invocations matching
> the dispatcher count.
> File: `docs/demo/worker_invocations.png`

### Step 4 — Cosmos DB record appears

Open **Cosmos DB -> Data Explorer -> mlpipeline -> inferences**, refresh, and
the newly uploaded blob should appear as a document keyed by `blob_name`.

> **Screenshot 2.4** — Cosmos DB Data Explorer showing the new record with
> fields: `id`, `blob_name`, `predictions`, `model_version`, `latency_ms`,
> `confidence_score`, `hf_summary`.
> File: `docs/demo/cosmos_record.png`

### Step 5 — End-to-end timing

The full flow (blob upload -> visible in Cosmos) completes in under 10
seconds for cold-start scenarios, ~2 seconds when functions and Container App
are warm.

---

## Scenario 3 — Live React Dashboard

The dashboard is built with Vite + React + TypeScript + Tailwind + Recharts.
It polls `/api/recent` every 30 seconds.

### Running it locally against the live Azure backend

```bash
cd web
npm ci
VITE_API_URL="https://func-mlpipeline-aa8229.azurewebsites.net" npm run dev
# Open http://localhost:5173
```

> **Screenshot 3.1** — Dashboard at `localhost:5173` showing real-time data:
> 6 stat cards (Files processed, Predictions made, Avg latency, Avg predicted
> temp, A/B split with v1 + v2 visible, DB read latency), bar chart of
> predicted temperatures, area chart of latency, table of recent batches with
> HuggingFace summaries.
> File: `docs/demo/dashboard_live.png`

### Note on Static Web App deployment

The dashboard was not deployed to the actual Azure Static Web App resource:
`Microsoft.Web/staticSites` is only available in five Azure regions
(`centralus`, `eastus2`, `westus2`, `westeurope`, `eastasia`), and the
Azure for Students subscription policy blocks all of them with
`RequestDisallowedByAzure`. See README for the full explanation.

---

## Scenario 4 — Application Insights dashboard and alert firing

### 4.1 — Application Insights dashboard

Three KQL queries (already captured in `docs/kql/`):

- `inference_per_hour.png` — requests per hour (timechart)
- `top5_slowest.png` — top 5 slowest operations by p95 latency
- `http_status_distribution.png` — status code piechart (100% success)

### 4.2 — Active alerts configured

```bash
az monitor metrics alert list --resource-group rg-mlpipeline-prod
```

Two alerts are configured on the Function App's Application Insights:

| Alert | Condition | Window | Severity |
|-------|-----------|--------|----------|
| `alert-high-error-rate` | `count requests/failed > 5` | 5 min | 2 (Warning) |
| `alert-high-p95-latency` | `avg requests/duration > 2000 ms` | 5 min | 2 (Warning) |

> **Screenshot 4.1** — Azure Portal showing both alert rules in the
> "Alert rules" page of the resource group, with state "Enabled".
> File: `docs/demo/alerts_configured.png`

### 4.3 — Simulating an alert firing

The error-rate alert fires when the worker can't reach the ML API. To
simulate this, we can disable the Container App ingress briefly, then upload
a few CSVs. Workers will fail, the count of failed requests will exceed the
threshold, and the alert state will flip to "Fired".

```bash
# 1. Simulate downtime
az containerapp ingress disable \
  --name ca-mlapi --resource-group rg-mlpipeline-prod

# 2. Upload 6 CSVs to trigger 6 failing worker runs
for i in {1..6}; do
  az storage blob upload \
    --container-name input \
    --name "fail_test_$i.csv" \
    --file model/data/sample_weather.csv \
    --connection-string "$STORAGE_CONN" --overwrite
  sleep 5
done

# 3. Wait ~6 minutes for the alert evaluation window
# Then check alert state:
az monitor metrics alert show \
  --name alert-high-error-rate \
  --resource-group rg-mlpipeline-prod \
  --query "{name:name, lastFired:lastUpdatedTime}"

# 4. Re-enable ingress
az containerapp ingress enable \
  --name ca-mlapi --resource-group rg-mlpipeline-prod \
  --type external --target-port 8000
```

> **Screenshot 4.2** — Azure Portal showing `alert-high-error-rate` in the
> "Fired" state, with the recent failed requests visible in the metric chart
> below. File: `docs/demo/alert_fired.png`

### 4.4 — Custom metrics emitted

Worker function emits three custom metrics:

- `inference_count` — total successful predictions
- `model_latency_ms` — duration of ML API call
- `api_error` — count of failed ML API calls

Query in App Insights:

```kusto
customMetrics
| where timestamp > ago(1h) and name in ("inference_count", "model_latency_ms", "api_error")
| summarize sum(value) by name, bin(timestamp, 5m)
| render timechart
```

> **Screenshot 4.3** — App Insights chart showing the three custom metrics
> over the demo session.
> File: `docs/demo/custom_metrics_chart.png`

---

## Summary table — every screenshot required

| File | Source | Status |
|------|--------|--------|
| `docs/demo/ci_run_success.png` | GitHub Actions tab | TODO (after push) |
| `docs/demo/deploy_run_with_approval.png` | GitHub Actions tab | TODO (after push) |
| `docs/demo/github_environments.png` | GitHub repo settings | TODO (after push) |
| `docs/demo/blob_upload.png` | Azure Portal | TODO (browser) |
| `docs/demo/dispatcher_invocations.png` | App Insights Logs | TODO (browser) |
| `docs/demo/worker_invocations.png` | App Insights Logs | TODO (browser) |
| `docs/demo/cosmos_record.png` | Cosmos Data Explorer | TODO (browser) |
| `docs/demo/dashboard_live.png` | `localhost:5173` | TODO (browser) |
| `docs/demo/alerts_configured.png` | Azure Portal | TODO (browser) |
| `docs/demo/alert_fired.png` | Azure Portal (after simulation) | TODO (browser) |
| `docs/demo/custom_metrics_chart.png` | App Insights Logs | TODO (browser) |
| `docs/kql/inference_per_hour.png` | App Insights Logs | DONE |
| `docs/kql/top5_slowest.png` | App Insights Logs | DONE |
| `docs/kql/http_status_distribution.png` | App Insights Logs | DONE |
