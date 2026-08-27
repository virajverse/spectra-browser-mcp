"""Tests for secret redaction engine."""

import json
import sys
from pathlib import Path

# Setup PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from browser_qa.processors.redactor import (
    redact_action_value, redact_body_string, redact_data, redact_headers
)


def test_bearer_redaction():
    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThis",
        "Content-Type": "application/json"
    }
    redacted = redact_headers(headers)
    assert redacted["Authorization"] == "Bearer [REDACTED]"
    assert redacted["Content-Type"] == "application/json"


def test_cookie_redaction():
    headers = {
        "Cookie": "session_id=secret123; theme=dark; auth_token=token456"
    }
    redacted = redact_headers(headers)
    assert "session_id=[REDACTED]" in redacted["Cookie"]
    assert "auth_token=[REDACTED]" in redacted["Cookie"]
    assert "theme=[REDACTED]" in redacted["Cookie"]


def test_json_payload_redaction():
    payload = {
        "username": "alice",
        "password": "SuperSecretPassword123!",
        "profile": {
            "api_key": "sk-1234567890",
            "nested_token": "secret_token_val",
            "active": True
        }
    }
    redacted = redact_data(payload)
    assert redacted["username"] == "alice"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["profile"]["api_key"] == "[REDACTED]"
    assert redacted["profile"]["nested_token"] == "[REDACTED]"
    assert redacted["profile"]["active"] is True


def test_action_typer_redaction():
    assert redact_action_value("password input field", "my_secret_pass") == "[REDACTED]"
    assert redact_action_value("Search input", "laptops") == "laptops"
    assert redact_action_value("User OTP", "123456") == "[REDACTED]"


if __name__ == "__main__":
    test_bearer_redaction()
    test_cookie_redaction()
    test_json_payload_redaction()
    test_action_typer_redaction()
    print("All redaction tests passed successfully! [PASSED]")
