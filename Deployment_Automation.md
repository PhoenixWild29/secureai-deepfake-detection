# SecureAI DeepFake Detection System
## Deployment Automation & CI/CD

### 🚀 Automated Deployment Pipeline

This guide covers the complete CI/CD pipeline, deployment automation, and infrastructure management for the SecureAI DeepFake Detection System.

---

## 🎯 CI/CD Pipeline Overview

### **Pipeline Architecture**

```mermaid
graph LR
    A[Code Commit] --> B[GitHub Actions]
    B --> C[Build & Test]
    C --> D[Security Scan]
    D --> E[Build Images]
    E --> F[Push to ECR]
    F --> G[Deploy to Staging]
    G --> H[Integration Tests]
    H --> I[Deploy to Production]
    I --> J[Health Checks]
    J --> K[Notify Teams]
```

### **Pipeline Stages**

#### **Stage 1: Code Quality & Testing**
- **Code Analysis**: Linting, formatting, type checking
- **Unit Tests**: Automated test execution with coverage
- **Integration Tests**: API and database integration testing
- **Security Scanning**: Vulnerability and dependency scanning

#### **Stage 2: Build & Package**
- **Docker Images**: Multi-stage builds for optimization
- **Artifact Storage**: ECR repository management
- **Version Tagging**: Semantic versioning and tagging
- **Metadata Generation**: Build information and provenance

#### **Stage 3: Deployment**
- **Staging Deployment**: Automated staging environment deployment
- **Production Deployment**: Blue-green deployment strategy
- **Database Migrations**: Automated schema and data migrations
- **Configuration Management**: Environment-specific configuration

#### **Stage 4: Verification**
- **Health Checks**: Application and service health validation
- **Smoke Tests**: Basic functionality verification
- **Performance Tests**: Load and performance validation
- **Security Validation**: Security configuration verification

---

## 🔧 GitHub Actions Workflows

### **Main CI/CD Pipeline**

