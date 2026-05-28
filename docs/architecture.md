# Architecture

## Component flow

```
User
 │
 │  upload CSV
 ▼
┌─────────────────────────────┐
│  1. Azure Blob Storage      │  Container: input/
│     (LRS Standard)          │  Versioning: enabled
└──────────────┬──────────────┘
               │ Microsoft.Storage.BlobCreated
               ▼
┌─────────────────────────────┐
│  2. Event Grid              │  System topic on storage account
│     + Dispatcher Function   │  Validates: extension, size ≤ 10 MB,
│     (Event Grid trigger)    │  CSV schema (required columns present)
└──────────────┬──────────────┘
               │  invalid → rejected/ container
               │  valid   → enqueue
               ▼
┌─────────────────────────────┐
│  3. Azure Storage Queue     │  ml-inference-queue
│     (free tier)             │  Max retries: 5
│                             │  Poison queue: ml-inference-queue-poison
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  4. Worker Function         │  Queue trigger
│     (Queue trigger)         │  Idempotent (blob ID as dedup key)
│                             │  → calls ML API /predict
│                             │  → writes JSON to output/
│                             │  → writes metadata to Cosmos DB
└──────────────┬──────────────┘
               │  POST /predict
               ▼
┌─────────────────────────────┐
│  5. ML Inference API        │  FastAPI · multi-stage Docker image
│     Azure Container Apps    │  Autoscale: 0-3 replicas
│     (Consumption)           │  Endpoints: /health /version /predict /metrics
└──────────────┬──────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌────────────┐  ┌──────────────────┐
│ 6. Blob    │  │ 7. Cosmos DB     │
│  output/   │  │  (Free Tier)     │
│ JSON files │  │  inference meta  │
└────────────┘  └───────┬──────────┘
                        │ /api/recent (HTTP Function)
                        ▼
               ┌─────────────────┐
               │ 8. Static       │
               │  Web App (Free) │
               │  Dashboard      │
               └─────────────────┘
```

## Cross-cutting concerns

- **Application Insights**: logs, custom metrics, alerts from Functions and Container Apps
- **GitHub Actions**: CI (test + lint) on every PR; CD (build + deploy) on push to main
- **Environments**: staging and prod (prod requires manual approval gate)

## Azure resource group layout

```
rg-mlpipeline-dev   (development)
rg-mlpipeline-prod  (production)
├── stmlpipeline{suffix}      Storage Account
├── func-dispatcher           Function App (dispatcher)
├── func-worker               Function App (worker)
├── acr{suffix}               Container Registry (Basic)
├── ca-mlapi                  Container App (ML API)
├── cosmos-mlpipeline         Cosmos DB account (Free Tier)
├── swa-mlpipeline            Static Web App (Free)
└── appi-mlpipeline           Application Insights
```
