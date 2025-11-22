# Kubernetes Deployment Guide

## 🚀 Multi-User Engineering Scene Graph System - Azure Deployment

### Prerequisites

- **Azure CLI** installed and configured
- **Docker** installed for building images
- **kubectl** configured for your AKS cluster
- **Azure Container Registry** (ACR) created
- **Azure PostgreSQL** flexible server provisioned
- **Neo4j Aura** instance (external)

## 📦 Container Images

### Building Images

```bash
# Build backend image
docker build -f Dockerfile.backend -t building-intelligence-backend:latest .

# Build frontend image  
docker build -f frontend/Dockerfile -t building-intelligence-frontend:latest ./frontend

# Tag for Azure Container Registry
docker tag building-intelligence-backend:latest your-registry.azurecr.io/building-intelligence-backend:latest
docker tag building-intelligence-frontend:latest your-registry.azurecr.io/building-intelligence-frontend:latest

# Push to ACR
az acr login --name your-registry
docker push your-registry.azurecr.io/building-intelligence-backend:latest
docker push your-registry.azurecr.io/building-intelligence-frontend:latest
```

## ☁️ Azure Infrastructure Setup

### 1. Create Azure PostgreSQL

```bash
# Create PostgreSQL flexible server
az postgres flexible-server create \
  --resource-group your-rg \
  --name your-postgres-server \
  --location eastus \
  --admin-user pgadmin \
  --admin-password 'YourSecurePassword!' \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 15

# Create database
az postgres flexible-server db create \
  --resource-group your-rg \
  --server-name your-postgres-server \
  --database-name building_intelligence
```

### 2. Create AKS Cluster

```bash
# Create AKS cluster with Application Gateway ingress
az aks create \
  --resource-group your-rg \
  --name your-aks-cluster \
  --node-count 2 \
  --node-vm-size Standard_B2s \
  --enable-addons ingress-appgw \
  --appgw-name your-app-gateway \
  --appgw-subnet-cidr "10.2.0.0/16" \
  --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group your-rg --name your-aks-cluster
```

## 🔧 Kubernetes Deployment

### 1. Update Configuration

Edit `k8s/configmap.yaml`:
```yaml
POSTGRES_HOST: "your-postgres-server.postgres.database.azure.com"
NEO4J_URI: "your-neo4j-aura-uri"
```

Edit `k8s/secrets.yaml` with base64 encoded values:
```bash
echo -n "your-openai-key" | base64
echo -n "your-neo4j-password" | base64
echo -n "your-jwt-secret" | base64
echo -n "your-postgres-password" | base64
```

Edit `k8s/backend-deployment.yaml` and `k8s/frontend-deployment.yaml`:
```yaml
image: your-registry.azurecr.io/building-intelligence-backend:latest
image: your-registry.azurecr.io/building-intelligence-frontend:latest
```

### 2. Deploy to Kubernetes

```bash
# Apply all manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml

# Check deployment status
kubectl get pods -n building-intelligence
kubectl get services -n building-intelligence
kubectl get ingress -n building-intelligence
```

## 🔍 Local Development with Docker

### Start with Docker Compose

```bash
# Start PostgreSQL + Backend + Frontend
docker-compose up -d

# Check logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Access application
# Frontend: http://localhost
# Backend API: http://localhost:8000
```

## 🗄️ Database Migration

### Initialize Database Schema

```bash
# Local development (SQLite fallback)
python -c "from auth_database import auth_db; auth_db.create_tables()"

# Production (PostgreSQL)
# Tables are auto-created on first startup
```

## 🧪 Testing Multi-User Features

### 1. Create Test User

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123", "email": "test@example.com"}'
```

### 2. Login and Get Token

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'
```

### 3. Create Building

```bash
curl -X POST "http://localhost:8000/buildings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"name": "Main Office Building", "address": "123 Main St"}'
```

## 📊 Monitoring & Health Checks

### Health Check Endpoints

- **Backend**: `GET /health`
- **Frontend**: `GET /health` (Nginx)
- **Database**: Built-in PostgreSQL health checks

### Kubernetes Monitoring

```bash
# Pod status
kubectl get pods -n building-intelligence -w

# Service endpoints
kubectl get endpoints -n building-intelligence

# Ingress status
kubectl describe ingress app-ingress -n building-intelligence

# Application logs
kubectl logs -f deployment/backend -n building-intelligence
kubectl logs -f deployment/frontend -n building-intelligence
```

## 🔄 CI/CD Pipeline (Optional)

### GitHub Actions Workflow

Create `.github/workflows/deploy.yml` for automated deployment:
- Build and push Docker images to ACR
- Update Kubernetes deployments
- Run health checks and integration tests

## 🏗️ Architecture Summary

```
Internet → Azure Application Gateway → AKS Cluster
├── Frontend Pods (Nginx + React)
├── Backend Pods (FastAPI + Python)
├── Azure PostgreSQL (User/Building/Drawing data)
└── Neo4j Aura (Scene Graphs) [External]
```

## 🔐 Security Considerations

- **JWT tokens** for authentication
- **Password hashing** with bcrypt
- **Non-root containers** for security
- **Network policies** for pod isolation
- **Secrets management** with Kubernetes secrets
- **HTTPS/TLS** termination at ingress

Ready for production deployment on Azure Kubernetes Service!