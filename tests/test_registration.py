"""Comprehensive tests for personal Chrome profile registration and security enforcement."""

import json
import os
import sys
import tempfile
from pathlib import Path
import pytest
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "src"))

from browser_qa.browser.registration import BrowserRegistrationManager
from browser_qa.models.registration import RegistrationStatus
from browser_qa.models.session import BrowserMode, BrowserTarget
from browser_qa.service import BrowserQAService
from browser_qa.processors.redactor import redact_headers, redact_body_string, redact_action_value


class MockCDPHandler(BaseHTTPRequestHandler):
    """Simulates a Chrome CDP /json/version endpoint."""
    def do_GET(self):
        if self.path == "/json/version":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = {
                "Browser": "Chrome/125.0.6422.142",
                "Protocol-Version": "1.3",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "webSocketDebuggerUrl": "ws://127.0.0.1:9876/devtools/browser/mock"
            }
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Quiet mock


@pytest.fixture
def mock_cdp_server():
    server = HTTPServer(("127.0.0.1", 9876), MockCDPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:9876"
    server.shutdown()


def test_registration_manager_discovery():
    """Verifies that dynamic Chrome discovery functions run without hardcoding errors."""
    mgr = BrowserRegistrationManager()
    chrome_path = mgr.detect_chrome_executable()
    # On most developer/Windows machines chrome is found; either way must return str or None
    assert chrome_path is None or isinstance(chrome_path, str)

    profiles = mgr.list_available_profiles()
    assert isinstance(profiles, list)
    assert len(profiles) >= 1
    assert "profile_id" in profiles[0]


def test_registration_lifecycle_start_and_status(tmp_path):
    """Tests registration initiation, status queries, and metadata safety."""
    reg_file = tmp_path / "test_registrations.json"
    mgr = BrowserRegistrationManager(registrations_file=reg_file)

    res = mgr.start_registration(
        display_name="My Work Chrome",
        cdp_url="http://127.0.0.1:9222",
        port=9222,
        profile_identifier="Profile 2"
    )

    assert "registration_id" in res
    reg_id = res["registration_id"]
    assert res["status"] in ("WAITING_FOR_USER", "REGISTERING")
    assert res["connection_method"] == "Chrome DevTools Protocol (CDP)"
    assert "browser_register_confirm" in res["instructions"]
    assert "--remote-debugging-port=9222" in res["instructions"]
    assert "Profile 2" in res["instructions"]

    # Status check
    status = mgr.get_status(reg_id)
    assert status["status"] in ("WAITING_FOR_USER", "REGISTERING")
    assert status["display_name"] == "My Work Chrome"
    assert status["profile_identifier"] == "Profile 2"

    # Verify persistence file exists and contains NO credentials
    assert reg_file.exists()
    with open(reg_file, "r") as f:
        stored = json.load(f)
    assert reg_id in stored
    serialized = json.dumps(stored)
    for forbidden in ["password", "secret", "cookie", "token", "auth_token"]:
        assert forbidden not in serialized.lower() or forbidden in ("profile_identifier",)


def test_registration_probe_and_confirm_failures(tmp_path):
    """Tests confirming an inactive port returns a descriptive failure and guidance."""
    reg_file = tmp_path / "test_registrations.json"
    mgr = BrowserRegistrationManager(registrations_file=reg_file)

    # Use an unallocated port
    start_res = mgr.start_registration(
        display_name="Test Inactive",
        cdp_url="http://127.0.0.1:59999",
        port=59999
    )
    reg_id = start_res["registration_id"]

    # Confirm should safely fail with guidance
    confirm_res = mgr.confirm_registration(reg_id)
    assert confirm_res["success"] is False
    assert "Unable to connect to Chrome" in confirm_res["error"]
    assert confirm_res["status"] == "WAITING_FOR_USER"


def test_registration_revocation(tmp_path):
    """Tests that revoking a registration terminates control and disallows future use."""
    reg_file = tmp_path / "test_registrations.json"
    mgr = BrowserRegistrationManager(registrations_file=reg_file)

    start_res = mgr.start_registration(display_name="Revocable Chrome")
    reg_id = start_res["registration_id"]

    revoke_res = mgr.revoke_registration(reg_id)
    assert revoke_res["success"] is True
    assert revoke_res["status"] == "REVOKED"

    # Status reflects revoked
    status = mgr.get_status(reg_id)
    assert status["status"] == "REVOKED"

    # Confirming a revoked browser is rejected
    confirm_res = mgr.confirm_registration(reg_id)
    assert confirm_res["success"] is False
    assert "REVOKED" in confirm_res["error"]

    # Attempting to retrieve connection returns error
    _, _, err = mgr.get_connected_browser(reg_id)
    assert "REVOKED" in err


def test_mock_cdp_probe(mock_cdp_server, tmp_path):
    """Tests successful CDP probing against mock HTTP CDP server."""
    reg_file = tmp_path / "test_registrations.json"
    mgr = BrowserRegistrationManager(registrations_file=reg_file)

    is_active, meta = mgr.probe_cdp_endpoint(mock_cdp_server, timeout_seconds=2.0)
    assert is_active is True
    assert "Chrome/125" in meta["browser"]
    assert meta["protocol_version"] == "1.3"


def test_service_layer_registration_tools():
    """Tests the service layer registration methods and tab management."""
    service = BrowserQAService()

    # Start registration via service
    start_res = service.browser_register_start(display_name="Service Test Chrome", port=9333)
    reg_id = start_res["registration_id"]
    assert start_res["status"] in ("WAITING_FOR_USER", "REGISTERING")

    # List registrations
    reg_list = service.browser_register_list()
    assert any(r["registration_id"] == reg_id for r in reg_list)

    # Status via service
    status = service.browser_register_status(reg_id)
    assert status["registration_id"] == reg_id

    # Revocation via service
    rev_res = service.browser_register_revoke(reg_id)
    assert rev_res["success"] is True
    assert rev_res["status"] == "REVOKED"


def test_session_create_registered_guard():
    """Tests that requesting registered browser without a valid connected registration fails explicitly."""
    service = BrowserQAService()

    with pytest.raises(ValueError) as excinfo:
        service.session_create(
            session_id="unregistered_session",
            browser_target="registered",
            registration_id="reg_does_not_exist"
        )
    assert "Registered browser" in str(excinfo.value) or "unavailable" in str(excinfo.value)


def test_security_redaction_guarantees():
    """Tests that credentials, Authorization headers, and cookies are redacted."""
    headers = {
        "authorization": "Bearer secret_jwt_token_12345",
        "cookie": "session_id=abc123xyz; secure_token=super_secret",
        "x-api-key": "sk-live-abcdef1234567890",
        "content-type": "application/json"
    }
    redacted_h = redact_headers(headers)
    assert redacted_h["authorization"] == "Bearer [REDACTED]"
    assert "session_id=[REDACTED]" in redacted_h["cookie"]
    assert "secure_token=[REDACTED]" in redacted_h["cookie"]
    assert "super_secret" not in redacted_h["cookie"]
    assert "abc123xyz" not in redacted_h["cookie"]
    assert redacted_h["x-api-key"] == "[REDACTED]"
    assert redacted_h["content-type"] == "application/json"

    # Body string redaction
    json_body = '{"username": "john", "password": "MySuperSecretPassword", "token": "abcdef"}'
    redacted_b = redact_body_string(json_body)
    assert "MySuperSecretPassword" not in redacted_b
    assert "[REDACTED]" in redacted_b

    # Action value masking for password fields
    masked_val = redact_action_value("#password-input", "TopSecret999!")
    assert masked_val == "[REDACTED]"


def test_scope_guard_navigation_enforcement():
    """Tests origin scope guards block unauthorized domains."""
    service = BrowserQAService()
    session_id = "scope_test_session"

    service.session_create(
        session_id=session_id,
        browser_mode="headless",
        browser_target="managed",
        target_origin="https://client.example.com",
        allowed_origins=["https://client.example.com", "https://auth.example.com"]
    )

    # Allowed navigation
    valid, _ = service.controller.session_mgr.validate_navigation(session_id, "https://client.example.com/dashboard")
    assert valid is True

    valid_auth, _ = service.controller.session_mgr.validate_navigation(session_id, "https://auth.example.com/login")
    assert valid_auth is True

    # Blocked external navigation (e.g. personal email or banking)
    blocked, err = service.controller.session_mgr.validate_navigation(session_id, "https://mail.google.com")
    assert blocked is False
    assert "Scope Guard" in err

    service.session_close(session_id)
