"""Telemetry Layer - Observability for FlowCheck.

This module provides OpenTelemetry instrumentation and audit logging
for tracking all MCP tool invocations.
"""

from .otel_emitter import OTelEmitter, create_tracer
from .audit_logger import AuditLogger, AuditEntry

__all__ = [
    "OTelEmitter",
    "create_tracer",
    "AuditLogger",
    "AuditEntry",
]
