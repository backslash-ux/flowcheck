"""Unit tests for the Guardian Layer sanitizer."""

import pytest

from flowcheck.guardian.sanitizer import (
    Sanitizer,
    SanitizationResult,
    SensitiveType,
    RedactedItem,
)


class TestSanitizerSecrets:
    """Tests for secret detection."""

    def test_detects_aws_access_key(self):
        """Should detect AWS access key IDs."""
        sanitizer = Sanitizer()
        text = "aws_access_key_id = AKIAIOSFODNN7EXAMPLE"
        result = sanitizer.sanitize(text)

        assert result.secrets_detected
        assert len(result.redacted_items) >= 1
        assert "AKIAIOSFODNN7EXAMPLE" not in result.sanitized_text

    def test_detects_github_token(self):
        """Should detect GitHub personal access tokens."""
        sanitizer = Sanitizer()
        text = "export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        result = sanitizer.sanitize(text)

        assert result.secrets_detected
        assert "ghp_" not in result.sanitized_text

    def test_detects_api_key_pattern(self):
        """Should detect generic API key patterns."""
        sanitizer = Sanitizer()
        text = 'api_key = "sk_live_abcdefghij1234567890"'
        result = sanitizer.sanitize(text)

        assert result.secrets_detected
        assert "sk_live" not in result.sanitized_text

    def test_detects_password_in_config(self):
        """Should detect password values."""
        sanitizer = Sanitizer()
        text = 'password: "MySecretPassword123!"'
        result = sanitizer.sanitize(text)

        assert result.secrets_detected
        assert "MySecretPassword123!" not in result.sanitized_text

    def test_detects_private_key_header(self):
        """Should detect private key headers."""
        sanitizer = Sanitizer()
        text = "-----BEGIN RSA PRIVATE KEY-----"
        result = sanitizer.sanitize(text)

        assert result.secrets_detected


class TestSanitizerPII:
    """Tests for PII detection."""

    def test_detects_email_address(self):
        """Should detect and redact email addresses."""
        sanitizer = Sanitizer()
        text = "Contact: john.doe@company.com for support"
        result = sanitizer.sanitize(text)

        assert result.pii_detected
        assert "john.doe@company.com" not in result.sanitized_text
        assert "[REDACTED_EMAIL" in result.sanitized_text

    def test_detects_phone_number(self):
        """Should detect US phone numbers."""
        sanitizer = Sanitizer()
        text = "Call us at 555-123-4567"
        result = sanitizer.sanitize(text)

        assert result.pii_detected
        assert "555-123-4567" not in result.sanitized_text

    def test_detects_ssn(self):
        """Should detect Social Security Numbers."""
        sanitizer = Sanitizer()
        text = "SSN: 123-45-6789"
        result = sanitizer.sanitize(text)

        assert result.pii_detected
        assert "123-45-6789" not in result.sanitized_text

    def test_detects_credit_card(self):
        """Should detect credit card numbers."""
        sanitizer = Sanitizer()
        text = "Card: 4111111111111111"  # Visa test number
        result = sanitizer.sanitize(text)

        assert result.pii_detected
        assert "4111111111111111" not in result.sanitized_text


class TestSanitizerCleanContent:
    """Tests for clean content handling."""

    def test_clean_code_unchanged(self):
        """Clean code should pass through unchanged."""
        sanitizer = Sanitizer()
        text = """
def hello_world():
    print("Hello, World!")
    return 42
"""
        result = sanitizer.sanitize(text)

        assert not result.pii_detected
        assert not result.secrets_detected
        assert len(result.redacted_items) == 0
        assert result.sanitized_text == text

    def test_quick_check_clean(self):
        """Quick check should return False for clean content."""
        sanitizer = Sanitizer()
        text = "Normal code without secrets"

        assert not sanitizer.quick_check(text)

    def test_quick_check_sensitive(self):
        """Quick check should return True for sensitive content."""
        sanitizer = Sanitizer()
        text = "api_key = AKIAIOSFODNN7EXAMPLE"

        assert sanitizer.quick_check(text)


class TestSanitizationResult:
    """Tests for SanitizationResult."""

    def test_to_dict_format(self):
        """Result should serialize correctly."""
        result = SanitizationResult(
            sanitized_text="redacted text",
            redacted_items=[
                RedactedItem(
                    sensitive_type=SensitiveType.EMAIL,
                    original_length=20,
                    line_number=1,
                    token="[REDACTED_EMAIL_1]"
                )
            ],
            pii_detected=True,
            secrets_detected=False,
        )

        data = result.to_dict()

        assert data["sanitized_text"] == "redacted text"
        assert data["redacted_count"] == 1
        assert data["pii_detected"] is True
        assert data["secrets_detected"] is False
        assert len(data["redacted_items"]) == 1
