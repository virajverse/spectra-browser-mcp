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


if __name__ == "__main__":
    test_bridge_root()
    test_session_create_tool_endpoint()
    print("All OpenAPI bridge tests passed successfully! [PASSED]")
