"""OpenTelemetry emitter for FlowCheck observability.

Provides standardized tracing for all MCP tool invocations using
OpenTelemetry semantic conventions for gen_ai operations.
"""

import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Generator
from functools import wraps

# Check if opentelemetry is available
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import Status, StatusCode, Span
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


@dataclass
class TraceContext:
    """Context for a traced operation."""

    trace_id: str
    span_id: str
    agent_id: Optional[str] = None
    action_type: str = "tool_call"
    started_at: datetime = None

    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "agent_id": self.agent_id,
            "action_type": self.action_type,
            "started_at": self.started_at.isoformat(),
        }


def create_tracer(
    service_name: str = "flowcheck",
    enable_console: bool = False,
) -> Optional[Any]:
    """Create an OpenTelemetry tracer.

    Args:
        service_name: Name for the traced service.
        enable_console: Whether to export spans to console (for debugging).

    Returns:
        Tracer instance if OTel available, None otherwise.
    """
    if not OTEL_AVAILABLE:
        return None

    # Create resource with service info
    from flowcheck import __version__
    resource = Resource.create({
        "service.name": service_name,
        "service.version": __version__,
    })

    # Create provider
    provider = TracerProvider(resource=resource)

    if enable_console:
        # Add console exporter for debugging
        processor = SimpleSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)

    # Set as global provider
    trace.set_tracer_provider(provider)

    return trace.get_tracer(service_name)


class OTelEmitter:
    """OpenTelemetry emitter for FlowCheck operations.

    Implements gen_ai semantic conventions for tracing AI operations.
    Falls back gracefully when OpenTelemetry is not installed.
    """

    # gen_ai semantic conventions
    ATTR_AGENT_ID = "gen_ai.agent.id"
    ATTR_ACTION_TYPE = "gen_ai.action.type"
    ATTR_SAFETY_PII = "gen_ai.safety.pii"
    ATTR_SAFETY_INJECTION = "gen_ai.safety.injection_detected"
    ATTR_TASK_ID = "gen_ai.task.id"
    ATTR_TOOL_NAME = "gen_ai.tool.name"
    ATTR_REPO_PATH = "flowcheck.repo_path"
    ATTR_STATUS = "flowcheck.status"
    ATTR_RISK_SCORE = "flowcheck.risk_score"

    def __init__(
        self,
        service_name: str = "flowcheck",
        agent_id: Optional[str] = None,
        enable_console: bool = False,
    ):
        """Initialize the OTel emitter.

        Args:
            service_name: Name for the traced service.
            agent_id: Optional agent identifier (e.g., model name).
            enable_console: Whether to export to console.
        """
        self.service_name = service_name
        self.agent_id = agent_id or os.environ.get(
            "FLOWCHECK_AGENT_ID", "unknown")
        self.tracer = create_tracer(service_name, enable_console)
        self._enabled = OTEL_AVAILABLE and self.tracer is not None

    @property
    def enabled(self) -> bool:
        """Check if OTel tracing is enabled."""
        return self._enabled

    def _generate_ids(self) -> tuple[str, str]:
        """Generate trace and span IDs."""
        trace_id = uuid.uuid4().hex[:32]
        span_id = uuid.uuid4().hex[:16]
        return trace_id, span_id

    @contextmanager
    def trace_tool_call(
        self,
        tool_name: str,
        repo_path: Optional[str] = None,
        task_id: Optional[str] = None,
        **extra_attrs,
    ) -> Generator[TraceContext, None, None]:
        """Context manager for tracing a tool call.

        Args:
            tool_name: Name of the MCP tool being called.
            repo_path: Optional path to the repository.
            task_id: Optional ticket/task ID for context.
            **extra_attrs: Additional span attributes.

        Yields:
            TraceContext with trace/span IDs.
        """
        trace_id, span_id = self._generate_ids()
        context = TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            agent_id=self.agent_id,
            action_type="tool_call",
        )

        if not self._enabled:
            # Fallback: just yield context without actual tracing
            yield context
            return

        with self.tracer.start_as_current_span(f"flowcheck.{tool_name}") as span:
            # Set standard attributes
            span.set_attribute(self.ATTR_AGENT_ID, self.agent_id)
            span.set_attribute(self.ATTR_ACTION_TYPE, "tool_call")
            span.set_attribute(self.ATTR_TOOL_NAME, tool_name)

            if repo_path:
                span.set_attribute(self.ATTR_REPO_PATH, repo_path)
            if task_id:
                span.set_attribute(self.ATTR_TASK_ID, task_id)

            # Set extra attributes
            for key, value in extra_attrs.items():
                span.set_attribute(f"flowcheck.{key}", value)

            try:
                yield context
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    def record_security_event(
        self,
        span: Optional[Any],
        pii_detected: bool = False,
        injection_detected: bool = False,
        risk_score: float = 0.0,
    ):
        """Record security-related attributes on a span.

        Args:
            span: Current span (can be None if OTel not available).
            pii_detected: Whether PII was detected.
            injection_detected: Whether injection patterns were detected.
            risk_score: Overall risk score (0.0-1.0).
        """
        if not self._enabled or span is None:
            return

        span.set_attribute(self.ATTR_SAFETY_PII, pii_detected)
        span.set_attribute(self.ATTR_SAFETY_INJECTION, injection_detected)
        span.set_attribute(self.ATTR_RISK_SCORE, risk_score)

    def record_flow_state(
        self,
        span: Optional[Any],
        status: str,
        minutes_since_commit: int,
        uncommitted_lines: int,
    ):
        """Record flow state attributes on a span.

        Args:
            span: Current span.
            status: Flow health status (ok/warning/danger).
            minutes_since_commit: Minutes since last commit.
            uncommitted_lines: Number of uncommitted lines.
        """
        if not self._enabled or span is None:
            return

        span.set_attribute(self.ATTR_STATUS, status)
        span.set_attribute("flowcheck.minutes_since_commit",
                           minutes_since_commit)
        span.set_attribute("flowcheck.uncommitted_lines", uncommitted_lines)

    def traced(self, tool_name: Optional[str] = None):
        """Decorator for tracing function calls.

        Args:
            tool_name: Optional override for tool name (defaults to function name).

        Returns:
            Decorator function.
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                name = tool_name or func.__name__
                repo_path = kwargs.get("repo_path", args[0] if args else None)

                with self.trace_tool_call(name, repo_path=repo_path):
                    return func(*args, **kwargs)

            return wrapper
        return decorator


# Global emitter instance (can be reconfigured)
_global_emitter: Optional[OTelEmitter] = None


def get_emitter() -> OTelEmitter:
    """Get the global OTel emitter instance."""
    global _global_emitter
    if _global_emitter is None:
        _global_emitter = OTelEmitter()
    return _global_emitter


def configure_emitter(
    service_name: str = "flowcheck",
    agent_id: Optional[str] = None,
    enable_console: bool = False,
):
    """Configure the global OTel emitter."""
    global _global_emitter
    _global_emitter = OTelEmitter(
        service_name=service_name,
        agent_id=agent_id,
        enable_console=enable_console,
    )
