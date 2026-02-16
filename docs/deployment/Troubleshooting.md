# Docker Troubleshooting Guide

Common issues and their solutions.

## Container Issues

### Container won't start

**Symptoms**: Container exits immediately or fails to create

**Debugging**:
```bash
# Check logs
docker-compose logs flowcheck-server

# Inspect image
docker inspect flowcheck:v0.4

# Try verbose startup
docker run -it flowcheck:latest bash
```

**Common causes**:
1. Missing environment variables → Set all required env vars in `.env`
2. Port conflict → Use `lsof -i :8000` to find conflicting process
3. Insufficient resources → Free memory/disk space

### Container keeps restarting

**Symptoms**: Container constantly crashes and restarts

**Solutions**:
```bash
# Check restart policy
docker inspect flowcheck-server | grep RestartPolicy

# View recent logs
docker logs --tail 50 flowcheck-server

# Run without auto-restart
docker run --restart=no flowcheck:latest
```

### Container is unresponsive

**Symptoms**: Container runs but doesn't respond to requests

**Debugging**:
```bash
# Check if process is running
docker exec flowcheck-server ps aux

# Check open ports
docker exec flowcheck-server netstat -tlnp

# Ping container
docker exec flowcheck-server ping 127.0.0.1
```

## Configuration Issues

### API key not working

**Symptoms**: "401 Unauthorized" or authentication errors

**Solutions**:
```bash
# Verify env var is set
docker exec flowcheck-server env | grep API_KEY

# Check format
echo $ANTHROPIC_API_KEY  # Should start with sk-ant-

# Test directly
curl -H "Authorization: Bearer $KEY" https://api.anthropic.com/v1/models
```

### Config file not found

**Symptoms**: "FileNotFoundError: ~/.flowcheck/config.json"

**Solutions**:
```bash
# Mount config directory
docker run -v ~/.flowcheck:/root/.flowcheck flowcheck:latest

# Or create inside container
docker exec flowcheck-server mkdir -p ~/.flowcheck
```

### Wrong log level

**Symptoms**: Too many or too few logs

**Solutions**:
```bash
# Update env
export FLOWCHECK_LOG_LEVEL=DEBUG
docker-compose up

# Or in compose file
environment:
  FLOWCHECK_LOG_LEVEL: DEBUG
```

## Performance Issues

### High memory usage

**Symptoms**: Container consuming >1GB RAM

**Debugging**:
```bash
# Check memory stats
docker stats flowcheck-server

# Limit memory
docker run -m 512m flowcheck:latest
```

**Solutions**:
1. Use `flowcheck:slim` variant
2. Reduce log level from DEBUG to INFO
3. Increase container memory limit
4. Check for memory leaks in logs

### Slow startup

**Symptoms**: Container takes >30 seconds to start

**Debugging**:
```bash
# Time the startup
time docker run flowcheck:latest --version

# Check what's happening
docker run -it flowcheck:latest bash
```

**Solutions**:
1. Pre-pull image: `docker pull flowcheck:latest`
2. Use BuildKit: `export DOCKER_BUILDKIT=1`
3. Check internet connection for dependency downloads

## Network Issues

### Port already in use

**Symptoms**: `bind: address already in use`

**Solutions**:
```bash
# Find process using port
lsof -i :8000
sudo kill -9 <PID>

# Or use different port
docker run -p 9000:8000 flowcheck:latest

# Check Docker port mapping
docker port flowcheck-server
```

### Cannot reach container from host

**Symptoms**: `curl localhost:8000` times out

**Solutions**:
```bash
# Verify port mapping
docker ps | grep flowcheck

# Try from inside container
docker exec flowcheck-server curl localhost:8000

# Check network settings
docker network inspect bridge

# Use host network (Linux only)
docker run --network host flowcheck:latest
```

### DNS resolution fails

**Symptoms**: "Name or service not known"

**Solutions**:
```bash
# Check DNS from container
docker exec flowcheck-server nslookup google.com

# Override DNS
docker run --dns 8.8.8.8 flowcheck:latest

# In compose file
dns:
  - 8.8.8.8
  - 8.8.4.4
```

## Volume Issues

### Volume mount not working

**Symptoms**: Files not visible in container

**Solutions**:
```bash
# Check mount point
docker inspect flowcheck-server | grep -A 5 Mounts

# Verify source exists
ls -la ~/.flowcheck

# Test volume independently
docker run -v ~/.flowcheck:/data alpine ls -la /data
```

### Permission denied on volume

**Symptoms**: "Permission denied" when accessing mounted files

**Solutions**:
```bash
# Check ownership
ls -la ~/.flowcheck

# Change ownership
chown -R 1000:1000 ~/.flowcheck  # For user UID 1000

# Or use root in container
docker run -u root flowcheck:latest

# In compose file - use user
user: "root:root"
```

### Volume space full

**Symptoms**: "No space left on device"

**Solutions**:
```bash
# Check volume usage
docker system df

# Clean up unused volumes
docker volume prune

# Check container storage
docker exec flowcheck-server df -h
```

## Docker-Compose Issues

### Service fails to start

**Symptoms**: `docker-compose up` fails

**Debugging**:
```bash
# Check compose file syntax
docker-compose config

# Validate services
docker-compose ps

# See full error
docker-compose up  # Without -d flag
```

### Dependencies not starting in order

**Symptoms**: Container starts before dependencies are ready

**Solutions**:
```yaml
# Add depends_on
services:
  flowcheck-server:
    depends_on:
      - database
    healthcheck:
      test: ["CMD", "flowcheck-server", "--version"]
```

### Cannot connect between services

**Symptoms**: Services can't reach each other

**Solutions**:
```bash
# Use service name as hostname
# Inside flowcheck-server, use: database:5432

# Check network
docker network ls
docker network inspect flowcheck_default

# Test connectivity
docker exec flowcheck-server ping database
```

## Image Issues

### Image build fails

**Symptoms**: `docker build` fails at various stages

**Debugging**:
```bash
# Build without cache
docker build --no-cache .

# Build specific stage
docker build --target builder .

# Check each layer
docker history flowcheck:latest
```

### Image too large

**Symptoms**: Image size >500MB

**Solutions**:
1. Use python:3.13-slim base instead of python:3.13
2. Remove unnecessary files in Dockerfile
3. Use multi-stage builds
4. Check `.dockerignore` includes large directories

### Cannot pull image from registry

**Symptoms**: "Error response from daemon: pull access denied"

**Solutions**:
```bash
# Login to registry
docker login

# Check credentials
cat ~/.docker/config.json

# Pull specific version
docker pull backslash-ux/flowcheck:v0.4
```

## Getting Help

If you can't find a solution:

1. Check logs: `docker logs flowcheck-server`
2. Check system resources: `docker stats`
3. Review [Docker.md](Docker.md) deployment guide
4. Open an issue: https://github.com/backslash-ux/flowcheck/issues

---

## Quick Reference

| Issue | Command |
|-------|---------|
| View logs | `docker logs -f flowcheck-server` |
| Check health | `docker ps --format "{{.Names}}\t{{.Status}}"` |
| Get IP | `docker inspect -f '{{.NetworkSettings.IPAddress}}' flowcheck-server` |
| Execute command | `docker exec flowcheck-server <command>` |
| Clean up | `docker system prune -a` |
| Restart | `docker-compose restart` |
| Full rebuild | `docker-compose up --build` |
