"""Sanitizer for PII and secret detection/redaction.

This module scans text content (diffs, logs, file contents) for sensitive
information and replaces it with redaction tokens.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SensitiveType(str, Enum):
    """Types of sensitive information that can be detected."""

    API_KEY = "api_key"
    SECRET = "secret"
    PASSWORD = "password"
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    AWS_KEY = "aws_key"
    GITHUB_TOKEN = "github_token"
    PRIVATE_KEY = "private_key"


@dataclass
class RedactedItem:
    """Represents a single redacted piece of sensitive data."""

    sensitive_type: SensitiveType
    original_length: int
    line_number: Optional[int] = None
    token: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.sensitive_type.value,
            "original_length": self.original_length,
            "line_number": self.line_number,
            "token": self.token,
        }


@dataclass
class SanitizationResult:
    """Result of sanitizing content."""

    sanitized_text: str
    redacted_items: list[RedactedItem] = field(default_factory=list)
    pii_detected: bool = False
    secrets_detected: bool = False

    def to_dict(self) -> dict:
        return {
            "sanitized_text": self.sanitized_text,
            "redacted_count": len(self.redacted_items),
            "pii_detected": self.pii_detected,
            "secrets_detected": self.secrets_detected,
            "redacted_items": [item.to_dict() for item in self.redacted_items],
        }


class Sanitizer:
    """Scans and sanitizes text for PII and secrets.

    Uses regex patterns to detect sensitive information and replaces
    it with consistent redaction tokens.
    """

    # High-entropy detection threshold (for potential secrets)
    HIGH_ENTROPY_THRESHOLD = 4.5
    MIN_SECRET_LENGTH = 20

    # Regex patterns for different sensitive types
    PATTERNS = {
        # API Keys and Secrets (high entropy strings)
        SensitiveType.API_KEY: [
            # Generic API key patterns
            r'(?i)(?:api[_-]?key|apikey)["\s:=]+["\']?([a-zA-Z0-9_\-]{20,})["\']?',
            r'(?i)(?:auth[_-]?token|bearer)["\s:=]+["\']?([a-zA-Z0-9_\-\.]{20,})["\']?',
        ],
        SensitiveType.AWS_KEY: [
            r'(?:AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}',  # AWS Access Key ID
            r'(?i)aws[_-]?secret[_-]?access[_-]?key["\s:=]+["\']?([a-zA-Z0-9/+=]{40})["\']?',
        ],
        SensitiveType.GITHUB_TOKEN: [
            r'ghp_[a-zA-Z0-9]{36}',  # GitHub Personal Access Token
            r'gho_[a-zA-Z0-9]{36}',  # GitHub OAuth Token
            r'ghu_[a-zA-Z0-9]{36}',  # GitHub User Token
            r'ghs_[a-zA-Z0-9]{36}',  # GitHub Server Token
            r'ghr_[a-zA-Z0-9]{36}',  # GitHub Refresh Token
        ],
        SensitiveType.PRIVATE_KEY: [
            r'-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----',
            r'-----BEGIN PGP PRIVATE KEY BLOCK-----',
        ],
        SensitiveType.SECRET: [
            # Generic secret patterns
            r'(?i)(?:secret|password|passwd|pwd)["\s:=]+["\']?([^\s"\']{8,})["\']?',
            r'(?i)(?:client[_-]?secret)["\s:=]+["\']?([a-zA-Z0-9_\-]{20,})["\']?',
        ],
        SensitiveType.PASSWORD: [
            r'(?i)(?:password|passwd|pwd)\s*[=:]\s*["\']?([^\s"\']{6,})["\']?',
        ],
        # PII Patterns
        SensitiveType.EMAIL: [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        ],
        SensitiveType.PHONE: [
            r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
            r'\b\+[0-9]{1,3}[-.\s]?[0-9]{6,14}\b',
        ],
        SensitiveType.SSN: [
            r'\b[0-9]{3}[-\s]?[0-9]{2}[-\s]?[0-9]{4}\b',
        ],
        SensitiveType.CREDIT_CARD: [
            r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',
        ],
        SensitiveType.IP_ADDRESS: [
            # IPv4 (excluding common local/test IPs)
            r'\b(?!(?:127\.|10\.|192\.168\.|172\.(?:1[6-9]|2[0-9]|3[01])\.|0\.0\.0\.0))(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
        ],
    }

    # Types considered as secrets (vs PII)
    SECRET_TYPES = {
        SensitiveType.API_KEY,
        SensitiveType.AWS_KEY,
        SensitiveType.GITHUB_TOKEN,
        SensitiveType.PRIVATE_KEY,
        SensitiveType.SECRET,
        SensitiveType.PASSWORD,
    }

    def __init__(self, enable_high_entropy: bool = True):
        """Initialize the sanitizer.

        Args:
            enable_high_entropy: Whether to detect high-entropy strings as potential secrets.
        """
        self.enable_high_entropy = enable_high_entropy
        self._token_counter: dict[SensitiveType, int] = {}

    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not text:
            return 0.0

        counter = Counter(text)
        length = len(text)
        entropy = -sum(
            (count / length) * math.log2(count / length)
            for count in counter.values()
        )
        return entropy

    def _get_redaction_token(self, sensitive_type: SensitiveType) -> str:
        """Generate a consistent redaction token."""
        count = self._token_counter.get(sensitive_type, 0) + 1
        self._token_counter[sensitive_type] = count
        return f"[REDACTED_{sensitive_type.value.upper()}_{count}]"

    def _detect_high_entropy_secrets(self, text: str) -> list[tuple[str, int]]:
        """Detect potential secrets based on high entropy.

        Returns list of (match, line_number) tuples.
        """
        if not self.enable_high_entropy:
            return []

        results = []
        lines = text.split('\n')

        # Pattern for potential secret values (alphanumeric strings)
        potential_secret_pattern = re.compile(r'\b[a-zA-Z0-9_\-/+=]{20,64}\b')

        for line_num, line in enumerate(lines, 1):
            for match in potential_secret_pattern.finditer(line):
                value = match.group()
                entropy = self._calculate_entropy(value)

                if entropy >= self.HIGH_ENTROPY_THRESHOLD:
                    results.append((value, line_num))

        return results

    def sanitize(self, text: str) -> SanitizationResult:
        """Sanitize text by redacting sensitive information.

        Args:
            text: The text content to sanitize.

        Returns:
            SanitizationResult with sanitized text and metadata.
        """
        self._token_counter.clear()
        redacted_items: list[RedactedItem] = []
        pii_detected = False
        secrets_detected = False

        # Phase 1: collect all matches on the original text
        # Each entry: (start, end, sensitive_type, matched_value)
        all_matches: list[tuple[int, int, SensitiveType, str]] = []

        for sensitive_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    start, end = match.span()
                    matched_value = match.group()
                    if match.lastindex:
                        matched_value = match.group(1)
                        start = match.start(1)
                        end = match.end(1)
                    all_matches.append(
                        (start, end, sensitive_type, matched_value))

        # Remove overlapping matches (keep the first occurrence)
        all_matches.sort(key=lambda m: m[0])
        filtered: list[tuple[int, int, SensitiveType, str]] = []
        for m in all_matches:
            if filtered and m[0] < filtered[-1][1]:
                continue  # overlaps with previous kept match
            filtered.append(m)

        # Phase 2: apply replacements in reverse order so positions stay valid
        sanitized = text
        for start, end, sensitive_type, matched_value in reversed(filtered):
            token = self._get_redaction_token(sensitive_type)
            line_number = text[:start].count('\n') + 1

            item = RedactedItem(
                sensitive_type=sensitive_type,
                original_length=len(matched_value),
                line_number=line_number,
                token=token,
            )
            redacted_items.append(item)

            if sensitive_type in self.SECRET_TYPES:
                secrets_detected = True
            else:
                pii_detected = True

            sanitized = sanitized[:start] + token + sanitized[end:]

        # Reverse so items appear in document order
        redacted_items.reverse()

        # High entropy detection
        if self.enable_high_entropy:
            for secret_value, line_num in self._detect_high_entropy_secrets(sanitized):
                if secret_value.startswith('[REDACTED_'):
                    continue  # Skip already redacted

                token = self._get_redaction_token(SensitiveType.SECRET)
                item = RedactedItem(
                    sensitive_type=SensitiveType.SECRET,
                    original_length=len(secret_value),
                    line_number=line_num,
                    token=token,
                )
                redacted_items.append(item)
                secrets_detected = True
                sanitized = sanitized.replace(secret_value, token, 1)

        return SanitizationResult(
            sanitized_text=sanitized,
            redacted_items=redacted_items,
            pii_detected=pii_detected,
            secrets_detected=secrets_detected,
        )

    def quick_check(self, text: str) -> bool:
        """Quick check if text contains any sensitive information.

        This is faster than full sanitization when you just need to know
        if content is sensitive.

        Args:
            text: Text to check.

        Returns:
            True if sensitive information detected.
        """
        for patterns in self.PATTERNS.values():
            for pattern in patterns:
                if re.search(pattern, text):
                    return True
        return False
