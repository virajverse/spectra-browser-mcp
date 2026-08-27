# 🌐 SpectraBrowser MCP
### Autonomous Cognitive Browser Automation & Full-Spectrum Network QA Suite

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium%20%7C%20Chrome-green.svg)](https://playwright.dev/)
[![FastMCP](https://img.shields.io/badge/FastMCP-Model%20Context%20Protocol-purple.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**SpectraBrowser MCP** is an enterprise-grade, **zero-hardcoding**, capability-driven Model Context Protocol (MCP) server that empowers autonomous AI agents (**Open WebUI, Antigravity, Claude, GPT-4o, DeepSeek, Qwen**) to intelligently explore, interact with, audit, and self-heal on any web application.

---

## 🌟 Why SpectraBrowser?

* 🧠 **Cognitive Screen Diagnosis (`screen_diagnosis`)**: Automatically detects intermediate states: **Cloudflare Turnstile**, **Auth/Login Gates**, **Loading Spinners**, and **Interactive SPAs** with zero agent confusion.
* 🤝 **Human-in-the-Loop ("Pooch Kar Karo")**: Dedicated `session_ask_human()` tool allows the agent to pause, ask the user decisions/options, and resume seamlessly.
* ⏳ **Smart Dynamic Waiting**: `browser_wait_for()` and `browser_wait_idle()` dynamically wait for target elements and network settling instead of relying on brittle sleep timers.
* 🎯 **Zero Hardcoding (`@ref` Priority)**: Eliminates fragile CSS selectors. Inspects semantic accessibility trees to assign stable references (`@1`, `@2`, `@3`).
* 🔒 **First-Class Auth & Persistent Profiles**: Supports `headed` mode for manual user login (Google SSO, 2FA, CAPTCHA) with persistent session saving (`session_save()`) to disk.
* ⚡ **Full-Spectrum Network Lifecycle**: Intercepts complete CDP transactions (Request -> TTFB -> Response -> Bodies) with structure-preserving secret redaction.
* 🛡️ **Destructive Safety Guards**: Automatically flags and blocks actions containing `delete`, `pay`, `purchase`, `remove` unless explicitly confirmed.
* 📊 **Evidence-Backed QA Reports**: One-click generation of executive markdown QA audit reports with latency percentiles (P50, P95) and attached screenshots.

---

## 🚀 60-Second Quick Start (For New Users)

### Windows (1-Click Setup)
1. **Double-click `install.bat`** (Automatically creates `.venv`, installs requirements, and downloads Playwright Chromium).
2. **Double-click `run_bridge.bat`** (Starts the OpenAPI Bridge on port **`8002`**).

### Linux / macOS
```bash
# 1. Clone repository
git clone https://github.com/virajverse/spectra-browser-mcp.git
cd spectra-browser-mcp

# 2. Run automated setup
chmod +x install.sh
./install.sh

# 3. Start the bridge
python openapi_bridge.py
```

---

## 🔌 Integration Options

### 1. Open WebUI (FastAPI Bridge)
1. Ensure the bridge is running (`python openapi_bridge.py` on port `8002`).
2. In Open WebUI, navigate to **Admin Settings -> Tools -> Add Tool Server**.
3. Enter URL: `http://127.0.0.1:8002/openapi.json`.
4. All **31 tools** are now instantly available to your AI agents!

### 2. Antigravity / Claude Desktop (Native STDIO)
Add to your `mcp_config.json`:
```json
{
  "mcpServers": {
    "spectra-browser": {
      "command": "python",
      "args": ["-m", "browser_qa.server"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "PYTHONPATH": "src"
      }
    }
  }
}
```

---

## 🛠️ Complete MCP Tool Catalog (31 Tools)

### 1. Session Lifecycle & Human-in-the-Loop
| Tool | Description |
|---|---|
| `session_create` | Initializes isolated browser context (supports `headed` mode for manual login). |
| `session_status` | Returns session lifecycle state (`active`, `paused`), URL, and transaction telemetry. |
| `session_ask_human` | 🤝 **Interactive Protocol:** Pauses execution to ask user instructions or choices before acting. |
| `session_pause` | Pauses automation so human can complete manual login, 2FA, or CAPTCHA. |
| `session_resume` | Resumes agent automation with optional user decision recorded in telemetry. |
| `session_save` | Persists browser storage state (cookies & localStorage) to `profiles/<id>/state/`. |
| `session_close` | Cleanly closes browser context and releases memory. |

### 2. Browser Interaction & Smart Waiting
| Tool | Description |
|---|---|
| `browser_navigate` | Navigates to URL within session allowed origins. |
| `browser_click` | Clicks element by `@ref`, role, or text. Destructive actions require `confirm_destructive=True`. |
| `browser_type` | Types text into input fields. Automatically redacts passwords and tokens. |
| `browser_select` | Selects dropdown options. |
| `browser_scroll` | Scrolls viewport up or down smoothly. |
| `browser_press` | Simulates keyboard key presses (`Enter`, `Tab`, `Escape`). |
| `browser_wait` | Basic sleep timer for specified milliseconds. |
| `browser_wait_for` | ⏳ **Smart Wait:** Dynamically waits for target element (`@ref`, text, or selector) to become visible/hidden. |
| `browser_wait_idle` | ⏳ **Network Settle:** Waits for in-flight requests and DOM mutations to finish. |
| `browser_screenshot` | Captures high-res screenshot and saves to `screenshots/`. |

### 3. Semantic Page Observation & Screen Diagnosis
| Tool | Description |
|---|---|
| `page_inspect` | 🧠 Returns accessibility tree nodes (`@1`, `@2`) and active `screen_diagnosis` (Cloudflare, Login, Loading, Interactive). |
| `page_forms` | Returns detected forms, inputs, types, placeholders, and current values. |
| `page_text` | Extracts clean, human-readable text summary of the page. |

### 4. Full-Spectrum Network Telemetry
| Tool | Description |
|---|---|
| `network_stream` | Consumes real-time event stream from the per-session ring buffer. |
| `network_list` | Lists captured HTTP transactions with method, URL, status, and latency. |
| `network_get` | Retrieves full redacted transaction details (headers, payload, response, timing breakdown). |
| `network_summary` | Returns endpoint latency percentiles (P50, P95), error distributions, and duplicate call flags. |
| `network_clear` | Clears captured transactions and resets stream cursor. |

### 5. Console & Real-time Streams
| Tool | Description |
|---|---|
| `console_list` | Lists captured console logs, warnings, errors, and uncaught page exceptions. |
| `websocket_list` | Lists active WebSocket connections, handshake status, and frame metrics. |
| `sse_list` | Lists active Server-Sent Events (SSE) streams and captured event payloads. |

### 6. QA Intelligence & Reporting
| Tool | Description |
|---|---|
| `qa_anomalies` | Scans for HTTP 5xx, CORS failures, tail latency spikes (>3s), and JS errors. |
| `qa_correlate` | Returns `FlowEvent` linking specific user action to triggered network calls and errors. |
| `qa_report` | Compiles an evidence-backed QA audit report with reproduction steps and performance stats. |

---

## 🧪 Verification & Testing

SpectraBrowser comes with a comprehensive offline test suite:
```bash
python tests/test_redaction.py   # Secret masking unit tests
python tests/test_schema.py      # Normalization & schema drift tests
python tests/test_smoke.py       # End-to-end integration test
python tests/test_bridge.py      # OpenAPI bridge test
```

---

## 📄 License
MIT License © 2026 VirajVerse (https://github.com/virajverse)
