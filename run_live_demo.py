import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add src to python path
src_dir = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(src_dir))

from browser_qa.service import BrowserQAService

def main():
    svc = BrowserQAService()
    session_id = "live_demo"

    print("=" * 60)
    print("🚀 [STEP 1] Initializing Isolated Browser Context...")
    print("=" * 60)
    svc.session_create(session_id=session_id, browser_mode="headless")
    print("✅ Playwright Chromium Browser started in Headless mode.")

    print("\n" + "=" * 60)
    print("🌐 [STEP 2] Navigating to https://taliyotechnologies.com...")
    print("=" * 60)
    nav = svc.browser_navigate(url="https://taliyotechnologies.com", session_id=session_id)
    print(f"✅ Navigation successful! Current URL: {nav.get('current_url')}")

    print("\n" + "=" * 60)
    print("🔍 [STEP 3] Semantic Page Observation (Accessibility Tree)...")
    print("=" * 60)
    ins = svc.page_inspect(session_id=session_id)
    print(f"✅ Page Title: {ins.get('title')}")
    print(f"✅ Active Observation ID: {ins.get('observation_id')}")
    elements = ins.get("interactive_elements", [])
    print(f"✅ Total Interactive Elements Discovered: {len(elements)}")
    print("📌 First 5 Semantic Interactive Elements:")
    for el in elements[1:6]:
        print(f"   👉 [{el.get('ref', 'N/A')}] <{el.get('role')}> \"{el.get('name')}\"")

    print("\n" + "=" * 60)
    print("📸 [STEP 4] Capturing Visual Evidence (Full-Page Screenshot)...")
    print("=" * 60)
    shot = svc.browser_screenshot(session_id=session_id, full_page=True)
    shot_path = shot.get("screenshot_path")
    print(f"✅ High-Res Screenshot Captured: {shot_path}")

    print("\n" + "=" * 60)
    print("📡 [STEP 5] Telemetry & Network Interception...")
    print("=" * 60)
    net = svc.network_list(session_id=session_id, limit=5)
    print(f"✅ Intercepted {len(net)} Sample HTTP Transactions:")
    for r in net[:4]:
        url = r.get("url", "")
        if len(url) > 60:
            url = url[:57] + "..."
        print(f"   ⚡ {r.get('method')} {url} -> Status {r.get('status')}")

    print("\n" + "=" * 60)
    print("📊 [STEP 6] Generating Executive QA Audit Report...")
    print("=" * 60)
    report = svc.qa_report(session_id=session_id, format_type="markdown")
    for line in report.split("\n")[:14]:
        print(f"   {line}")

    print("\n" + "=" * 60)
    print("🧹 [STEP 7] Tearing Down Browser Session...")
    print("=" * 60)
    svc.session_close(session_id=session_id)
    print("✅ Session closed and memory released successfully!")

if __name__ == "__main__":
    main()
