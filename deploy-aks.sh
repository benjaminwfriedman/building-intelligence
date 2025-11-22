#!/bin/bash

# Engineering Scene Graph - AKS Deployment Script
# Usage: ./deploy-aks.sh [--services frontend,backend] [--push] [--remove] [--help]

set -e  # Exit on any error

# Configuration
ACR_NAME="hierarchicaldevregistry"
NAMESPACE="building-intelligence"

# Generate dynamic image tag from git commit + timestamp
if command -v git &> /dev/null && git rev-parse --git-dir > /dev/null 2>&1; then
    GIT_COMMIT=$(git rev-parse --short HEAD)
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    IMAGE_TAG="${GIT_COMMIT}-${TIMESTAMP}"
else
    # Fallback if not in git repo
    IMAGE_TAG="manual-$(date +%Y%m%d-%H%M%S)"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
SERVICES=""
PUSH_ONLY=false
REMOVE_IMAGES=false
DEPLOY_ALL=true
SECRETS_FILE="k8s/secrets.yaml"

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

show_help() {
    cat << EOF
🚀 Engineering Scene Graph - AKS Deployment Script

Usage: $0 [OPTIONS]

OPTIONS:
    --services <list>    Deploy specific services (comma-separated: frontend,backend,postgres)
                        Example: --services frontend,backend
                        Available: frontend, backend, postgres
                        Default: Deploy all services
    
    --push              Push images to ACR without deploying to AKS
    
    --remove            Remove local Docker images after push (saves disk space)
    
    --secrets-file <file>  Use specific secrets file (default: k8s/secrets.yaml)
                          Example: --secrets-file k8s/secrets.local.yaml
    
    --help              Show this help message

EXAMPLES:
    # Deploy everything to AKS
    $0
    
    # Build and deploy only backend
    $0 --services backend
    
    # Build and push images only (no AKS deployment)
    $0 --push
    
    # Build, push, deploy, and clean up local images
    $0 --services frontend,backend --remove
    
    # Deploy with custom secrets file
    $0 --secrets-file k8s/secrets.local.yaml
    
    # Push existing images without rebuilding
    $0 --push --remove

ENVIRONMENT VARIABLES:
    ACR_NAME           Azure Container Registry name (default: your-registry)
    
IMAGE TAGGING:
    Images are automatically tagged with: git-commit-timestamp
    Example: abc123ef-20251120-143022
    Override with: IMAGE_TAG=custom-tag ./deploy-aks.sh

PREREQUISITES:
    - Azure CLI logged in: az login
    - ACR access: az acr login --name \$ACR_NAME
    - kubectl configured for AKS cluster
    - Docker running
EOF
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Azure CLI is installed and logged in
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI not found. Please install Azure CLI."
        exit 1
    fi
    
    # Check if logged into Azure
    if ! az account show &> /dev/null; then
        log_error "Not logged into Azure. Run 'az login' first."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
    
    # Check if Docker BuildKit is available for multi-platform builds
    if ! docker buildx version &> /dev/null; then
        log_error "Docker BuildKit not available. Please update Docker Desktop."
        exit 1
    fi
    
    # Create and use multi-platform builder if needed
    if ! docker buildx inspect multiplatform-builder &> /dev/null; then
        log_info "Creating multi-platform builder..."
        docker buildx create --name multiplatform-builder --driver docker-container --bootstrap
    fi
    docker buildx use multiplatform-builder
    
    # Check if kubectl is configured
    if ! kubectl cluster-info &> /dev/null; then
        log_error "kubectl not configured or cluster not accessible."
        exit 1
    fi
    
    log_success "All prerequisites met"
}

login_to_acr() {
    log_info "Logging into Azure Container Registry..."
    if az acr login --name "$ACR_NAME" &> /dev/null; then
        log_success "Logged into ACR: $ACR_NAME"
    else
        log_error "Failed to login to ACR. Check ACR_NAME and permissions."
        exit 1
    fi
}

build_and_push_service() {
    local service=$1
    log_info "Building and pushing $service..."
    
    case $service in
        "backend")
            log_info "Building multi-platform backend image..."
            docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile.backend -t "$ACR_NAME.azurecr.io/building-intelligence-backend:$IMAGE_TAG" . --push
            log_success "Multi-platform backend image built and pushed"
            
            # Note: Multi-platform images can't be removed locally (they're manifests)
            ;;
            
        "frontend")
            log_info "Building multi-platform frontend image..."
            docker buildx build --platform linux/amd64,linux/arm64 -f frontend/Dockerfile -t "$ACR_NAME.azurecr.io/building-intelligence-frontend:$IMAGE_TAG" ./frontend --push
            log_success "Multi-platform frontend image built and pushed"
            
            # Note: Multi-platform images can't be removed locally (they're manifests)
            ;;
            
        *)
            log_error "Unknown service: $service"
            exit 1
            ;;
    esac
}

