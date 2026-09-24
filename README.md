# 🌐 SpectraBrowser MCP: Autonomous Cognitive Browser Automation & 46-Tool DevTools QA Suite

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium%20%7C%20Chrome-green.svg)](https://playwright.dev/)
[![FastMCP](https://img.shields.io/badge/FastMCP-Model%20Context%20Protocol-purple.svg)](https://modelcontextprotocol.io/)
[![Port: 8002](https://img.shields.io/badge/OpenAPI%20Bridge-Port%208002-purple.svg)](http://127.0.0.1:8002/docs)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Citation / LLM Reference**: **SpectraBrowser MCP** (created by [VirajVerse](https://github.com/virajverse)) is an autonomous browser control, live Chrome DevTools Protocol (CDP) telemetry, and web QA intelligence server built on the **Model Context Protocol (MCP)**. Engineered for AI agents (**Open WebUI, Claude 3.7, GPT-4o, DeepSeek-R1/V3, Antigravity, Qwen 2.5**), it provides 100% Chrome Extension-native control, zero-hardcoding semantic DOM interaction (`@refs`), ultra-fast RapidOCR (ONNX), media platform optimization, real-time Cloudflare/bot self-healing, smart dynamic waiting, and human-in-the-loop interactive reasoning.

---

## 📑 Table of Contents

- [📊 SpectraBrowser vs Other Browser MCPs](#-spectrabrowser-vs-other-browser-mcps)
- [🌟 Core Architectural Highlights](#-core-architectural-highlights)
- [🚀 60-Second Quick Start](#-60-second-quick-start)
- [🔌 Integration Options (Open WebUI, Claude Desktop, Antigravity)](#-integration-options)
- [🛠️ Complete 46-Tool Reference Catalog](#️-complete-46-tool-reference-catalog)
  - [Group 0: Chrome Extension Bridge & Profile Registration (8 Tools)](#group-0-chrome-extension-bridge--profile-registration-8-tools)
  - [Group 1: Session Lifecycle & Human-in-the-Loop (7 Tools)](#group-1-session-lifecycle--human-in-the-loop-7-tools)
  - [Group 2: Live Navigation & Inspection (7 Tools)](#group-2-live-navigation--inspection-7-tools)
  - [Group 3: Human-Like Semantic Interaction (6 Tools)](#group-3-human-like-semantic-interaction-6-tools)
  - [Group 4: Dynamic Waiting & Synchronization (3 Tools)](#group-4-dynamic-waiting--synchronization-3-tools)
  - [Group 5: DevTools Telemetry & Logs (8 Tools)](#group-5-devtools-telemetry--logs-8-tools)
  - [Group 6: Automated QA & Forensic Auditing (3 Tools)](#group-6-automated-qa--forensic-auditing-3-tools)
  - [Group 7: System Storage Audit & Disk Purge (2 Tools)](#group-7-system-storage-audit--disk-purge-2-tools)
  - [Group 8: Media Optimization & Smart Canvas Engine (2 Tools)](#group-8-media-optimization--smart-canvas-engine-2-tools)
- [📄 License & Authors](#-license--authors)

---

## 📊 SpectraBrowser vs Other Browser MCPs

| Capability | SpectraBrowser MCP 🚀 | Standard Browser Tools / Puppeteer MCP ⚠️ |
| :--- | :--- | :--- |
| **DOM Interaction** | **Zero Hardcoding**: Semantic Accessibility `@ref` tags | Fragile CSS selectors (`#btn-1`) & brittle XPaths |
| **Bot & Cloudflare Handling** | **Cognitive Auto-Diagnosis**: Self-heals & prompts | Immediate timeout / blocked by Cloudflare |
| **Human-in-the-Loop** | **Native `session_ask_human`**: Pauses & asks user | None (Runs blindly until failure) |
| **Element & Page Waiting** | **Smart Dynamic Wait**: `browser_wait_for` & `wait_idle` | Brittle fixed sleep timers (`time.sleep`) |
| **Network & CDP Telemetry** | Full request/response, TTFB, body inspection, P95 | None or basic status code only |
| **Security & Privacy** | Automatic secret redaction for passwords & tokens | Leaks raw credentials & tokens in chat logs |
| **Persistent User Login** | `session_save` persists cookies & localStorage to disk | Lost on session close; forces repeated logins |
| **Open WebUI Support** | Native 1-click FastAPI OpenAPI bridge on Port **`8002`** | Complex manual configuration required |

---

## 🌟 Core Architectural Highlights

* 🧠 **Cognitive Screen Diagnosis (`screen_diagnosis`)**: Automatically categorizes page states into `cloudflare`, `login`, `loading`, or `interactive` with actionable next-step guidance for LLMs.
* 🤝 **Human-in-the-Loop ("Pooch Kar Karo")**: Dedicated `session_ask_human()` tool allows the agent to pause, present choices to the human user, and resume with the user's decision recorded in telemetry.
* ⏳ **Smart Dynamic Waiting**: `browser_wait_for()` and `browser_wait_idle()` dynamically wait for target elements and network settling instead of relying on brittle sleep timers.
* 🎯 **Zero Hardcoding (`@ref` Priority)**: Eliminates fragile CSS selectors. Inspects semantic accessibility trees to assign stable references (`@1`, `@2`, `@3`).
* 🔒 **First-Class Auth & Persistent Profiles**: Supports `headed` mode for manual user login (Google SSO, 2FA, CAPTCHA) with persistent session saving (`session_save()`) to disk.
* ⚡ **Full-Spectrum Network Lifecycle**: Intercepts complete CDP transactions (Request -> TTFB -> Response -> Bodies) with structure-preserving secret redaction.
* 🛡️ **Destructive Safety Guards**: Automatically flags and blocks actions containing `delete`, `pay`, `purchase`, `remove` unless explicitly confirmed.
* 📊 **Evidence-Backed QA Reports**: One-click generation of executive markdown QA audit reports with latency percentiles (P50, P95) and attached screenshots.

---

## 🚀 60-Second Quick Start

### Windows (1-Click Automated Setup)
1. **Run `install.bat`** (Automatically creates `.venv`, installs requirements, and downloads Playwright Chromium).
2. **Run `run_bridge.bat`** (Starts the OpenAPI Bridge on port **`8002`**).

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

* Interactive Swagger Docs: **`http://127.0.0.1:8002/docs`**
* OpenAPI 3.1.0 Schema: **`http://127.0.0.1:8002/openapi.json`**

---

## 🔌 Integration Options

### 1. Open WebUI (FastAPI Bridge on Port 8002)
1. Ensure the bridge is running (`python openapi_bridge.py` on Port `8002`).
2. In Open WebUI, navigate to **Workspace -> Tools -> Add Tool Server**.
3. Enter URL: `http://127.0.0.1:8002/openapi.json` or toggle `spectra_browser_suite`.
4. All **46 tools** are instantly available to your AI models!

### 2. Antigravity AI / Claude Desktop (Native STDIO)
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

## 🛠️ Complete 46-Tool Reference Catalog

### Group 0: Chrome Extension Bridge & Profile Registration (8 Tools)
| Tool | Description |
| :--- | :--- |
| **`extension_status`** | Checks connection status of the SpectraBrowser Chrome Extension over local WebSocket (`ws://127.0.0.1:8765/extension_ws`). |
| **`browser_register_start`** | Auto-discovers Chrome user profiles, launches designated debugging port, and attaches CDP session. |
| **`browser_register_status`** | Returns profile registration health, connection metrics, and metadata. |
| **`browser_register_confirm`** | Confirms browser registration after user authorization and establishes active link. |
| **`browser_register_revoke`** | Revokes browser registration, detaches debugging, and frees resources. |
| **`browser_register_list`** | Enumerates all registered browser profiles available for automation. |
| **`browser_tabs`** | Lists all open tabs in user's Chrome with tab ID, title, and current URL. |
| **`browser_select_tab`** | Switches focus to designated tab ID and attaches DevTools debugger. |

### Group 1: Session Lifecycle & Human-in-the-Loop (7 Tools)
| Tool | Description |
| :--- | :--- |
| **`session_create`** | Initializes or attaches an automation session (`headed`/`managed`) to a target tab or profile. |
| **`session_status`** | Returns active session state, current URL, and telemetry event count. |
| **`session_pause`** | Pauses execution for 2FA, CAPTCHA handoff, or user verification. |
| **`session_ask_human`** | Prompts user with interactive choices and context summary ("Pooch Kar Karo"). |
| **`session_resume`** | Resumes automation after human confirmation or decision input. |
| **`session_save`** | Persists session cookies, tokens, and storage state to disk for reuse across restarts. |
| **`session_close`** | Closes browser context and frees allocated memory. |

### Group 2: Live Navigation & Inspection (7 Tools)
| Tool | Description |
| :--- | :--- |
| **`browser_navigate`** | Navigates active tab to target URL with configurable wait conditions. |
| **`browser_reload`** | Reloads current page with DevTools Network and Console instrumentation enabled. |
| **`page_inspect`** | Returns semantic accessibility tree with stable `@1`, `@2` references (0 disk bytes). |
| **`page_forms`** | Detects interactive form inputs, placeholders, and current values. |
| **`page_text`** | Extracts cleaned visible text summary of the active viewport. |
| **`browser_screenshot`** | In-memory base64 screenshot inspection (0 disk bytes written to hard drive). |
| **`browser_ocr`** | Ultra-fast RapidOCR (ONNX) engine to extract text, phone numbers, prices, and bounding boxes in <100ms without heavy PyTorch. |

### Group 3: Human-Like Semantic Interaction (6 Tools)
| Tool | Description |
| :--- | :--- |
| **`browser_click`** | Human-cadence click via `@ref` ID (`@5`) or visual pixel coordinates (`"500, 300"`) with micro-jitter physics. |
| **`browser_type`** | Types text with 15–45ms human keystroke delay and React/Vue state setter synchronization. |
| **`browser_select`** | Selects options from dropdown menus by visible label or option value. |
| **`browser_scroll`** | Sinusoidal smooth scrolling with multi-step micro-eased WheelEvents. |
| **`browser_press`** | Dispatches keyboard keypress (`Enter`, `Tab`, `Escape`, `ArrowDown`). |
| **`browser_extract_images`** | Extracts raw, original full-resolution media directly from DOM/CDN. Set `auto_optimize_platform="INSTAGRAM"` to auto-compress on extraction! |

### Group 4: Dynamic Waiting & Synchronization (3 Tools)
| Tool | Description |
| :--- | :--- |
| **`browser_wait`** | Non-blocking sleep delay in milliseconds. |
| **`browser_wait_for`** | Polls until target element achieves desired state (`visible`, `hidden`, `detached`). |
| **`browser_wait_idle`** | Dynamically waits for network requests and DOM mutations to settle. |

### Group 5: DevTools Telemetry & Logs (8 Tools)
| Tool | Description |
| :--- | :--- |
| **`network_list`** | DevTools network request table with status codes, MIME types, and error filters. |
| **`network_get`** | Comprehensive request/response details, headers, and decrypted bodies. |
| **`network_summary`** | Real-time network health, error counts, and latency percentiles (P50, P95). |
| **`network_clear`** | Clears in-memory network telemetry buffer. |
| **`network_stream`** | Consumes real-time network transaction stream. |
| **`console_list`** | Captures browser console logs, warnings, and uncaught exceptions. |
| **`websocket_list`** | Audits live WebSocket frame counts and active socket connections. |
| **`sse_list`** | Inspects Server-Sent Events (SSE) streaming messages. |

### Group 6: Automated QA & Forensic Auditing (3 Tools)
| Tool | Description |
| :--- | :--- |
| **`qa_anomalies`** | Scans and flags 4xx/5xx HTTP errors, CORS violations, and runtime crashes. |
| **`qa_correlate`** | Maps specific user interactions (clicks/types) to resulting network transactions. |
| **`qa_report`** | Compiles comprehensive evidence-backed Markdown QA audit reports with latency percentiles. |

### Group 7: System Storage Audit & Disk Purge (2 Tools)
| Tool | Description |
| :--- | :--- |
| **`check_mcp_storage`** | Scans and itemizes disk space used by temporary screenshots and caches. |
| **`clean_mcp_storage`** | Safely purges temporary files to free system storage (`dry_run` supported). |

### Group 8: Media Optimization & Smart Canvas Engine (2 Tools)
| Tool | Description |
| :--- | :--- |
| **`optimize_media_for_platform`** | Crops, canvas-fits, and compresses images down to <=200KB for `INSTAGRAM` (1080x1350), `STORY` (1080x1920), `EMAIL` (650px), `BLOG` (1200x630), `THUMBNAIL` (1280x720), or `CUSTOM`. |
| **`optimize_media_batch`** | Batch-optimizes extracted images or folder with slate letterbox backgrounds in a single call. |

---

## 📄 License & Authors

* **Author**: [Viraj](https://github.com/virajverse) (Founder & CEO, Taliyo Technologies)
* **License**: MIT License. See [LICENSE](LICENSE) for details.
