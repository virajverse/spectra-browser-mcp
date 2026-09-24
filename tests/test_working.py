"""Working tests for Spectra Browser MCP (99 tools) — zero-dependency, no Chrome needed.

Run:  .venv/Scripts/python.exe tests/test_working.py   (or D:\\Company work\\.venv)
Covers: tool registry, memory, tabs, macros, test-cases, timeline, visual-local,
        graceful no-Chrome failures, scripts/adapters, adaptive vision.
"""
import asyncio
import base64
import sys
import traceback
from io import BytesIO
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "src"))

from PIL import Image  # noqa: E402

from browser_qa.service import BrowserQAService  # noqa: E402
import browser_qa.server as server  # noqa: E402

PASS, FAIL = [], []


def check(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  PASS {name}")
    except Exception as e:
        FAIL.append((name, e))
        print(f"  FAIL {name}: {e}")
        traceback.print_exc()


def b64img(color="red", size=(80, 60)):
    img = Image.new("RGB", size, color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def test_tool_registry():
    names = sorted(t.name for t in asyncio.run(server.mcp.list_tools()))
    assert len(names) == 99, f"expected 99 tools, got {len(names)}"
    for must in ["page_see", "vision_set_mode", "vision_get_mode", "element_fingerprint",
                 "visual_compare", "screenshot_annotate", "page_vitals", "page_a11y_audit",
                 "extract_table", "macro_run", "test_export", "tab_create", "session_memory_set",
                 "browser_click_retry", "browser_click_fallback", "script_library_run",
                 "adapter_resolve", "browser_scroll_harvest", "find_element_smart"]:
        assert must in names, f"missing tool {must}"


def test_session_memory():
    s = BrowserQAService()
    sid = "t_mem"
    assert s.session_memory_set(sid, "goal", "buy Pro")["success"]
    g = s.session_memory_get(sid, "goal")
    assert g["found"] and g["value"] == "buy Pro"
    m = s.session_memory_get(sid, "nope", default="dflt")
    assert not m["found"] and m["value"] == "dflt"
    assert "goal" in s.session_memory_list(sid)["keys"]
    assert s.session_memory_delete(sid, "goal")["deleted"]
    s.session_memory_set(sid, "a", 1)
    assert s.session_memory_clear(sid)["cleared_keys"] >= 1


def test_tabs():
    s = BrowserQAService()
    sid = "t_tabs"
    c = s.tab_create("login", url="https://example.com/login", session_id=sid)
    assert c["success"] and c["name"] == "login"
    assert any(h["name"] == "login" for h in s.tab_list(sid))
    sw = s.tab_switch("login", sid)  # no Chrome → graceful False, never raise
    assert isinstance(sw, dict) and "success" in sw
    assert s.tab_close("login", sid)["success"]
    assert not s.tab_close("login", sid)["success"]


def test_macros():
    s = BrowserQAService()
    assert s.macro_start_recording("m1")["success"]
    assert s.macro_stop_recording()["name"] == "m1"
    assert any(m["name"] == "m1" for m in s.macro_list())
    assert s.macro_get("m1")["success"]
    r = s.macro_run("m1")  # empty macro → trivially successful
    assert r["success"] and r["total"] == 0
    assert s.macro_delete("m1")["deleted"]
    assert not s.macro_run("nope")["success"]


def test_testcases():
    s = BrowserQAService()
    assert s.test_start_recording("tc1")["success"]
    assert s.test_stop_recording("tc1")["success"]
    ex = s.test_export("tc1")
    assert ex["success"] and "steps" in ex and "replay_hint" in ex
    assert s.test_get("tc1")["success"]
    assert any(t["name"] == "tc1" for t in s.test_list())
    assert s.test_delete("tc1")["deleted"]


def test_timeline_and_failed():
    s = BrowserQAService()
    sid = "t_tl"
    s.tab_create("x", url="https://example.com", session_id=sid)
    tl = s.action_timeline(sid)
    assert len(tl) >= 1 and tl[-1]["action_type"] == "tab_create"
    assert s.action_last(sid)["success"]
    assert isinstance(s.failed_targets_list(sid), list)
    assert s.failed_targets_clear(sid)["success"]
    # retry/fallback without Chrome → False, no raise
    assert not s.browser_click_retry("@1", session_id=sid, max_attempts=2, backoff_ms=10)["success"]
    assert not s.browser_click_fallback(["@1", "@2"], session_id=sid)["success"]
    assert len(s.failed_targets_list(sid)) >= 1


def test_health_auth():
    s = BrowserQAService()
    h = s.session_health_check("default")
    assert h["success"] and h["recommended_action"] == "connect_extension"
    a = s.auth_status("default")
    assert a["success"] and a.get("logged_in") is None


def test_visual_local():
    s = BrowserQAService()
    r, b = b64img("red"), b64img("blue")
    same = s.visual_compare(r, r)
    assert same["success"] and same["similarity_percent"] == 100.0 and same["verdict"] == "same"
    diff = s.visual_compare(r, b)
    assert diff["success"] and diff["similarity_percent"] == 0.0 and diff["bbox"] is not None
    bad = s.visual_compare("", b)
    assert not bad["success"]
    ann = s.screenshot_annotate(image=r, annotations=[{"bbox": [5, 5, 30, 25], "label": "BUG"}])
    assert ann["success"] and ann["annotated_count"] == 1 and ann["base64"].startswith("data:image/png;base64,")
    # file-path input also works
    p = PROJECT_DIR / "screenshots" / "_test_red.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 40), "red").save(p)
    try:
        assert s.visual_compare(str(p), str(p))["similarity_percent"] == 100.0
    finally:
        p.unlink(missing_ok=True)


def test_chrome_graceful():
    s = BrowserQAService()
    for res in [s.element_fingerprint("@1"), s.find_element("login"),
                s.relocate_element({"name": "x", "role": "button", "tag": "button"}),
                s.page_vitals(), s.page_a11y_audit(), s.extract_table(),
                s.text_with_positions(), s.page_understand(),
                s.find_element_smart("login button"),
                s.browser_scroll_harvest(target_count=3, max_scrolls=1),
                s.script_library_run("missing")]:
        assert isinstance(res, dict) and res.get("success") is False, res


def test_scripts_adapters():
    s = BrowserQAService()
    sid = "t_sa"
    assert s.script_library_add("b1", "(() => 1)()", "d", sid)["success"]
    assert any(x["name"] == "b1" for x in s.script_library_list(sid))
    assert s.script_library_get("b1", sid)["success"]
    assert not s.script_library_run("b1", sid)["success"]  # needs Chrome
    assert s.script_library_delete("b1", sid)["deleted"]
    assert s.adapter_save("example.com", {"search": "input[name=q]"}, session_id=sid)["aliases_count"] == 1
    hit = s.adapter_resolve("example.com", "search", session_id=sid)
    assert hit["success"] and hit["selector"] == "input[name=q]" and hit["source"] == "adapter"
    ex = s.extract_by_description({"price": "price thing"}, session_id=sid)
    assert ex["success"] and "price" in ex["data"]  # None without Chrome, but call succeeds


def test_vision_modes():
    s = BrowserQAService()
    sid = "t_vis"
    assert s.vision_set_mode("text", sid)["vision_mode"] == "text"
    assert s.vision_get_mode(sid)["vision_mode"] == "text"
    see = s.page_see(session_id=sid)
    assert see["success"] and see["visual"] is None  # text mode omits image
    assert not s.vision_set_mode("hologram", sid)["success"]
    assert s.vision_set_mode("auto", sid)["vision_mode"] == "auto"


if __name__ == "__main__":
    print("Running working tests (no Chrome required)...")
    check("tool_registry_99", test_tool_registry)
    check("session_memory", test_session_memory)
    check("tabs", test_tabs)
    check("macros", test_macros)
    check("testcases", test_testcases)
    check("timeline_failed_retry", test_timeline_and_failed)
    check("health_auth", test_health_auth)
    check("visual_local", test_visual_local)
    check("chrome_graceful", test_chrome_graceful)
    check("scripts_adapters", test_scripts_adapters)
    check("vision_modes", test_vision_modes)
    print(f"\nRESULT: {len(PASS)} passed, {len(FAIL)} failed (total {len(PASS) + len(FAIL)})")
    sys.exit(1 if FAIL else 0)