#### **Complete Workflow Configuration**
```yaml
# .github/workflows/ci-cd.yml
name: SecureAI CI/CD Pipeline

on:
  push:
    branches: [main, develop, 'feature/*']
  pull_request:
    branches: [main, develop]

env:
  AWS_REGION: us-west-2
  EKS_CLUSTER_NAME: secureai-cluster
  ECR_REGISTRY: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-west-2.amazonaws.com
  IMAGE_TAG: ${{ github.sha }}

jobs:
  # Code Quality and Testing
  quality-check:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        cache: 'pip'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Code formatting check
      run: |
        black --check src/
        isort --check-only src/
    
    - name: Linting
      run: |
        flake8 src/
        pylint src/
    
    - name: Type checking
      run: |
        mypy src/
    
    - name: Security scan
      run: |
        bandit -r src/
        safety check
    
    - name: Run tests
      run: |
        pytest tests/ --cov=src --cov-report=xml --cov-report=html
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  # Build and Push Images
  build-images:
    needs: quality-check
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
    
    strategy:
      matrix:
        service: [backend, frontend, ai-service, worker]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Log in to Amazon ECR
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.ECR_REGISTRY }}/secureai-${{ matrix.service }}
        tags: |
          type=ref,event=branch
          type=sha,prefix={{branch}}-
          type=raw,value=latest,enable={{is_default_branch}}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: ./${{ matrix.service }}
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
        platforms: linux/amd64

  # Deploy to Staging
  deploy-staging:
    needs: build-images
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: staging
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}
    
    - name: Update kubeconfig
      run: |
        aws eks update-kubeconfig --region ${{ env.AWS_REGION }} --name ${{ env.EKS_CLUSTER_NAME }}
    
    - name: Deploy to staging
      run: |
        # Update image tags
        find k8s/staging -name "*.yaml" -exec sed -i "s|secureai/.*:latest|${{ env.ECR_REGISTRY }}/secureai-&:{{ github.sha }}|g" {} \;
        
        # Apply staging configuration
        kubectl apply -f k8s/staging/
        
        # Wait for deployment
        kubectl rollout status deployment/secureai-backend -n secureai-staging --timeout=300s
        kubectl rollout status deployment/secureai-frontend -n secureai-staging --timeout=300s
    
    - name: Run integration tests
      run: |
        # Wait for services to be ready
        kubectl wait --for=condition=available --timeout=300s deployment/secureai-backend -n secureai-staging
        
        # Run integration tests
        pytest tests/integration/ --kubeconfig=$HOME/.kube/config --namespace=secureai-staging

  # Deploy to Production
  deploy-production:
    needs: [build-images, deploy-staging]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}
    
    - name: Update kubeconfig
      run: |
        aws eks update-kubeconfig --region ${{ env.AWS_REGION }} --name ${{ env.EKS_CLUSTER_NAME }}
    
    - name: Blue-Green Deployment
      run: |
        # Create new deployment with updated images
        envsubst < k8s/production/blue-green-template.yaml > k8s/production/blue-green-deployment.yaml
        
        # Deploy to blue environment
        kubectl apply -f k8s/production/blue-green-deployment.yaml
        
        # Wait for blue deployment to be ready
        kubectl wait --for=condition=available --timeout=600s deployment/secureai-backend-blue -n secureai-production
        
        # Run health checks on blue environment
        ./scripts/health-check.sh --environment=blue
        
        # Switch traffic to blue environment
        kubectl patch service secureai-backend -n secureai-production -p '{"spec":{"selector":{"version":"blue"}}}'
        
        # Wait for green deployment to drain
        kubectl wait --for=delete --timeout=300s pod -l version=green -n secureai-production
        
        # Clean up green deployment
        kubectl delete deployment secureai-backend-green -n secureai-production

  # Post-deployment verification
  verify-deployment:
    needs: deploy-production
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}
    
    - name: Update kubeconfig
      run: |
        aws eks update-kubeconfig --region ${{ env.AWS_REGION }} --name ${{ env.EKS_CLUSTER_NAME }}
    
    - name: Health checks
      run: |
        ./scripts/health-check.sh --environment=production
    
    - name: Smoke tests
      run: |
        pytest tests/smoke/ --kubeconfig=$HOME/.kube/config --namespace=secureai-production
    
    - name: Performance tests
      run: |
        # Run basic performance tests
        ./scripts/performance-test.sh --environment=production --duration=300s

  # Notification
  notify:
    needs: [quality-check, build-images, deploy-staging, deploy-production, verify-deployment]
    runs-on: ubuntu-latest
    if: always()
    
    steps:
    - name: Notify Slack
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ job.status }}
        channel: '#deployments'
        text: |
          🚀 SecureAI Deployment ${{ job.status }}!
          
          **Branch:** ${{ github.ref }}
          **Commit:** ${{ github.sha }}
          **Author:** ${{ github.actor }}
          **Duration:** ${{ github.event.head_commit.timestamp }}
          
          **Services Deployed:**
          - Backend: ${{ env.ECR_REGISTRY }}/secureai-backend:${{ env.IMAGE_TAG }}
          - Frontend: ${{ env.ECR_REGISTRY }}/secureai-frontend:${{ env.IMAGE_TAG }}
          - AI Service: ${{ env.ECR_REGISTRY }}/secureai-ai-service:${{ env.IMAGE_TAG }}
          
          **Environment:** Production
          **Status:** ${{ needs.verify-deployment.result }}
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### **Security Scanning Workflow**

#### **Comprehensive Security Pipeline**
```yaml
# .github/workflows/security.yml
name: Security Scanning

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday at 2 AM

jobs:
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: pip install -r requirements.txt
    
    - name: Run safety check
      run: safety check --json --output safety-report.json
    
    - name: Upload safety results
      uses: actions/upload-artifact@v3
      with:
        name: safety-report
        path: safety-report.json

  container-scan:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [backend, frontend, ai-service, worker]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: |
        docker build -t secureai-${{ matrix.service }} ./${{ matrix.service }}
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: 'secureai-${{ matrix.service }}'
        format: 'sarif'
        output: 'trivy-results-${{ matrix.service }}.sarif'
    
    - name: Upload Trivy scan results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results-${{ matrix.service }}.sarif'

  infrastructure-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Terraform
      uses: hashicorp/setup-terraform@v2
      with:
        terraform_version: 1.5.0
    
    - name: Terraform Format Check
      run: terraform fmt -check -recursive
    
    - name: Terraform Init
      run: terraform init
    
    - name: Terraform Validate
      run: terraform validate
    
    - name: Run Checkov
      uses: bridgecrewio/checkov-action@master
      with:
        directory: terraform/
        framework: terraform
        output_format: sarif
        output_file_path: checkov-results.sarif
    
    - name: Upload Checkov results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: checkov-results.sarif
