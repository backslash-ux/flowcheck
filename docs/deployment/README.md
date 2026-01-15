# Deployment Guide

Complete guides for deploying FlowCheck in various environments.

## Quick Navigation

| Scenario | Guide | Time |
|----------|-------|------|
| **Local Development** | [Docker](Docker.md#local-development) | 5 min |
| **Production (Docker)** | [Docker](Docker.md#production-deployment) | 10 min |
| **Production (Kubernetes)** | [Kubernetes](Kubernetes.md) | 30 min |
| **CI/CD Integration** | [CI/CD](CI-CD.md) | 15 min |
| **Troubleshooting** | [Troubleshooting](Troubleshooting.md) | - |

---

## Deployment Models

### 1. Docker (Recommended)

**Best for**: Local dev, small teams, single-host deployments

- Setup time: 5 minutes
- Resource footprint: ~200MB RAM, minimal CPU
- Scaling: Manual or via Docker Swarm
- Complexity: Low

[Go to Docker Guide →](Docker.md)

### 2. Kubernetes

**Best for**: Cloud deployments, high availability, auto-scaling

- Setup time: 30+ minutes (includes cluster provisioning)
- Resource footprint: Configurable
- Scaling: Horizontal via Kubernetes
- Complexity: High

[Go to Kubernetes Guide →](Kubernetes.md)

### 3. CI/CD Integration

**Best for**: Automated testing and deployment workflows

- Setup time: 15 minutes
- Integrations: GitHub Actions, GitLab CI, Jenkins
- Complexity: Medium

[Go to CI/CD Guide →](CI-CD.md)

---

## Environment Variables

All deployment methods use the same environment variables. See [.env.example](../../.env.example) for complete reference.

### Required

- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` - LLM provider credentials

### Optional

- `FLOWCHECK_LOG_LEVEL` - Log verbosity (DEBUG, INFO, WARNING, ERROR)
- `FLOWCHECK_STORAGE_PATH` - Data directory path
- `FLOWCHECK_SESSION_TIMEOUT` - Session expiry in seconds

---

## Troubleshooting

**Common issues and solutions**: [Troubleshooting Guide](Troubleshooting.md)

---

## Monitoring

After deployment, verify that FlowCheck is running:

```bash
# Check container/pod health
docker ps  # or kubectl get pods

# Check logs
docker logs flowcheck-server  # or kubectl logs pod/flowcheck-server

# Test endpoint
curl http://localhost:8000/health
```

---

## Next Steps

- [Local Development with Docker Compose](Docker.md#local-development)
- [Production Deployment Best Practices](Docker.md#production-deployment)
- [Setting up CI/CD Pipelines](CI-CD.md)
