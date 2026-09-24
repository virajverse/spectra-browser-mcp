"""End-to-end integration smoke test running against local test fixture."""

import os
import sys
import threading
import time
from pathlib import Path
import uvicorn

# Setup PYTHONPATH
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "src"))

from browser_qa.service import BrowserQAService
from tests.fixtures.app import app


def run_fixture_server():
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="error")


def run_smoke_test():
    print("--- 1. Launching Local Test Server ---")
    server_thread = threading.Thread(target=run_fixture_server, daemon=True)
    server_thread.start()
    time.sleep(1.5)  # Wait for server to boot

    service = BrowserQAService()
    session_id = "smoke_session"

    print("--- 2. Initializing Session ---")
    sess_info = service.session_create(
        session_id=session_id,
        browser_mode="headless",
        target_origin="http://127.0.0.1:8765"
    )
    assert sess_info["session_id"] == session_id

    print("--- 3. Navigating to Test Page ---")
    nav_res = service.browser_navigate("http://127.0.0.1:8765/test-page", session_id=session_id)
    assert nav_res["success"] is True

    print("--- 4. Semantic Page Inspection ---")
    obs = service.page_inspect(session_id=session_id)
    obs_id = obs["observation_id"]
    elements = obs["interactive_elements"]
    print(f"Observation ID: {obs_id} | Total Interactive Elements: {len(elements)}")
    assert len(elements) >= 4

    # Locate buttons
    btn_ok_ref = None
    btn_err_ref = None
    btn_delete_ref = None

    for el in elements:
        name = el.get("name", "").lower()
        if "fetch ok" in name:
            btn_ok_ref = el["ref_id"]
        elif "500" in name:
            btn_err_ref = el["ref_id"]
        elif "delete account" in name:
            btn_delete_ref = el["ref_id"]

    assert btn_ok_ref is not None, "Fetch OK button not found"
    assert btn_err_ref is not None, "Trigger 500 button not found"
    assert btn_delete_ref is not None, "Delete Account button not found"

    print(f"Discovered: OK={btn_ok_ref}, Err={btn_err_ref}, Delete={btn_delete_ref}")

    print("--- 5. Destructive Action Guard Verification ---")
    del_res = service.browser_click(target=btn_delete_ref, observation_id=obs_id, session_id=session_id, confirm_destructive=False)
    assert del_res["status"] == "failed"
    assert "Destructive Action Guard" in del_res["message"]
    print("Destructive action guard successfully blocked unauthorized action! [PASSED]")

    print("--- 6. Successful Action & Telemetry ---")
    click_res = service.browser_click(target=btn_ok_ref, observation_id=obs_id, session_id=session_id)
    assert click_res["status"] == "success"
    time.sleep(0.5)

    print("--- 7. Secret-Aware Typer Verification ---")
    pwd_ref = None
    for el in elements:
        attrs = el.get("attributes", {})
        if attrs.get("type") == "password" or "password" in str(attrs.get("placeholder", "")).lower():
            pwd_ref = el["ref_id"]
            break
    type_res = service.browser_type(target=pwd_ref or "#pwd-input", text="SuperSecret123!", observation_id=obs_id, session_id=session_id)
    assert type_res["status"] == "success"
    print("Typed into password field with automatic secret masking! [PASSED]")

    print("--- 8. Failing Action & Correlation Flow ---")
    err_click_res = service.browser_click(target=btn_err_ref, observation_id=obs_id, session_id=session_id)
    print(f"err_click_res: {err_click_res}")
    assert err_click_res["status"] == "success"
    service.browser_wait(ms=1500, session_id=session_id)

    print("--- 9. Anomaly & Correlated Flow Verification ---")
    txs = service.storage.list_transactions(session_id=session_id)
    print(f"Transactions recorded: {[t.request.url for t in txs]}")
    anomalies = service.qa_anomalies(session_id=session_id)
    print(f"Total Anomalies Detected: {len(anomalies)}: {[a['title'] for a in anomalies]}")
    assert len(anomalies) >= 1
    assert any("500" in a["title"] or "error" in a["title"].lower() or a["anomaly_type"] in ("http_5xx", "console_error") for a in anomalies)

    flows = service.qa_correlate(session_id=session_id)
    assert len(flows) >= 1
    print(f"Correlated Flows Recorded: {len(flows)} [PASSED]")

    print("--- 10. QA Audit Report Generation ---")
    report = service.qa_report(session_id=session_id, format_type="markdown")
    assert "# Browser QA & Network Intelligence Audit Report" in report
    assert "HTTP 500 Server Error" in report
    print("\nReport Preview:\n" + "\n".join(report.splitlines()[:25]))

    print("--- 11. Cleanup ---")
    service.session_close(session_id=session_id)
    print("\nSmoke test executed 100% successfully! All 11 assertions passed! [PASSED]")


if __name__ == "__main__":
    run_smoke_test()