```

---

## 🐳 Docker Configuration

### **Multi-Stage Dockerfiles**

#### **Backend Service Dockerfile**
```dockerfile
# backend/Dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Expose port
EXPOSE 8000

# Start application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### **AI Service Dockerfile**
```dockerfile
# ai-service/Dockerfile
# Base image with CUDA support
FROM nvidia/cuda:11.8-devel-ubuntu22.04 as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-pip \
    python3.11-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM nvidia/cuda:11.8-runtime-ubuntu22.04

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-distutils \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY models/ ./models/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Expose port
EXPOSE 8080

# Start application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### **Docker Compose for Development**

#### **Development Environment**
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: secureai_dev
      POSTGRES_USER: secureai
      POSTGRES_PASSWORD: secureai_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U secureai"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://secureai:secureai_password@postgres:5432/secureai_dev
      - REDIS_URL=redis://redis:6379
      - ENVIRONMENT=development
    volumes:
      - ./backend:/app
      - /app/venv
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

  ai-service:
    build:
      context: ./ai-service
      dockerfile: Dockerfile.dev
    ports:
      - "8080:8080"
    environment:
      - MODEL_PATH=/models
      - CUDA_VISIBLE_DEVICES=0
    volumes:
      - ./ai-service:/app
      - ./models:/models
    command: ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: ["npm", "start"]

volumes:
  postgres_data:
  redis_data:
```

---

## 🚀 Deployment Strategies

### **Blue-Green Deployment**

#### **Blue-Green Configuration**
```yaml
# blue-green-deployment.yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: secureai-backend
  namespace: secureai-production
spec:
  replicas: 3
  strategy:
    blueGreen:
      activeService: secureai-backend-active
      previewService: secureai-backend-preview
      autoPromotionEnabled: false
      scaleDownDelaySeconds: 30
      prePromotionAnalysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: secureai-backend-preview
      postPromotionAnalysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: secureai-backend-active
  selector:
    matchLabels:
      app: secureai-backend
  template:
    metadata:
      labels:
        app: secureai-backend
    spec:
      containers:
      - name: secureai-backend
        image: secureai/backend:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"

---
# Analysis template for blue-green deployment
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
  namespace: secureai-production
spec:
  args:
  - name: service-name
  metrics:
  - name: success-rate
    successCondition: result[0] >= 0.95
    provider:
      prometheus:
        address: http://prometheus:9090
        query: |
          sum(rate(http_requests_total{service="{{args.service-name}}",status!~"5.."}[5m])) /
          sum(rate(http_requests_total{service="{{args.service-name}}"}[5m]))
```

### **Canary Deployment**

#### **Canary Configuration**
```yaml
# canary-deployment.yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: secureai-ai-service
  namespace: secureai-production
spec:
  replicas: 5
  strategy:
    canary:
      steps:
      - setWeight: 20
      - pause: {duration: 10m}
      - analysis:
          templates:
          - templateName: success-rate
          args:
          - name: service-name
            value: secureai-ai-service
      - setWeight: 40
      - pause: {duration: 10m}
      - setWeight: 60
      - pause: {duration: 10m}
      - setWeight: 80
      - pause: {duration: 10m}
      trafficRouting:
        istio:
          virtualService:
            name: secureai-ai-service
            routes:
            - primary
  selector:
    matchLabels:
      app: secureai-ai-service
  template:
    metadata:
      labels:
        app: secureai-ai-service
    spec:
      containers:
      - name: secureai-ai-service
        image: secureai/ai-service:latest
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "4Gi"
            cpu: "1000m"
            nvidia.com/gpu: 1
          limits:
            memory: "8Gi"
            cpu: "2000m"
            nvidia.com/gpu: 1
```

