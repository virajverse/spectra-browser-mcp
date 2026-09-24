"""Debug-preserving secret redaction engine."""

import json
import re
from typing import Any, Dict, List, Union
from browser_qa.config import SENSITIVE_HEADERS, SENSITIVE_PAYLOAD_KEYS

BEARER_REGEX = re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE)
BASIC_REGEX = re.compile(r"Basic\s+[A-Za-z0-9\+\/]+=*", re.IGNORECASE)
JWT_REGEX = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")


def redact_header_value(header_name: str, header_val: str) -> str:
    """Mask sensitive tokens while preserving auth type structure for debugging."""
    lower_name = header_name.lower().strip()

    if lower_name in SENSITIVE_HEADERS or any(s in lower_name for s in ("token", "auth", "cookie", "key")):
        if BEARER_REGEX.match(header_val):
            return "Bearer [REDACTED]"
        if BASIC_REGEX.match(header_val):
            return "Basic [REDACTED]"
        if lower_name in ("cookie", "set-cookie"):
            # Preserve cookie names, mask values: e.g. session=abc; path=/ -> session=[REDACTED]; path=/
            parts = header_val.split(";")
            redacted_parts = []
            for part in parts:
                if "=" in part:
                    k, _ = part.split("=", 1)
                    redacted_parts.append(f"{k.strip()}=[REDACTED]")
                else:
                    redacted_parts.append(part.strip())
            return "; ".join(redacted_parts)
        return "[REDACTED]"

    # Check for embedded JWT inside any non-standard header
    if JWT_REGEX.search(header_val):
        return JWT_REGEX.sub("[REDACTED_JWT]", header_val)

    return header_val


def redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Sanitize all headers."""
    if not headers:
        return {}
    return {k: redact_header_value(k, v) for k, v in headers.items()}


def redact_data(data: Any) -> Any:
    """Recursively mask sensitive keys in JSON payloads, dictionaries, and lists."""
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            lower_k = str(k).lower()
            if any(s in lower_k for s in SENSITIVE_PAYLOAD_KEYS):
                new_dict[k] = "[REDACTED]"
            else:
                new_dict[k] = redact_data(v)
        return new_dict
    elif isinstance(data, list):
        return [redact_data(item) for item in data]
    elif isinstance(data, str):
        # Redact JWTs in string values
        if JWT_REGEX.search(data):
            return JWT_REGEX.sub("[REDACTED_JWT]", data)
        return data
    return data


def redact_body_string(body: Union[str, None]) -> Union[str, None]:
    """Redacts raw string body (handles JSON automatically)."""
    if not body:
        return body

    # Try parsing JSON
    trimmed = body.strip()
    if (trimmed.startswith("{") and trimmed.endswith("}")) or (trimmed.startswith("[") and trimmed.endswith("]")):
        try:
            parsed = json.loads(trimmed)
            redacted = redact_data(parsed)
            return json.dumps(redacted, indent=2)
        except Exception:
            pass

    # Generic string masking
    redacted = JWT_REGEX.sub("[REDACTED_JWT]", body)
    for sensitive_key in SENSITIVE_PAYLOAD_KEYS:
        # Mask key=value in form data or query strings
        pattern = re.compile(rf"({sensitive_key}=)([^&]+)", re.IGNORECASE)
        redacted = pattern.sub(r"\1[REDACTED]", redacted)

    return redacted


def redact_action_value(target: str, value: Union[str, None]) -> Union[str, None]:
    """Redacts typed value if target indicates sensitive input (password, otp, pin, token)."""
    if value is None:
        return None
    lower_target = target.lower()
    if any(s in lower_target for s in ("password", "passwd", "token", "otp", "pin", "cvv", "secret", "card")):
        return "[REDACTED]"
    return value


class Redactor:
    """Class wrapper providing static redaction methods for CDP telemetry and actions."""

    @staticmethod
    def redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
        return redact_headers(headers)

    @staticmethod
    def redact_url(url: str) -> str:
        if not url:
            return ""
        pattern = re.compile(r"([?&](?:token|auth|key|secret|password|sig|signature|access_token)=)([^&]+)", re.IGNORECASE)
        return pattern.sub(r"\1[REDACTED]", url)

    @staticmethod
    def redact_data(data: Any) -> Any:
        return redact_data(data)

    @staticmethod
    def redact_body_string(body: Union[str, None]) -> Union[str, None]:
        return redact_body_string(body)

    @staticmethod
    def redact_text(text: Union[str, None]) -> Union[str, None]:
        if not text:
            return text
        return JWT_REGEX.sub("[REDACTED_JWT]", str(text))

    @staticmethod
    def redact_action_value(target: str, value: Union[str, None]) -> Union[str, None]:
        return redact_action_value(target, value)
