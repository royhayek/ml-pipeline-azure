# Azure Deployment Guide

Step-by-step `az` commands to deploy the full pipeline from scratch.

## Prerequisites

```bash
az login
az account set --subscription "<your-subscription-id>"

# Install extensions
az extension add --name containerapp --upgrade
az extension add --name application-insights --upgrade
```

---

## 1 — Resource group & core infrastructure

```bash
LOCATION="westeurope"
RG="rg-mlpipeline-prod"
SUFFIX="mlpipe$(openssl rand -hex 3)"   # unique suffix

az group create --name $RG --location $LOCATION

# Storage account (Blob + Queue)
az storage account create \
  --name "st${SUFFIX}" \
  --resource-group $RG \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --enable-hierarchical-namespace false

STORAGE_CONN=$(az storage account show-connection-string \
  --name "st${SUFFIX}" --resource-group $RG --query connectionString -o tsv)

# Blob containers
for container in input output models rejected; do
  az storage container create --name $container \
    --connection-string "$STORAGE_CONN"
done

# Storage Queue
az storage queue create --name ml-inference-queue \
  --connection-string "$STORAGE_CONN"
az storage queue create --name ml-inference-queue-poison \
  --connection-string "$STORAGE_CONN"
```

---

## 2 — Application Insights

```bash
az monitor app-insights component create \
  --app "appi-mlpipeline" \
  --resource-group $RG \
  --location $LOCATION \
  --kind web \
  --retention-time 30 \
  --ingestion-access Enabled

APPINSIGHTS_KEY=$(az monitor app-insights component show \
  --app "appi-mlpipeline" --resource-group $RG \
  --query instrumentationKey -o tsv)

# Set daily ingestion cap to 1 GB
az monitor app-insights component billing update \
  --app "appi-mlpipeline" --resource-group $RG \
  --cap 1 --stop-cap-at 1
```

---

## 3 — Azure Container Registry (ACR Basic)

```bash
ACR_NAME="acr${SUFFIX}"

az acr create \
  --name $ACR_NAME \
  --resource-group $RG \
  --sku Basic \
  --admin-enabled true

ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)

# Build and push the ML API image
az acr build \
  --registry $ACR_NAME \
  --image mlapi:v1.0.0 \
  ./api
```

---

## 4 — Container Apps environment + ML API

```bash
# Container Apps environment
az containerapp env create \
  --name "cae-mlpipeline" \
  --resource-group $RG \
  --location $LOCATION

# Deploy the ML API
az containerapp create \
  --name "ca-mlapi" \
  --resource-group $RG \
  --environment "cae-mlpipeline" \
  --image "${ACR_LOGIN_SERVER}/mlapi:v1.0.0" \
  --registry-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_NAME \
  --registry-password $ACR_PASSWORD \
  --cpu 0.25 --memory 0.5Gi \
  --min-replicas 0 --max-replicas 3 \
  --scale-rule-name "queue-based" \
  --scale-rule-type "http" \
  --scale-rule-http-concurrency 10 \
  --ingress external --target-port 8000 \
  --env-vars \
      MODEL_PATH=/app/model_v1.0.0.pkl \
      MODEL_VERSION=1.0.0 \
      API_VERSION=1.0.0 \
      APPINSIGHTS_INSTRUMENTATIONKEY=$APPINSIGHTS_KEY

ML_API_URL=$(az containerapp show \
  --name "ca-mlapi" --resource-group $RG \
  --query properties.configuration.ingress.fqdn -o tsv)
ML_API_URL="https://${ML_API_URL}"
echo "ML API URL: $ML_API_URL"
```

---

## 5 — Cosmos DB (Free Tier)

```bash
az cosmosdb create \
  --name "cosmos-mlpipeline" \
  --resource-group $RG \
  --kind GlobalDocumentDB \
  --enable-free-tier true \
  --default-consistency-level Session

az cosmosdb sql database create \
  --account-name "cosmos-mlpipeline" \
  --resource-group $RG \
  --name "mlpipeline"

az cosmosdb sql container create \
  --account-name "cosmos-mlpipeline" \
  --resource-group $RG \
  --database-name "mlpipeline" \
  --name "inferences" \
  --partition-key-path "/blob_name" \
  --throughput 400

COSMOS_CONN=$(az cosmosdb keys list \
  --name "cosmos-mlpipeline" --resource-group $RG \
  --type connection-strings \
  --query connectionStrings[0].connectionString -o tsv)
```

---

## 6 — Azure Functions (dispatcher + worker + http-api)

