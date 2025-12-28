"""Prompt injection filter for detecting adversarial instructions.

This module scans text for patterns commonly used in prompt injection
attacks, where malicious content attempts to override AI system instructions.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class InjectionType(str, Enum):
    """Types of prompt injection patterns."""

    INSTRUCTION_OVERRIDE = "instruction_override"
    ROLE_HIJACKING = "role_hijacking"
    CONTEXT_MANIPULATION = "context_manipulation"
    DELIMITER_ATTACK = "delimiter_attack"
    ENCODED_INJECTION = "encoded_injection"


@dataclass
class InjectionMatch:
    """Represents a detected injection pattern."""

    injection_type: InjectionType
    matched_text: str
    line_number: int
    severity: str  # "low", "medium", "high"
    description: str

    def to_dict(self) -> dict:
        return {
            "type": self.injection_type.value,
            "matched_text": self.matched_text[:50] + "..." if len(self.matched_text) > 50 else self.matched_text,
            "line_number": self.line_number,
            "severity": self.severity,
            "description": self.description,
        }


@dataclass
class InjectionResult:
    """Result of injection detection scan."""

    is_safe: bool
    matches: list[InjectionMatch] = field(default_factory=list)
    risk_score: float = 0.0  # 0.0 to 1.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "injection_count": len(self.matches),
            "matches": [m.to_dict() for m in self.matches],
        }


class InjectionFilter:
    """Detects prompt injection patterns in text content.

    Scans for common patterns used to manipulate AI systems through
    malicious content injected into data sources.
    """

    # Patterns categorized by injection type
    PATTERNS = {
        InjectionType.INSTRUCTION_OVERRIDE: [
            # Direct instruction overrides
            (r'(?i)ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions?|rules?|prompts?)', "high"),
            (r'(?i)disregard\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions?|rules?)', "high"),
            (r'(?i)forget\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions?|context)', "high"),
            (r'(?i)override\s+(?:all\s+)?(?:safety|security)\s+(?:rules?|protocols?)', "high"),
            (r'(?i)bypass\s+(?:all\s+)?(?:safety|security|content)\s+(?:filters?|checks?)', "high"),
            (r'(?i)new\s+instructions?\s*[:=]', "medium"),
            (r'(?i)updated?\s+(?:system\s+)?instructions?\s*[:=]', "medium"),
        ],
        InjectionType.ROLE_HIJACKING: [
            # Role/identity manipulation
            (r'(?i)you\s+are\s+now\s+(?:a\s+)?(?:different|new|my)', "high"),
            (r'(?i)act\s+as\s+(?:if\s+you\s+(?:are|were)\s+)?(?:a\s+)?(?:different|unrestricted)', "high"),
            (r'(?i)pretend\s+(?:you\s+are|to\s+be)\s+(?:a\s+)?', "medium"),
            (r'(?i)roleplay\s+as\s+(?:a\s+)?(?:hacker|attacker|malicious)', "high"),
            (r'(?i)switch\s+to\s+(?:developer|admin|root|sudo)\s+mode', "high"),
            (r'(?i)enable\s+(?:developer|debug|admin)\s+mode', "medium"),
            (r'(?i)\[?system\]?\s*[:=]\s*you\s+are', "high"),
        ],
        InjectionType.CONTEXT_MANIPULATION: [
            # Context/scope manipulation
            (r'(?i)actually[,\s]+(?:the\s+)?(?:real|true)\s+(?:task|goal|objective)\s+is', "medium"),
            (r'(?i)(?:the\s+)?previous\s+(?:context|conversation)\s+was\s+(?:a\s+)?(?:test|fake)', "medium"),
            (r'(?i)start\s+(?:a\s+)?new\s+(?:conversation|session|context)', "low"),
            (r'(?i)reset\s+(?:your\s+)?(?:context|memory|instructions)', "medium"),
            (r'(?i)clear\s+(?:your\s+)?(?:previous\s+)?(?:context|history)', "low"),
        ],
        InjectionType.DELIMITER_ATTACK: [
            # Delimiter/separator attacks
            (r'(?i)```\s*(?:system|assistant|user)\s*\n', "high"),
            (r'(?i)<\|(?:im_start|im_end|system|user|assistant)\|>', "high"),
            (r'(?i)\[INST\]|\[/INST\]', "high"),
            (r'(?i)<<SYS>>|<</SYS>>', "high"),
            (r'(?i)### (?:System|User|Assistant|Human|AI):', "medium"),
            (r'(?i)Human:\s*$|Assistant:\s*$|System:\s*$', "medium"),
        ],
        InjectionType.ENCODED_INJECTION: [
            # Base64 or other encoded content that might hide injections
            (r'(?i)decode\s+(?:this\s+)?(?:base64|hex):', "medium"),
            (r'(?i)execute\s+(?:this\s+)?(?:encoded|base64)\s+(?:command|instruction)', "high"),
            # Long base64-like strings in unexpected places (comments, docs)
            (r'(?:^|\s)(?:[A-Za-z0-9+/]{50,}={0,2})(?:\s|$)', "low"),
        ],
    }

    # Severity weights for risk score calculation
    SEVERITY_WEIGHTS = {
        "high": 1.0,
        "medium": 0.5,
        "low": 0.2,
    }

    def __init__(self, sensitivity: str = "medium"):
        """Initialize the injection filter.

        Args:
            sensitivity: Detection sensitivity ("low", "medium", "high").
                - low: Only detect high-severity patterns
                - medium: Detect high and medium severity patterns
                - high: Detect all patterns including low severity
        """
        self.sensitivity = sensitivity
        self._severity_threshold = {
            "low": {"high"},
            "medium": {"high", "medium"},
            "high": {"high", "medium", "low"},
        }.get(sensitivity, {"high", "medium"})

    def _get_description(self, injection_type: InjectionType) -> str:
        """Get human-readable description for injection type."""
        descriptions = {
            InjectionType.INSTRUCTION_OVERRIDE:
                "Attempt to override or ignore system instructions",
            InjectionType.ROLE_HIJACKING:
                "Attempt to change the AI's role or identity",
            InjectionType.CONTEXT_MANIPULATION:
                "Attempt to manipulate conversation context",
            InjectionType.DELIMITER_ATTACK:
                "Special delimiter patterns used to inject system prompts",
            InjectionType.ENCODED_INJECTION:
                "Potentially encoded malicious content",
        }
        return descriptions.get(injection_type, "Unknown injection pattern")

    def scan(self, text: str) -> InjectionResult:
        """Scan text for prompt injection patterns.

        Args:
            text: The text content to scan.

        Returns:
            InjectionResult with safety assessment and matches.
        """
        matches: list[InjectionMatch] = []
        lines = text.split('\n')

        for injection_type, patterns in self.PATTERNS.items():
            for pattern, severity in patterns:
                # Skip patterns below sensitivity threshold
                if severity not in self._severity_threshold:
                    continue

                for line_num, line in enumerate(lines, 1):
                    for regex_match in re.finditer(pattern, line):
                        match = InjectionMatch(
                            injection_type=injection_type,
                            matched_text=regex_match.group(),
                            line_number=line_num,
                            severity=severity,
                            description=self._get_description(injection_type),
                        )
                        matches.append(match)

        # Calculate risk score
        if not matches:
            risk_score = 0.0
        else:
            # Weighted sum of severities, capped at 1.0
            total_weight = sum(
                self.SEVERITY_WEIGHTS.get(m.severity, 0.5)
                for m in matches
            )
            risk_score = min(1.0, total_weight / 3.0)  # 3+ high severity = 1.0

        return InjectionResult(
            is_safe=len(matches) == 0,
            matches=matches,
            risk_score=risk_score,
        )

    def quick_check(self, text: str) -> bool:
        """Quick check if text contains any injection patterns.

        This is faster than full scan when you just need a boolean result.

        Args:
            text: Text to check.

        Returns:
            True if NO injection patterns detected (text is safe).
        """
        for patterns in self.PATTERNS.values():
            for pattern, severity in patterns:
                if severity not in self._severity_threshold:
                    continue
                if re.search(pattern, text):
                    return False
        return True

    def get_security_flags(self, text: str) -> list[str]:
        """Get list of security flags suitable for FlowState.

        Args:
            text: Text to scan.

        Returns:
            List of human-readable security flag strings.
        """
        result = self.scan(text)
        if result.is_safe:
            return []

        flags = []
        seen_types = set()

        for match in result.matches:
            if match.injection_type not in seen_types:
                seen_types.add(match.injection_type)
                flags.append(
                    f"⚠️ {match.severity.upper()}: {match.description} (line {match.line_number})"
                )

        return flags
