"""Real MCP wire-protocol tests: spawns `browser_qa.server` over stdio and talks
JSON-RPC (initialize → tools/list → tools/call), asserting on actual MCP responses.

Run:  D:\\Company work\\.venv\\Scripts\\python.exe tests/test_mcp_wire.py
No Chrome needed (pure-local tools + graceful no-extension paths).
"""
import base64
import json
import subprocess
import sys
import threading
from io import BytesIO
from pathlib import Path
from queue import Queue, Empty

PROJECT_DIR = Path(__file__).resolve().parent.parent

PASS, FAIL = [], []


def tiny_png_b64(color):
    from PIL import Image
    img = Image.new("RGB", (8, 8), color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class McpClient:
    def __init__(self):
        import os
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        env["PYTHONPATH"] = str(PROJECT_DIR / "src")
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "browser_qa.server"],
            cwd=str(PROJECT_DIR), env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1,
        )
        self._id = 0
        self._q: Queue = Queue()
        threading.Thread(target=self._reader, daemon=True).start()
        resp = self.request("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "wire-test", "version": "1.0"},
        })
        assert "result" in resp, resp
        self.notify("notifications/initialized", {})

    def _reader(self):
        for line in self.proc.stdout:
            line = line.strip()
            if line:
                self._q.put(json.loads(line))

    def request(self, method, params, timeout=60):
        self._id += 1
        rid = self._id
        self.proc.stdin.write(json.dumps(
            {"jsonrpc": "2.0", "id": rid, "method": method, "params": params}) + "\n")
        self.proc.stdin.flush()
        deadline = timeout
        while deadline > 0:
            try:
                msg = self._q.get(timeout=min(5, deadline))
            except Empty:
                deadline -= 5
                continue
            if msg.get("id") == rid:
                return msg
        raise TimeoutError(f"no response for {method}")

    def notify(self, method, params):
        self.proc.stdin.write(json.dumps(
            {"jsonrpc": "2.0", "method": method, "params": params}) + "\n")
        self.proc.stdin.flush()

    def call(self, name, args):
        resp = self.request("tools/call", {"name": name, "arguments": args})
        assert "result" in resp, resp
        res = resp["result"]
        # FastMCP: dict results → content[0].text (JSON), list results → structuredContent.result
        sc = res.get("structuredContent")
        if isinstance(sc, dict) and "result" in sc:
            return sc["result"]
        texts = [c["text"] for c in res.get("content", []) if c.get("type") == "text"]
        assert texts, resp
        return json.loads(texts[0])

    def close(self):
        try:
            self.proc.kill()
        except Exception:
            pass


def check(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  PASS {name}", flush=True)
    except Exception as e:
        FAIL.append(name)
        print(f"  FAIL {name}: {e}", flush=True)


CLIENT: McpClient = None  # type: ignore


def test_list():
    resp = CLIENT.request("tools/list", {})
    names = sorted(t["name"] for t in resp["result"]["tools"])
    assert len(names) == 99, len(names)
    print(f"    (server reports {len(names)} tools over MCP wire)", flush=True)


def test_memory_wire():
    assert CLIENT.call("session_memory_set", {"session_id": "w", "key": "goal", "value": "x"})["success"]
    g = CLIENT.call("session_memory_get", {"session_id": "w", "key": "goal"})
    assert g["found"] and g["value"] == "x"
    assert CLIENT.call("session_memory_delete", {"session_id": "w", "key": "goal"})["deleted"]


def test_vision_wire():
    assert CLIENT.call("vision_set_mode", {"mode": "text", "session_id": "w"})["vision_mode"] == "text"
    see = CLIENT.call("page_see", {"session_id": "w"})
    assert see["success"] and see["visual"] is None
    CLIENT.call("vision_set_mode", {"mode": "auto", "session_id": "w"})


def test_visual_compare_wire():
    r = tiny_png_b64("red")
    same = CLIENT.call("visual_compare", {"baseline": r, "current": r})
    assert same["similarity_percent"] == 100.0
    diff = CLIENT.call("visual_compare", {"baseline": r, "current": tiny_png_b64("blue")})
    assert diff["similarity_percent"] == 0.0 and diff["bbox"] is not None


def test_annotate_wire():
    ann = CLIENT.call("screenshot_annotate", {
        "image": tiny_png_b64("red"),
        "annotations": [{"bbox": [1, 1, 4, 3], "label": "BUG"}]})
    assert ann["success"] and ann["annotated_count"] == 1


def test_macro_test_wire():
    assert CLIENT.call("macro_start_recording", {"name": "wm"})["success"]
    assert CLIENT.call("macro_stop_recording", {})["name"] == "wm"
    assert CLIENT.call("macro_run", {"name": "wm", "session_id": "w"})["success"]
    assert CLIENT.call("test_start_recording", {"name": "wt", "session_id": "w"})["success"]
    assert CLIENT.call("test_stop_recording", {"name": "wt"})["success"]
    assert CLIENT.call("test_export", {"name": "wt"})["success"]
    assert CLIENT.call("action_timeline", {"session_id": "w", "limit": 5}) is not None


def test_health_wire():
    h = CLIENT.call("session_health_check", {"session_id": "w"})
    assert h["success"] and h["recommended_action"] == "connect_extension"
    a = CLIENT.call("auth_status", {"session_id": "w"})
    assert a["success"]


def test_tabs_scripts_wire():
    assert CLIENT.call("tab_create", {"name": "t1", "url": "https://example.com", "session_id": "w"})["success"]
    assert any(t["name"] == "t1" for t in CLIENT.call("tab_list", {"session_id": "w"}))
    assert CLIENT.call("script_library_add", {"name": "s1", "js_code": "(() => 1)()", "session_id": "w"})["success"]
    assert CLIENT.call("adapter_save", {"site": "ex.com", "aliases": {"q": "input"}, "session_id": "w"})["success"]
    hit = CLIENT.call("adapter_resolve", {"site": "ex.com", "friendly_name": "q", "session_id": "w"})
    assert hit["selector"] == "input"


if __name__ == "__main__":
    print("Spawning real MCP server over stdio...", flush=True)
    CLIENT = McpClient()
    try:
        check("wire_tools_list_99", test_list)
        check("wire_memory", test_memory_wire)
        check("wire_vision", test_vision_wire)
        check("wire_visual_compare", test_visual_compare_wire)
        check("wire_annotate", test_annotate_wire)
        check("wire_macro_test", test_macro_test_wire)
        check("wire_health", test_health_wire)
        check("wire_tabs_scripts", test_tabs_scripts_wire)
    finally:
        CLIENT.close()
    print(f"\nWIRE RESULT: {len(PASS)} passed, {len(FAIL)} failed", flush=True)
    sys.exit(1 if FAIL else 0)