---

## 📊 Monitoring & Alerting

### **Deployment Monitoring**

#### **Deployment Status Monitoring**
```yaml
# deployment-monitoring.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: secureai-deployment
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: secureai-backend
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s

---
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: deployment-alerts
  namespace: monitoring
spec:
  groups:
  - name: deployment
    rules:
      - alert: DeploymentFailed
        expr: kube_deployment_status_replicas_unavailable > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Deployment {{ $labels.deployment }} has unavailable replicas"
          description: "Deployment {{ $labels.deployment }} has {{ $value }} unavailable replicas"
      
      - alert: RolloutStuck
        expr: argo_rollouts_rollout_phase{phase!="Healthy"} == 1
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Rollout {{ $labels.name }} is stuck"
          description: "Rollout {{ $labels.name }} has been in phase {{ $labels.phase }} for more than 10 minutes"
```

### **Performance Monitoring**

#### **Application Performance Metrics**
```python
# performance_monitoring.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
import logging

# Deployment metrics
deployment_requests_total = Counter('secureai_deployment_requests_total', 'Total deployment requests', ['method', 'status'])
deployment_duration = Histogram('secureai_deployment_duration_seconds', 'Deployment duration', ['service'])
deployment_success_rate = Gauge('secureai_deployment_success_rate', 'Deployment success rate', ['service'])
active_deployments = Gauge('secureai_active_deployments', 'Number of active deployments')

# Performance metrics
response_time = Histogram('secureai_response_time_seconds', 'Response time', ['endpoint', 'method'])
throughput = Counter('secureai_requests_total', 'Total requests', ['endpoint', 'method', 'status'])
error_rate = Gauge('secureai_error_rate', 'Error rate percentage', ['service'])

# Resource metrics
cpu_usage = Gauge('secureai_cpu_usage_percent', 'CPU usage percentage', ['pod', 'service'])
memory_usage = Gauge('secureai_memory_usage_bytes', 'Memory usage in bytes', ['pod', 'service'])
gpu_usage = Gauge('secureai_gpu_usage_percent', 'GPU usage percentage', ['gpu_id', 'pod'])

class DeploymentMonitor:
    def __init__(self):
        self.start_time = time.time()
    
    def record_deployment(self, service: str, duration: float, success: bool):
        deployment_duration.labels(service=service).observe(duration)
        deployment_requests_total.labels(method="deploy", status="success" if success else "failure").inc()
    
    def update_success_rate(self, service: str, rate: float):
        deployment_success_rate.labels(service=service).set(rate)
    
    def update_active_deployments(self, count: int):
        active_deployments.set(count)

# Start metrics server
start_http_server(8000)
```

---

## 🔧 Infrastructure Management

### **Terraform Automation**

#### **Infrastructure Pipeline**
```yaml
# .github/workflows/infrastructure.yml
name: Infrastructure Management

on:
  push:
    branches: [main]
    paths: ['terraform/**']
  pull_request:
    branches: [main]
    paths: ['terraform/**']

jobs:
  terraform-plan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Terraform
      uses: hashicorp/setup-terraform@v2
      with:
        terraform_version: 1.5.0
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-west-2
    
    - name: Terraform Format Check
      run: terraform fmt -check -recursive
    
    - name: Terraform Init
      run: terraform init
    
    - name: Terraform Validate
      run: terraform validate
    
    - name: Terraform Plan
      run: terraform plan -out=tfplan
      working-directory: terraform/
    
    - name: Upload Terraform Plan
      uses: actions/upload-artifact@v3
      with:
        name: terraform-plan
        path: terraform/tfplan

  terraform-apply:
    needs: terraform-plan
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Download Terraform Plan
      uses: actions/download-artifact@v3
      with:
        name: terraform-plan
        path: terraform/
    
    - name: Set up Terraform
      uses: hashicorp/setup-terraform@v2
      with:
        terraform_version: 1.5.0
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-west-2
    
    - name: Terraform Init
      run: terraform init
      working-directory: terraform/
    
    - name: Terraform Apply
      run: terraform apply -auto-approve tfplan
      working-directory: terraform/
```

### **Configuration Management**

