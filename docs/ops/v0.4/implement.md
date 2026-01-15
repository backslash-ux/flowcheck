# v0.4 Implementation Roadmap: "Containerize It"

> **Status**: 🔄 **IN PROGRESS**  
> **Branch**: `feat/v0.4-containerization`  
> **Objective**: Ship FlowCheck as production-ready Docker images

This document outlines the engineering work for FlowCheck v0.4, focusing on **containerization**, **multi-image strategy**, and **deployment simplicity**.

## Goals

v0.4 transforms FlowCheck into a containerized platform:

1. **Docker Images**: Multi-stage builds for slim, secure containers
2. **Compose Stack**: One-command setup with Docker Compose (MCP server + API gateway)
3. **Registry**: Publish images to Docker Hub (`backslash-ux/flowcheck`)
4. **Docs**: Deploy guides for Docker, Kubernetes, and CI/CD systems
5. **Configuration**: Environment-based config with `.env` templates

---

## 1. Dockerfile Strategy ✏️

**Goal**: Create lean, production-ready Docker images.

### 1.1 Multi-Stage Build

```dockerfile
# Stage 1: Builder
FROM python:3.13-slim as builder
WORKDIR /app
COPY pyproject.toml .
RUN pip install --user --no-cache-dir -e .

# Stage 2: Runtime
FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY src/ /app/src/
ENV PATH=/root/.local/bin:$PATH
CMD ["flowcheck-server"]
```

### 1.2 Images

| Image | Purpose | Size Target |
|-------|---------|------------|
| `flowcheck:latest` | MCP server with all features | <150MB |
| `flowcheck:slim` | MCP server, no docs | <100MB |
| `flowcheck:dev` | Development image with dev deps | <200MB |

### 1.3 Tasks

- [ ] Create `Dockerfile` for production image
- [ ] Create `Dockerfile.slim` for minimal deployments
- [ ] Create `Dockerfile.dev` for development
- [ ] Add `.dockerignore` to exclude unnecessary files
- [ ] Test builds for all variants

---

## 2. Docker Compose Orchestration ✏️

**Goal**: One-command local setup.

### 2.1 Services

```yaml
services:
  flowcheck-server:
    image: flowcheck:latest
    ports:
      - "8000:8000"
    environment:
      - FLOWCHECK_LOG_LEVEL=INFO
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ~/.flowcheck:/root/.flowcheck
      - /var/run/docker.sock:/var/run/docker.sock
  
  reverse-proxy:
    image: traefik:v3.0
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./traefik.yml:/etc/traefik/traefik.yml
      - /var/run/docker.sock:/var/run/docker.sock
```

### 2.2 Tasks

- [ ] Create `docker-compose.yml`
- [ ] Create `docker-compose.dev.yml` for local development
- [ ] Add `.env.example` template
- [ ] Document `docker-compose up` workflow
- [ ] Add health checks to services

---

## 3. Configuration & Secrets ✏️

**Goal**: Secure, flexible configuration management.

### 3.1 Environment Variables

Map all config to env vars:

```bash
FLOWCHECK_LOG_LEVEL=INFO
FLOWCHECK_STORAGE_PATH=/data/flowcheck
FLOWCHECK_SESSION_TIMEOUT=3600
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...  # Fallback
```

### 3.2 Config Volume

Mount host config directory:

```
/var/flowcheck/
├── config.yaml
├── rules/
└── .env
```

### 3.3 Tasks

- [ ] Update `config/loader.py` to read env vars
- [ ] Create `.env.example` file
- [ ] Add config validation on startup
- [ ] Document secrets management (Docker Secrets, Vault)
- [ ] Add healthcheck endpoint to MCP server

---

## 4. Publishing & Registry ✏️

**Goal**: Distribute images via Docker Hub.

### 4.1 Build & Push Pipeline

```bash
# Build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t backslash-ux/flowcheck:v0.4 \
  -t backslash-ux/flowcheck:latest \
  --push .
```

### 4.2 Registry Structure

- `backslash-ux/flowcheck:latest` → Latest stable release
- `backslash-ux/flowcheck:v0.4` → Release tag
- `backslash-ux/flowcheck:dev` → Development builds
- `backslash-ux/flowcheck:slim` → Minimal variant

### 4.3 Tasks

- [ ] Set up Docker Hub repository
- [ ] Create GitHub Actions workflow for buildx
- [ ] Add registry documentation
- [ ] Create pull request template for image updates

---

## 5. Deployment Guides ✏️

**Goal**: Make deployment effortless.

### 5.1 Quick Start

```markdown
# Docker Quick Start

1. Pull the image:
   docker pull backslash-ux/flowcheck:latest

2. Run with docker-compose:
   docker-compose up

3. Access at http://localhost:8000
```

### 5.2 Deployment Scenarios

