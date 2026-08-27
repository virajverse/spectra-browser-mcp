"""Tests for OpenAPI bridge endpoints."""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "src"))

from openapi_bridge import app

client = TestClient(app)


def test_bridge_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["total_tools"] >= 25
    assert "browser_click" in data["tools"]
    assert "page_inspect" in data["tools"]
    assert "network_list" in data["tools"]
    assert "qa_report" in data["tools"]
    print(f"OpenAPI Bridge exposed {data['total_tools']} tools successfully! [PASSED]")


def test_session_create_tool_endpoint():
    payload = {
        "session_id": "api_test",
        "browser_mode": "headless"
    }
    response = client.post("/session_create", json=payload)
    if response.status_code != 200:
        print("Error detail:", response.status_code, response.json())
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "api_test"
    print("Direct invocation of /session_create via OpenAPI bridge passed! [PASSED]")

    # Cleanup
    client.post("/session_close", json={"session_id": "api_test"})


def test_registration_endpoints_via_bridge():
    # 1. Start registration
    start_payload = {
        "display_name": "OpenAPI Bridge Chrome",
        "port": 9444
    }
    res = client.post("/browser_register_start", json=start_payload)
    assert res.status_code == 200
    data = res.json()
    assert "registration_id" in data
    reg_id = data["registration_id"]
    assert data["display_name"] == "OpenAPI Bridge Chrome"
    assert data["status"] in ("CONNECTED", "WAITING_FOR_USER", "REGISTERING")

    # 2. List registrations
    list_res = client.post("/browser_register_list", json={})
    assert list_res.status_code == 200
    regs = list_res.json()
    assert any(r["registration_id"] == reg_id for r in regs)

    # 3. Status
    status_res = client.post("/browser_register_status", json={"registration_id": reg_id})
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["registration_id"] == reg_id

    # 4. Revoke
    rev_res = client.post("/browser_register_revoke", json={"registration_id": reg_id})
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["success"] is True
    assert rev_data["status"] == "REVOKED"


if __name__ == "__main__":
    test_bridge_root()
    test_session_create_tool_endpoint()
    test_registration_endpoints_via_bridge()
    print("All OpenAPI bridge tests passed successfully! [PASSED]")