generate_manifests() {
    log_info "Generating Kubernetes manifests with image tag: $IMAGE_TAG"
    
    # Create temporary directory for generated manifests
    mkdir -p k8s/generated
    
    # Generate manifests using environment variable substitution
    export ACR_NAME IMAGE_TAG NAMESPACE
    
    if [[ -f k8s/backend-deployment.template.yaml ]]; then
        envsubst < k8s/backend-deployment.template.yaml > k8s/generated/backend-deployment.yaml
        log_success "Generated backend deployment manifest"
    fi
    
    if [[ -f k8s/frontend-deployment.template.yaml ]]; then
        envsubst < k8s/frontend-deployment.template.yaml > k8s/generated/frontend-deployment.yaml
        log_success "Generated frontend deployment manifest"
    fi
    
    if [[ -f k8s/ingress.template.yaml ]]; then
        envsubst < k8s/ingress.template.yaml > k8s/generated/ingress.yaml
        log_success "Generated ingress manifest"
    fi
    
    # Copy static manifests
    cp k8s/namespace.yaml k8s/generated/ 2>/dev/null || true
    cp k8s/persistent-volumes.yaml k8s/generated/ 2>/dev/null || true
    cp k8s/configmap.yaml k8s/generated/ 2>/dev/null || true
    
    # Copy specified secrets file
    if [[ -f "$SECRETS_FILE" ]]; then
        cp "$SECRETS_FILE" k8s/generated/secrets.yaml
        log_success "Using secrets file: $SECRETS_FILE"
    else
        log_error "Secrets file not found: $SECRETS_FILE"
        exit 1
    fi
}

deploy_to_aks() {
    local service=$1
    log_info "Deploying $service to AKS..."
    
    # Generate manifests first
    generate_manifests
    
    case $service in
        "backend")
            kubectl apply -f k8s/generated/backend-deployment.yaml
            kubectl rollout status deployment/backend -n "$NAMESPACE" --timeout=300s
            log_success "Backend deployed to AKS"
            ;;
            
        "frontend")
            kubectl apply -f k8s/generated/frontend-deployment.yaml
            kubectl rollout status deployment/frontend -n "$NAMESPACE" --timeout=300s
            log_success "Frontend deployed to AKS"
            ;;
            
        "postgres")
            kubectl apply -f k8s/postgres-deployment.yaml
            kubectl rollout status deployment/postgres -n "$NAMESPACE" --timeout=300s
            log_success "PostgreSQL deployed to AKS"
            ;;
            
        "all")
            # Deploy all Kubernetes resources
            log_info "Deploying all Kubernetes resources..."
            kubectl apply -f k8s/generated/namespace.yaml
            kubectl apply -f k8s/generated/persistent-volumes.yaml
            kubectl apply -f k8s/generated/secrets.yaml
            kubectl apply -f k8s/generated/configmap.yaml
            
            # Deploy PostgreSQL first (backend depends on it)
            kubectl apply -f k8s/postgres-deployment.yaml
            kubectl rollout status deployment/postgres -n "$NAMESPACE" --timeout=300s
            log_success "PostgreSQL ready"
            
            # Deploy application services
            kubectl apply -f k8s/generated/backend-deployment.yaml
            kubectl apply -f k8s/generated/frontend-deployment.yaml
            kubectl apply -f k8s/generated/ingress.yaml
            
            # Wait for rollouts
            kubectl rollout status deployment/backend -n "$NAMESPACE" --timeout=300s
            kubectl rollout status deployment/frontend -n "$NAMESPACE" --timeout=300s
            
            log_success "All resources deployed to AKS"
            ;;
            
        *)
            log_error "Unknown deployment target: $service"
            exit 1
            ;;
    esac
}

show_status() {
    log_info "Deployment Status:"
    echo ""
    
    log_info "Pods:"
    kubectl get pods -n "$NAMESPACE" -o wide
    echo ""
    
    log_info "Services:"
    kubectl get services -n "$NAMESPACE"
    echo ""
    
    log_info "Ingress:"
    kubectl get ingress -n "$NAMESPACE"
    echo ""
    
    log_info "Persistent Volume Claims:"
    kubectl get pvc -n "$NAMESPACE"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --services)
            SERVICES="$2"
            DEPLOY_ALL=false
            shift 2
            ;;
        --push)
            PUSH_ONLY=true
            DEPLOY_ALL=false
            shift
            ;;
        --remove)
            REMOVE_IMAGES=true
            shift
            ;;
        --secrets-file)
            SECRETS_FILE="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
log_info "🚀 Starting AKS deployment for Engineering Scene Graph System"
echo ""

# Check prerequisites
check_prerequisites

# Login to ACR
login_to_acr

# Determine what to build and deploy
if [ "$DEPLOY_ALL" = true ]; then
    SERVICES="backend,frontend"
fi

# Split services by comma
IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"

# Build and push images
for service in "${SERVICE_ARRAY[@]}"; do
    service=$(echo "$service" | xargs)  # Trim whitespace
    build_and_push_service "$service"
done

# Deploy to AKS (unless push-only mode)
if [ "$PUSH_ONLY" = false ]; then
    log_info "Deploying to AKS cluster..."
    
    if [ "$DEPLOY_ALL" = true ]; then
        deploy_to_aks "all"
    else
        for service in "${SERVICE_ARRAY[@]}"; do
            service=$(echo "$service" | xargs)
            deploy_to_aks "$service"
        done
    fi
    
    # Show final status
    echo ""
    show_status
    
    log_success "🎉 Deployment completed successfully!"
    echo ""
    log_info "Next steps:"
    echo "1. Check pod status: kubectl get pods -n $NAMESPACE"
    echo "2. View logs: kubectl logs -f deployment/backend -n $NAMESPACE"
    echo "3. Access application via ingress URL"
    
else
    log_success "🎉 Images pushed to ACR successfully!"
    log_info "Images tagged as: $IMAGE_TAG"
    log_info "Use '$0 --services $SERVICES' to deploy to AKS"
fi

# Clean up generated manifests
rm -rf k8s/generated

echo ""