# Docker Deployment Guide

Complete guide for deploying FlowCheck using Docker.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Local Development](#local-development)
3. [Production Deployment](#production-deployment)
4. [Image Variants](#image-variants)
5. [Configuration](#configuration)
6. [Health Checks](#health-checks)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

Get FlowCheck running in 30 seconds:

```bash
# Clone the repository
git clone https://github.com/backslash-ux/flowcheck.git
cd flowcheck

# Configure environment
cp .env.example .env
# Edit .env with your API keys
nano .env

# Start the stack
docker-compose up
```

FlowCheck is now running at `http://localhost:8000`

---

## Local Development

For active development with hot-reload:

```bash
# Start development container
docker-compose -f docker-compose.dev.yml up

# Inside container, install in editable mode
pip install -e .

# Run tests
pytest

# Start server
flowcheck-server
```

All changes in your local `src/` directory are immediately reflected in the container.

---

## Production Deployment

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum
- 100MB disk space for data volume

### Setup

1. **Clone and configure**:

```bash
git clone https://github.com/backslash-ux/flowcheck.git
cd flowcheck
cp .env.example .env
```

2. **Set production values in .env**:

```bash
FLOWCHECK_LOG_LEVEL=INFO  # Not DEBUG
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx
```

3. **Build production image**:

```bash
docker build -t flowcheck:v0.4 .
docker tag flowcheck:v0.4 flowcheck:latest
```

4. **Start the stack**:

```bash
docker-compose up -d
```

5. **Verify health**:

```bash
docker ps  # Should show flowcheck-server running
docker logs -f flowcheck-server
```

### Data Persistence

Data is stored in the `flowcheck-data` Docker volume:

```bash
# Backup data
docker run --rm -v flowcheck-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/flowcheck-backup.tar.gz /data

# Restore from backup
docker run --rm -v flowcheck-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/flowcheck-backup.tar.gz -C /
```

### Scaling

To run multiple instances with load balancing:

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  flowcheck-1:
    # ... base config
  flowcheck-2:
    # ... base config
  nginx:
    image: nginx:alpine
    ports:
      - "8000:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

---

## Image Variants

### flowcheck:latest (Production)

- **Base**: python:3.13-slim
- **Size**: ~140MB
- **Use case**: Production deployments
- **Features**: Full feature set

```bash
docker run -it flowcheck:latest flowcheck-server
```

### flowcheck:slim

- **Base**: python:3.13-slim
- **Size**: ~120MB
- **Use case**: Memory-constrained environments
- **Trade-off**: Minimal dependencies

```bash
docker build -f Dockerfile.slim -t flowcheck:slim .
docker run -it flowcheck:slim flowcheck-server
```

### flowcheck:dev

- **Base**: python:3.13-slim
- **Size**: ~180MB
- **Use case**: Development and debugging
- **Includes**: pytest, dev tools, git

```bash
docker build -f Dockerfile.dev -t flowcheck:dev .
docker run -it flowcheck:dev bash
```

---

## Configuration

### Environment Variables

All configuration is via environment variables. See [.env.example](../../.env.example) for complete reference.

### Volume Mounting

```bash
docker run \
  -v ~/.flowcheck:/root/.flowcheck \  # Read rules
  -v /data/flowcheck:/data/flowcheck \  # Persist data
  flowcheck:latest
```

### Port Mapping

```bash
# Default (localhost only)
docker run -p 8000:8000 flowcheck:latest

# Public interface
docker run -p 0.0.0.0:8000:8000 flowcheck:latest

# Custom port
docker run -p 9000:8000 flowcheck:latest
```

---

## Health Checks

### Built-in Health Check

```bash
docker run \
  --health-cmd='flowcheck-server --version' \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  flowcheck:latest
```

### Manual Health Check

```bash
# Inside container
flowcheck-server --version

# Or from host
curl http://localhost:8000/health
```

### Container Status

```bash
# Check health status
docker ps --format "{{.Names}}\t{{.Status}}"

# View health details
docker inspect --format='{{.State.Health.Status}}' flowcheck-server
```

---

## Troubleshooting

### Container won't start

**Symptom**: `docker-compose up` fails or container exits immediately

**Solutions**:
1. Check logs: `docker logs flowcheck-server`
2. Verify environment: `cat .env` (check API keys)
3. Check disk space: `df -h`

### Port already in use

**Symptom**: `bind: address already in use`

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000

# Or use different port
docker-compose --project-name flowcheck-alt up
```

### Memory issues

**Symptom**: Container OOMKilled or slow performance

**Solution**:
```bash
# Increase Docker memory limit
# Edit Docker Desktop Preferences → Resources → Memory

# Or use slim variant
docker build -f Dockerfile.slim -t flowcheck:slim .
```

### API key not working

**Symptom**: 401 Unauthorized errors

**Solutions**:
1. Verify key format: `echo $ANTHROPIC_API_KEY`
2. Check env file is loaded: `docker exec flowcheck-server env | grep API`
3. Test key directly: `curl -H "Authorization: Bearer $API_KEY" https://api.anthropic.com/v1/models`

### Logs not visible

**Symptom**: `docker logs` shows nothing

**Solution**:
```bash
# Check container is running
docker ps | grep flowcheck

# View all logs (including stopped containers)
docker logs --all flowcheck-server

# Stream logs in real-time
docker logs -f flowcheck-server
```

---

## Advanced Topics

### Multi-arch builds

Build for both amd64 and arm64:

```bash
docker buildx create --name builder
docker buildx use builder
docker buildx build --platform linux/amd64,linux/arm64 -t flowcheck:latest .
```

### Using Docker Hub registry

```bash
docker tag flowcheck:latest backslash-ux/flowcheck:v0.4
docker login
docker push backslash-ux/flowcheck:v0.4
```

### Networking

```bash
# Create custom network
docker network create flowcheck-net

# Connect containers
docker run --network flowcheck-net --name server flowcheck:latest
docker run --network flowcheck-net --name client flowcheck:latest bash
```

---

## Performance Tips

1. **Use slim variant** for low-memory environments
2. **Enable BuildKit** for faster builds: `export DOCKER_BUILDKIT=1`
3. **Layer caching**: Dockerfile order matters; stable layers first
4. **Volume performance**: Use native volumes, not mounts (on macOS)

---

## Security Best Practices

1. **Non-root user**: Images run as `flowcheck` user (UID 999)
2. **Read-only filesystem** (optional): `docker run --read-only`
3. **Resource limits**: `docker run --memory 512m --cpus 0.5`
4. **Network policies**: Use Docker networks, not host network
5. **Image scanning**: `docker scan flowcheck:latest`

---

## Next Steps

- [Production Deployment Best Practices](../ops/v0.4/implement.md)
- [CI/CD Integration](CI-CD.md)
- [Kubernetes Deployment](Kubernetes.md)
- [Troubleshooting](Troubleshooting.md)
