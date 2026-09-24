"""Configuration constants and settings for Browser QA MCP."""

import os
from pathlib import Path

# Paths
MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parent.parent
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Registrations are in-memory by default (no unwanted profiles folder)
REGISTRATIONS_FILE = None

# Ring buffer & limits
RING_BUFFER_MAX_SIZE = 1000
MAX_BODY_BYTES = 102400  # 100 KB limit for request/response bodies returned to LLM
CORRELATION_WINDOW_SECONDS = 2.5

# Sensitive headers to redact
SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
    "x-session-token",
    "proxy-authorization",
    "x-csrf-token",
    "x-xsrf-token",
}

# Sensitive payload keys to redact (case-insensitive substring match)
SENSITIVE_PAYLOAD_KEYS = {
    "password",
    "passwd",
    "token",
    "access_token",
    "refresh_token",
    "client_secret",
    "api_key",
    "apikey",
    "secret",
    "otp",
    "jwt",
    "credit_card",
    "cvv",
    "ssn",
}

# Binary Content-Types that should not be returned as raw text
BINARY_CONTENT_PREFIXES = (
    "image/",
    "video/",
    "audio/",
    "font/",
    "application/pdf",
    "application/zip",
    "application/gzip",
    "application/octet-stream",
)
