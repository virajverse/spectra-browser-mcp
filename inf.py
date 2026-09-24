"""Helper: call Infinity Scraper bridge (port 8000) tools via HTTP POST."""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8000"


def call(tool, payload=None, timeout=120):
    data = json.dumps(payload or {}).encode()
    req = urllib.request.Request(f"{BASE}/{tool}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def get(path, timeout=30):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=timeout) as r:
        return json.loads(r.read().decode())


if __name__ == "__main__":
    tool = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else "{}"
    # allow @file.json to avoid shell quoting issues
    if arg.startswith("@"):
        payload = json.loads(open(arg[1:], encoding="utf-8").read())
    else:
        payload = json.loads(arg)
    res = call(tool, payload)
    with open("inf_out.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    txt = json.dumps(res, indent=1, ensure_ascii=True)
    print(txt[:3000])