#### **Environment Configuration**
```yaml
# config/environments.yaml
environments:
  development:
    replicas: 1
    resources:
      requests:
        memory: "512Mi"
        cpu: "250m"
      limits:
        memory: "1Gi"
        cpu: "500m"
    database:
      instance_class: "db.t3.micro"
      allocated_storage: 20
    monitoring:
      enabled: false
  
  staging:
    replicas: 2
    resources:
      requests:
        memory: "1Gi"
        cpu: "500m"
      limits:
        memory: "2Gi"
        cpu: "1000m"
    database:
      instance_class: "db.t3.small"
      allocated_storage: 100
    monitoring:
      enabled: true
  
  production:
    replicas: 3
    resources:
      requests:
        memory: "2Gi"
        cpu: "1000m"
      limits:
        memory: "4Gi"
        cpu: "2000m"
    database:
      instance_class: "db.r6g.xlarge"
      allocated_storage: 500
      multi_az: true
    monitoring:
      enabled: true
      alerts:
        enabled: true
```

---

## 📞 Deployment Support

### **Rollback Procedures**

#### **Automated Rollback**
```bash
#!/bin/bash
# rollback.sh - Automated rollback script

set -e

ENVIRONMENT=${1:-production}
NAMESPACE="secureai-${ENVIRONMENT}"
TIMEOUT=${2:-300}

echo "Starting rollback for environment: ${ENVIRONMENT}"

# Get current deployment status
kubectl get deployments -n ${NAMESPACE}

# Rollback to previous version
kubectl rollout undo deployment/secureai-backend -n ${NAMESPACE}
kubectl rollout undo deployment/secureai-ai-service -n ${NAMESPACE}
kubectl rollout undo deployment/secureai-frontend -n ${NAMESPACE}

# Wait for rollback to complete
kubectl rollout status deployment/secureai-backend -n ${NAMESPACE} --timeout=${TIMEOUT}s
kubectl rollout status deployment/secureai-ai-service -n ${NAMESPACE} --timeout=${TIMEOUT}s
kubectl rollout status deployment/secureai-frontend -n ${NAMESPACE} --timeout=${TIMEOUT}s

# Verify rollback
./scripts/health-check.sh --environment=${ENVIRONMENT}

echo "Rollback completed successfully"

# Notify teams
curl -X POST "${SLACK_WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"🔄 Rollback completed for ${ENVIRONMENT} environment\"}"
```

### **Emergency Procedures**

#### **Emergency Deployment**
```bash
#!/bin/bash
# emergency-deploy.sh - Emergency deployment script

set -e

ENVIRONMENT=${1:-production}
NAMESPACE="secureai-${ENVIRONMENT}"
IMAGE_TAG=${2:-latest}

echo "Starting emergency deployment for environment: ${ENVIRONMENT}"

# Scale down current deployment
kubectl scale deployment secureai-backend --replicas=0 -n ${NAMESPACE}
kubectl scale deployment secureai-ai-service --replicas=0 -n ${NAMESPACE}

# Deploy emergency version
kubectl set image deployment/secureai-backend secureai-backend=secureai/backend:${IMAGE_TAG} -n ${NAMESPACE}
kubectl set image deployment/secureai-ai-service secureai-ai-service=secureai/ai-service:${IMAGE_TAG} -n ${NAMESPACE}

# Scale up
kubectl scale deployment secureai-backend --replicas=3 -n ${NAMESPACE}
kubectl scale deployment secureai-ai-service --replicas=2 -n ${NAMESPACE}

# Wait for deployment
kubectl rollout status deployment/secureai-backend -n ${NAMESPACE} --timeout=300s
kubectl rollout status deployment/secureai-ai-service -n ${NAMESPACE} --timeout=300s

echo "Emergency deployment completed"

# Notify teams
curl -X POST "${SLACK_WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"🚨 Emergency deployment completed for ${ENVIRONMENT} environment\"}"
```

---

*This deployment automation guide provides a comprehensive framework for implementing CI/CD pipelines, automated deployments, and infrastructure management for the SecureAI DeepFake Detection System. For additional configuration details and advanced deployment strategies, refer to the specific component documentation.*