| Scenario | Method | Docs |
|----------|--------|------|
| Local development | docker-compose.dev.yml | Local.md |
| Production (single host) | docker-compose.yml | Production.md |
| Kubernetes | Helm chart | Kubernetes.md |
| CI/CD (GitHub Actions) | Docker image in action | CI-CD.md |
| Cloud (AWS/GCP/Azure) | Container Registry | Cloud.md |

### 5.3 Tasks

- [ ] Create `docs/deployment/Quick-Start.md`
- [ ] Create `docs/deployment/Docker.md`
- [ ] Create `docs/deployment/Kubernetes.md`
- [ ] Create `docs/deployment/CI-CD.md`
- [ ] Create `docs/deployment/Troubleshooting.md`

---

## 6. Testing & Validation ✏️

**Goal**: Ensure images work in production.

### 6.1 Image Tests

```bash
# Build test
docker build -t flowcheck:test .

# Run tests inside container
docker run flowcheck:test pytest

# Check image size
docker images flowcheck:test --format "{{.Size}}"

# Vulnerability scan
docker scan backslash-ux/flowcheck:latest
```

### 6.2 Tasks

- [ ] Add image size validation (<150MB)
- [ ] Run pytest inside container during build
- [ ] Add Trivy vulnerability scanning
- [ ] Test compose stack end-to-end
- [ ] Verify volume mounting works

---

## 7. Documentation ✏️

**Goal**: Clear deployment + contribution guides.

### 7.1 Update README

Add Docker section:

```markdown
## Docker

### Quick Start
\`\`\`bash
docker-compose up
\`\`\`

### Build Locally
\`\`\`bash
docker build -t flowcheck:local .
\`\`\`
```

### 7.2 New Files

- `docs/deployment/README.md` - Deployment index
- `docs/docker/Dockerfile.md` - Dockerfile walkthrough
- `docs/docker/Build.md` - Build & publish workflow

### 7.3 Tasks

- [ ] Update main README with Docker section
- [ ] Document all environment variables
- [ ] Add Docker troubleshooting guide
- [ ] Create deployment checklist

---

## File Structure (New/Modified)

```
.
├── Dockerfile                    # NEW: Production image
├── Dockerfile.slim               # NEW: Minimal variant
├── Dockerfile.dev                # NEW: Dev image
├── .dockerignore                 # NEW: Build exclusions
├── docker-compose.yml            # NEW: Production stack
├── docker-compose.dev.yml        # NEW: Dev stack
├── .env.example                  # NEW: Config template
├── .github/workflows/
│   └── docker-publish.yml        # NEW: CI/CD pipeline
├── docs/deployment/              # NEW: Deployment guides
│   ├── README.md
│   ├── Quick-Start.md
│   ├── Docker.md
│   ├── Kubernetes.md
│   ├── CI-CD.md
│   └── Troubleshooting.md
├── src/flowcheck/
│   ├── config/
│   │   └── loader.py             # MODIFIED: Add env var support
│   └── server.py                 # MODIFIED: Add healthcheck endpoint
└── README.md                     # MODIFIED: Add Docker section
```

---

## Timeline

| Phase | Tasks | Estimate | Status |
|-------|-------|----------|--------|
| Phase 1 | Dockerfiles + .dockerignore | 1-2 hours | ⏳ |
| Phase 2 | Docker Compose stacks | 1 hour | ⏳ |
| Phase 3 | Config & env vars | 1 hour | ⏳ |
| Phase 4 | GitHub Actions pipeline | 1-2 hours | ⏳ |
| Phase 5 | Deployment guides | 2-3 hours | ⏳ |
| Phase 6 | Testing & validation | 1-2 hours | ⏳ |
| Phase 7 | Documentation updates | 1 hour | ⏳ |
| **Total** | | **8-12 hours** | ⏳ |

---

## Implementation Priority

### Phase 1 (Immediate)
1. Create `Dockerfile` (production-ready)
2. Create `.dockerignore`
3. Test local build

### Phase 2 (Following)
4. Create `docker-compose.yml`
5. Create `.env.example`
6. Test compose up

### Phase 3 (Polish)
7. GitHub Actions CI/CD
8. Deployment guides
9. Registry publication

---

## Success Criteria

- ✅ `docker build .` succeeds in <5 minutes
- ✅ `docker run` starts MCP server on port 8000
- ✅ `docker-compose up` brings full stack online
- ✅ Images published to Docker Hub
- ✅ All deployment docs complete
- ✅ Vulnerability scan passes
- ✅ Image size < 150MB

---

## Deferred to v0.5

- Kubernetes Helm charts (complex setup)
- Multi-cloud deployment templates (AWS/GCP/Azure)
- Advanced monitoring (Prometheus/Grafana)
- Log aggregation (ELK stack)

---

## Notes

- Use `python:3.13-slim` as base (faster pulls, smaller size)
- Pin all dependency versions in requirements.txt
- Use buildx for multi-arch support (amd64, arm64)
- Document security best practices (non-root user, etc.)
- Consider caching strategy for layer optimization