```bash
FUNC_STORAGE="stfunc${SUFFIX}"
az storage account create \
  --name $FUNC_STORAGE --resource-group $RG \
  --location $LOCATION --sku Standard_LRS

# Dispatcher function app
az functionapp create \
  --name "func-dispatcher-${SUFFIX}" \
  --resource-group $RG \
  --consumption-plan-location $LOCATION \
  --runtime python --runtime-version 3.11 \
  --storage-account $FUNC_STORAGE \
  --os-type Linux \
  --functions-version 4

az functionapp config appsettings set \
  --name "func-dispatcher-${SUFFIX}" --resource-group $RG \
  --settings \
    AzureWebJobsStorage="$STORAGE_CONN" \
    STORAGE_CONNECTION_STRING="$STORAGE_CONN" \
    QUEUE_NAME="ml-inference-queue" \
    APPINSIGHTS_INSTRUMENTATIONKEY="$APPINSIGHTS_KEY"

# Worker function app
az functionapp create \
  --name "func-worker-${SUFFIX}" \
  --resource-group $RG \
  --consumption-plan-location $LOCATION \
  --runtime python --runtime-version 3.11 \
  --storage-account $FUNC_STORAGE \
  --os-type Linux \
  --functions-version 4

az functionapp config appsettings set \
  --name "func-worker-${SUFFIX}" --resource-group $RG \
  --settings \
    AzureWebJobsStorage="$STORAGE_CONN" \
    STORAGE_CONNECTION_STRING="$STORAGE_CONN" \
    COSMOS_CONNECTION_STRING="$COSMOS_CONN" \
    ML_API_URL="$ML_API_URL" \
    QUEUE_NAME="ml-inference-queue" \
    APPINSIGHTS_INSTRUMENTATIONKEY="$APPINSIGHTS_KEY"
```

---

## 7 — Event Grid subscription

```bash
STORAGE_RESOURCE_ID=$(az storage account show \
  --name "st${SUFFIX}" --resource-group $RG --query id -o tsv)

FUNC_DISPATCHER_ID=$(az functionapp function show \
  --name "func-dispatcher-${SUFFIX}" \
  --resource-group $RG \
  --function-name dispatcher \
  --query id -o tsv)

az eventgrid event-subscription create \
  --name "blob-created-sub" \
  --source-resource-id $STORAGE_RESOURCE_ID \
  --endpoint $FUNC_DISPATCHER_ID \
  --endpoint-type azurefunction \
  --included-event-types Microsoft.Storage.BlobCreated \
  --subject-begins-with "/blobServices/default/containers/input/"
```

---

## 8 — Static Web App

```bash
# Deploy from the web/ directory
az staticwebapp create \
  --name "swa-mlpipeline" \
  --resource-group $RG \
  --location "westeurope" \
  --source "https://github.com/<org>/<repo>" \
  --branch main \
  --app-location "/web" \
  --api-location "/functions" \
  --output-location ""
```

---

## 9 - Bonus: API Management Consumption (+1)

```bash
# Create APIM Consumption (free up to 1M calls/month)
az apim create \
  --name apim-mlpipeline-aa8229 \
  --resource-group $RG \
  --publisher-name "ML Pipeline Team" \
  --publisher-email "royhayek27@gmail.com" \
  --sku-name Consumption \
  --location $LOCATION

APIM_URL="https://apim-mlpipeline-aa8229.azure-api.net"

# Import the ML API from its live OpenAPI spec
az apim api import \
  --service-name apim-mlpipeline-aa8229 \
  --resource-group $RG \
  --path mlapi \
  --specification-format OpenApiJson \
  --specification-url "https://ca-mlapi.orangesky-cc1a99c3.switzerlandnorth.azurecontainerapps.io/openapi.json" \
  --api-id mlapi \
  --display-name "Weather ML API" \
  --protocols https

# Apply quota + rate-limit policy (docs/apim_policy.xml)
az apim api policy create \
  --service-name apim-mlpipeline-aa8229 \
  --resource-group $RG \
  --api-id mlapi \
  --value @docs/apim_policy.xml

# Create a product and subscription
az apim product create \
  --service-name apim-mlpipeline-aa8229 \
  --resource-group $RG \
  --product-id standard \
  --product-name "Standard" \
  --subscription-required true \
  --approval-required false \
  --state published

az apim product api add \
  --service-name apim-mlpipeline-aa8229 \
  --resource-group $RG \
  --product-id standard \
  --api-id mlapi

# Get subscription key
APIM_KEY=$(az apim subscription list \
  --service-name apim-mlpipeline-aa8229 \
  --resource-group $RG \
  --query "[0].primaryKey" -o tsv)

# Test through APIM
curl -H "Ocp-Apim-Subscription-Key: $APIM_KEY" \
  "$APIM_URL/mlapi/health"

# Update worker to use APIM endpoint
az functionapp config appsettings set \
  --name func-mlpipeline-aa8229 \
  --resource-group $RG \
  --settings \
    ML_API_URL="$APIM_URL/mlapi" \
    APIM_SUBSCRIPTION_KEY="$APIM_KEY"
```

---

## 10 - Bonus: Multi-region Cosmos DB (+0.5)

```bash
# Add northeurope as a read-only replica
az cosmosdb update \
  --name cosmos-mlpipeline \
  --resource-group $RG \
  --locations \
    regionName=switzerlandnorth failoverPriority=0 isZoneRedundant=False \
    regionName=northeurope      failoverPriority=1 isZoneRedundant=False

# Update HTTP API function to prefer northeurope reads
az functionapp config appsettings set \
  --name func-mlpipeline-aa8229 \
  --resource-group $RG \
  --settings COSMOS_PREFERRED_REGION="North Europe"
```

---

## Teardown (end of session)

```bash
az group delete --name $RG --yes --no-wait
```
