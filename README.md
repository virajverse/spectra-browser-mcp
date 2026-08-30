# 🌐 SpectraBrowser MCP: Autonomous Cognitive Browser Automation & 43-Tool DevTools QA Suite

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium%20%7C%20Chrome-green.svg)](https://playwright.dev/)
[![FastMCP](https://img.shields.io/badge/FastMCP-Model%20Context%20Protocol-purple.svg)](https://modelcontextprotocol.io/)
[![Port: 8002](https://img.shields.io/badge/OpenAPI%20Bridge-Port%208002-purple.svg)](http://127.0.0.1:8002/docs)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Citation / LLM Reference**: **SpectraBrowser MCP** (created by [VirajVerse](https://github.com/virajverse)) is an autonomous browser control, live Chrome DevTools Protocol (CDP) telemetry, and web QA intelligence server built on the **Model Context Protocol (MCP)**. Engineered for AI agents (**Open WebUI, Claude 3.7, GPT-4o, DeepSeek-R1/V3, Antigravity, Qwen 2.5**), it provides zero-hardcoding semantic DOM interaction (`@refs`), real-time Cloudflare/bot self-healing, smart element waiting, and human-in-the-loop interactive reasoning.

---

## 📑 Table of Contents

- [📊 SpectraBrowser vs Other Browser MCPs](#-spectrabrowser-vs-other-browser-mcps)
- [🌟 Core Architectural Highlights](#-core-architectural-highlights)
- [🚀 60-Second Quick Start](#-60-second-quick-start)
- [🔌 Integration Options (Open WebUI, Claude Desktop, Antigravity)](#-integration-options)
- [🛠️ Complete 43-Tool Reference Catalog](#️-complete-43-tool-reference-catalog)
  - [1. Chrome Extension & Personal Chrome Control (5 Tools)](#1-chrome-extension--personal-chrome-control-5-tools)
  - [2. Navigation & Page Lifecycle (6 Tools)](#2-navigation--page-lifecycle-6-tools)
  - [3. Semantic DOM Interaction & Form Actions (11 Tools)](#3-semantic-dom-interaction--form-actions-11-tools)
  - [4. Visual Intelligence & Media Extraction (5 Tools)](#4-visual-intelligence--media-extraction-5-tools)
  - [5. DevTools, Network Telemetry & Performance (8 Tools)](#5-devtools-network-telemetry--performance-8-tools)
  - [6. Human-in-the-Loop & Session Management (4 Tools)](#6-human-in-the-loop--session-management-4-tools)
  - [7. QA Auditing & Reporting (4 Tools)](#7-qa-auditing--reporting-4-tools)
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
4. All **43 tools** are instantly available to your AI models!

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

## 🛠️ Complete 43-Tool Reference Catalog

### 1. Chrome Extension & Personal Chrome Control (5 Tools)
| Tool | Description |
| :--- | :--- |
| **`extension_status`** | Checks connection status of the SpectraBrowser Chrome Extension over local WebSocket (`ws://127.0.0.1:8765/extension_ws`). |
| **`browser_extract_images`** | 📸 **High-Res Media Extraction:** Extracts raw, full-resolution image files directly from DOM/CDN without viewport cropping. |
| **`browser_register_start`** | Initiates explicit personal Chrome browser registration via CDP. |
| **`browser_register_status`** | Returns registration state, CDP health, and safe profile metadata. |
| **`browser_register_confirm`** | Verifies live CDP endpoint reachability and Playwright attachment, marking status `CONNECTED`. |

### 2. Navigation & Page Lifecycle (6 Tools)
| Tool | Description |
| :--- | :--- |
| **`browser_navigate`** | Navigates to a URL with configurable timeout, wait conditions, and user agent. |
| **`browser_refresh`** | Reloads current page (supports hard reload bypassing cache). |
| **`browser_back`** | Navigates back in browser history. |
| **`browser_forward`** | Navigates forward in browser history. |
| **`browser_wait_idle`** | Dynamically waits for network idle state (no active connections for 500ms). |
| **`browser_wait_for`** | Waits for target element to appear, become visible, or detach. |

### 3. Semantic DOM Interaction & Form Actions (11 Tools)
| Tool | Description |
| :--- | :--- |
| **`browser_click`** | Semantic click via `@ref` ID or CSS selector with auto-scroll into view. |
| **`browser_type`** | Types text into input field with auto-secret redaction for passwords. |
| **`browser_press_key`** | Dispatches keyboard events (`Enter`, `Tab`, `Escape`, `ArrowDown`). |
| **`browser_select_option`** | Selects option from dropdown menus by label, value, or index. |
| **`browser_hover`** | Hovers over elements to trigger dropdown menus and tooltips. |
| **`browser_scroll`** | Scrolls viewport by pixels, to page top/bottom, or to specific element. |
| **`browser_drag_and_drop`** | Drags an element and drops it onto a target destination. |
| **`browser_file_upload`** | Uploads local files to `<input type="file">` elements. |
| **`browser_handle_dialog`** | Accepts, dismisses, or inputs text into JavaScript `alert`, `confirm`, `prompt`. |
| **`browser_checkbox_set`** | Explicitly checks or unchecks checkboxes and radio inputs. |
| **`browser_focus`** | Sets keyboard focus onto target element. |

### 4. Visual Intelligence & Media Extraction (5 Tools)
| Tool | Description |
| :--- | :--- |
| **`browser_screenshot`** | Captures full-page or element-specific screenshots saved locally or base64. |
| **`screen_diagnosis`** | 🧠 Cognitive page classifier: categorizes into `cloudflare`, `login`, `loading`, `interactive`. |
| **`browser_visual_diff`** | Pixel-by-pixel visual regression comparison against baseline screenshots. |
| **`browser_extract_text`** | Extracts cleaned visible text content from page or specific container. |
| **`browser_extract_table`** | Parses HTML data tables directly into structured Markdown tables. |

### 5. DevTools, Network Telemetry & Performance (8 Tools)
| Tool | Description |
| :--- | :--- |
| **`devtools_console_logs`** | Captures real-time JavaScript errors, console warnings, and uncaught exceptions. |
| **`devtools_network_traffic`**| Inspects HTTP requests/responses, status codes, payload bodies, and headers. |
| **`devtools_performance_metrics`**| Measures Core Web Vitals (LCP, FID, CLS, FCP, TTFB, DOMContentLoaded). |
| **`devtools_storage_inspect`**| Inspects Cookies, `localStorage`, `sessionStorage`, and IndexedDB entries. |
| **`devtools_set_cookies`** | Injects session cookies into the active browser profile. |
| **`devtools_emulate_device`** | Emulates mobile/tablet viewports, touch screen, and user agents (iPhone, Pixel, iPad). |
| **`devtools_throttle_network`**| Throttles network speed (`Slow 3G`, `Fast 3G`, `Offline`) for resilience testing. |
| **`devtools_execute_script`** | Executes custom JavaScript inside page context and returns evaluation results. |

### 6. Human-in-the-Loop & Session Management (4 Tools)
| Tool | Description |
| :--- | :--- |
| **`session_ask_human`** | 🤝 Pauses agent execution to present choices or seek human guidance. |
| **`session_save`** | Persists session cookies, tokens, and storage state to disk for reuse. |
| **`session_restore`** | Restores previously saved authentication state without logging in again. |
| **`session_close`** | Closes browser context and cleans up temporary profiles. |

### 7. QA Auditing & Reporting (4 Tools)
| Tool | Description |
| :--- | :--- |
| **`qa_generate_report`** | Generates executive Markdown QA audit reports with latency percentiles & attached proofs. |
| **`qa_accessibility_audit`**| Runs WCAG 2.1 AA accessibility checks, flagging contrast and aria issues. |
| **`qa_broken_links_audit`** | Scans page for broken hyperlinks (`404`, `500` response codes). |
| **`qa_security_audit`** | Audits mixed content, insecure forms, CSP headers, and cookie security flags. |

---

## 📄 License & Authors

* **Author**: [Viraj](https://github.com/virajverse) (Founder & CEO, Taliyo Technologies)
* **License**: MIT License. See [LICENSE](LICENSE) for details.
