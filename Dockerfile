# Multi-stage build for FlowCheck MCP server
# Stage 1: Builder - compile dependencies
FROM python:3.13-slim as builder

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/

# Install build dependencies and package
RUN pip install --user --no-cache-dir -e .

# Stage 2: Runtime - minimal production image
FROM python:3.13-slim

WORKDIR /app

# Create non-root user for security
RUN groupadd -r flowcheck && useradd -r -g flowcheck flowcheck

# Install git (required by GitPython)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install git (required by GitPython)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies from builder
COPY --from=builder /root/.local /home/flowcheck/.local

# Copy application code
COPY --from=builder /app/src ./src

# Set environment
ENV PATH=/home/flowcheck/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    FLOWCHECK_LOG_LEVEL=INFO

# Create data directory with proper permissions
RUN mkdir -p /data/flowcheck && chown -R flowcheck:flowcheck /data/flowcheck

# Switch to non-root user
USER flowcheck

# Health check - check if process is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD ps aux | grep -q '[f]lowcheck-server' || exit 1

# Expose MCP server port
EXPOSE 8000

# Run MCP server
CMD ["flowcheck-server"]
