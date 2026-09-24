"""Live read-only tests against user's connected Chrome (via bridge :8002).
Run:  py tests/test_live_readonly.py   (PYTHONPATH=src + .venv site-packages)
NO clicks/navigates/types — inspect + screenshot + audits only.
"""
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "src"))

from browser_qa.service import BrowserQAService

PASS, FAIL = [], []


def check(name, fn):
    try:
        out = fn()
        PASS.append(name)
        print(f"  PASS {name} -> {out}", flush=True)
    except Exception as e:
        FAIL.append(name)
        print(f"  FAIL {name}: {e}", flush=True)


s = BrowserQAService()
CTX = {}


def t_ext():
    r = s.extension_status()
    assert r["extension_connected"] is True, r
    return "connected"


def t_inspect():
    obs = s.page_inspect("live")
    els = obs["interactive_elements"]
    assert len(els) > 0, "no elements"
    CTX["ref"] = els[0]["ref_id"]
    return f"{len(els)} elements, url={obs['url'][:60]}"


def t_see():
    see = s.page_see(session_id="live")
    assert see["success"] and see.get("visual"), "no visual in auto mode"
    assert see.get("text"), "no text fallback"
    return f"visual={len(see['visual'])} chars, text_items={see['text'].get('count')}"


def t_fingerprint():
    fp = s.element_fingerprint(CTX["ref"], "live")
    assert fp["success"], fp
    rel = s.relocate_element(fp["fingerprint"], "live")
    assert rel["success"], rel
    return f"fp {CTX['ref']} -> relocated {rel['ref_id']} score={rel['score']}"


def t_find():
    r = s.find_element("login", "live")
    assert r["success"]
    return f"{r['count']} candidates"


def t_vitals():
    v = s.page_vitals("live")
    assert v["success"], v
    return f"TTFB={v.get('ttfb_ms')} FCP={v.get('first_contentful_paint_ms')}"


def t_a11y():
    a = s.page_a11y_audit("live")
    assert a["success"], a
    return f"score={a['score']} violations={len(a['violations'])}"


def t_table():
    t = s.extract_table("", "live")
    assert isinstance(t, dict) and "success" in t
    return f"success={t['success']} total={t.get('total_tables')}"


def t_textpos():
    tp = s.text_with_positions("live", max_items=30)
    assert tp["success"], tp
    return f"{tp['count']} positioned texts"


def t_understand():
    u = s.page_understand("live")
    assert u["success"], u
    return f"zones={u['zone_counts']}"


def t_auth_health():
    a = s.auth_status("live")
    h = s.session_health_check("live")
    assert a["success"] and h["success"]
    return f"logged_in={a.get('logged_in')} health={h['recommended_action']}"


if __name__ == "__main__":
    print("Live read-only tests on user's Chrome...", flush=True)
    for n, f in [("ext_connected", t_ext), ("inspect", t_inspect), ("see", t_see),
                 ("fingerprint_relocate", t_fingerprint), ("find", t_find),
                 ("vitals", t_vitals), ("a11y", t_a11y), ("table", t_table),
                 ("textpos", t_textpos), ("understand", t_understand),
                 ("auth_health", t_auth_health)]:
        check(n, f)
    print(f"\nLIVE RESULT: {len(PASS)} passed, {len(FAIL)} failed", flush=True)
    sys.exit(1 if FAIL else 0)
