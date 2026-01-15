# Kubernetes Deployment Guide

Deploy FlowCheck on Kubernetes clusters (EKS, GKE, AKS, or on-premises).

## Prerequisites

- Kubernetes 1.24+
- kubectl configured to access your cluster
- Docker image pushed to registry (e.g., Docker Hub, ECR, GCR)
- 2GB RAM and 1 CPU available in cluster

## Quick Deploy

```bash
# Create namespace
kubectl create namespace flowcheck

# Create secret for API keys
kubectl create secret generic flowcheck-keys \
  --from-literal=anthropic-api-key=$ANTHROPIC_API_KEY \
  --from-literal=openai-api-key=$OPENAI_API_KEY \
  -n flowcheck

# Deploy
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flowcheck
  namespace: flowcheck
spec:
  replicas: 2
  selector:
    matchLabels:
      app: flowcheck
  template:
    metadata:
      labels:
        app: flowcheck
    spec:
      containers:
      - name: flowcheck
        image: backslash-ux/flowcheck:v0.4
        ports:
        - containerPort: 8000
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: flowcheck-keys
              key: anthropic-api-key
        - name: FLOWCHECK_LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - flowcheck-server
            - --version
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          exec:
            command:
            - flowcheck-server
            - --version
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: flowcheck
  namespace: flowcheck
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
  selector:
    app: flowcheck
EOF

# Verify deployment
kubectl get pods -n flowcheck
kubectl logs -f deployment/flowcheck -n flowcheck
```

## Production Manifest Files

See Kubernetes deployment manifests in `k8s/` directory:

- `k8s/namespace.yaml` - Namespace and RBAC
- `k8s/configmap.yaml` - Configuration
- `k8s/secrets.yaml` - API keys and credentials
- `k8s/deployment.yaml` - Main deployment
- `k8s/service.yaml` - Service exposure
- `k8s/ingress.yaml` - Ingress with TLS
- `k8s/hpa.yaml` - Horizontal Pod Autoscaler
- `k8s/kustomization.yaml` - Kustomize overlay

## Scaling

### Horizontal Pod Autoscaling

```bash
kubectl autoscale deployment flowcheck \
  --min=2 --max=10 \
  --cpu-percent=70 \
  -n flowcheck
```

### Rolling Updates

```bash
kubectl set image deployment/flowcheck \
  flowcheck=backslash-ux/flowcheck:v0.5 \
  -n flowcheck

# Monitor rollout
kubectl rollout status deployment/flowcheck -n flowcheck
```

## Storage

### Persistent Volume

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: flowcheck-data
  namespace: flowcheck
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

## Monitoring

### Prometheus Integration

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

## See Also

- [Docker Deployment](Docker.md)
- [CI/CD Integration](CI-CD.md)
- [Troubleshooting](Troubleshooting.md)
