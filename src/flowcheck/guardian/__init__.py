"""Guardian Layer - Security proxy for FlowCheck.

This module provides security controls for sanitizing data before
it reaches the MCP server or AI agents.
"""

from .sanitizer import Sanitizer, SanitizationResult
from .injection_filter import InjectionFilter, InjectionResult

__all__ = [
    "Sanitizer",
    "SanitizationResult",
    "InjectionFilter",
    "InjectionResult",
    "apply_security_scan",
]


def apply_security_scan(diff_content: str) -> list[str]:
    """Apply security scans and return security flags.

    Shared helper used by both the MCP server and CLI.

    Args:
        diff_content: The git diff text to scan.

    Returns:
        List of human-readable security flag strings.
    """
    sanitizer = Sanitizer()
    injection_filter = InjectionFilter()
    flags: list[str] = []

    # Check for secrets/PII
    if sanitizer.quick_check(diff_content):
        result = sanitizer.sanitize(diff_content)
        if result.secrets_detected:
            flags.append("⚠️ SECRETS: Potential secrets detected in diff")
        if result.pii_detected:
            flags.append("⚠️ PII: Personal information detected in diff")

    # Check for injection patterns
    injection_flags = injection_filter.get_security_flags(diff_content)
    flags.extend(injection_flags)

    return flags
