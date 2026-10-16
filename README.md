# 🌐 SpectraBrowser MCP: Autonomous Cognitive Browser Automation & 99-Tool DevTools QA Suite

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium%20%7C%20Chrome-green.svg)](https://playwright.dev/)
[![FastMCP](https://img.shields.io/badge/FastMCP-Model%20Context%20Protocol-purple.svg)](https://modelcontextprotocol.io/)
[![Port: 8002](https://img.shields.io/badge/OpenAPI%20Bridge-Port%208002-purple.svg)](http://127.0.0.1:8002/docs)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Citation / LLM Reference**: **SpectraBrowser MCP** (created by [VirajVerse](https://github.com/virajverse)) is an autonomous browser control, live Chrome DevTools Protocol (CDP) telemetry, and web QA intelligence server built on the **Model Context Protocol (MCP)**. Engineered for AI agents (**Open WebUI, Claude 3.7, GPT-4o, DeepSeek-R1/V3, Antigravity, Qwen 2.5**), it provides 100% Chrome Extension-native control, zero-hardcoding semantic DOM interaction (`@refs`), ultra-fast RapidOCR (ONNX), media platform optimization, real-time Cloudflare/bot self-healing, smart dynamic waiting, resilient self-healing clicks, and human-in-the-loop interactive reasoning across **99 production tools**.

---

## 📑 Table of Contents

- [📊 SpectraBrowser vs Other Browser MCPs](#-spectrabrowser-vs-other-browser-mcps)
- [🧬 Dynamic Cognitive Reasoning & Combinatorial Pattern Engine](#-dynamic-cognitive-reasoning--combinatorial-pattern-engine)
- [🌟 Core Architectural Highlights](#-core-architectural-highlights)
- [🚀 60-Second Quick Start](#-60-second-quick-start)
- [🔌 Integration Options (Open WebUI, Claude Desktop, Antigravity)](#-integration-options)
- [🛠️ Complete 99-Tool Reference Catalog (15 Groups)](#️-complete-99-tool-reference-catalog-15-groups)
  - [Group 0: Chrome Extension Bridge & Profile Registration (8 Tools)](#group-0-chrome-extension-bridge--profile-registration-8-tools)
  - [Group 1: Session Lifecycle & Human-in-the-Loop (7 Tools)](#group-1-session-lifecycle--human-in-the-loop-7-tools)
  - [Group 2: Live Navigation & Semantic Interaction (7 Tools)](#group-2-live-navigation--semantic-interaction-7-tools)
  - [Group 3: Media Extraction, Wait & Vision Inspection (6 Tools)](#group-3-media-extraction-wait--vision-inspection-6-tools)
  - [Group 4: Page Inspection & Semantic DOM (3 Tools)](#group-4-page-inspection--semantic-dom-3-tools)
  - [Group 5: DevTools Telemetry & Network Forensics (8 Tools)](#group-5-devtools-telemetry--network-forensics-8-tools)
  - [Group 6: Automated QA & Forensic Auditing (3 Tools)](#group-6-automated-qa--forensic-auditing-3-tools)
  - [Group 7: System Storage Audit & Disk Purge (2 Tools)](#group-7-system-storage-audit--disk-purge-2-tools)
  - [Group 8: Media Optimization & Smart Canvas Engine (2 Tools)](#group-8-media-optimization--smart-canvas-engine-2-tools)
  - [Group 9: Session Memory, Action Timeline & Failed Targets (9 Tools)](#group-9-session-memory-action-timeline--failed-targets-9-tools)
  - [Group 10: Multi-Tab & Named Tab Handles (4 Tools)](#group-10-multi-tab--named-tab-handles-4-tools)
  - [Group 11: Macros & Test Recording Engine (12 Tools)](#group-11-macros--test-recording-engine-12-tools)
  - [Group 12: Auth, Health & Resilient Self-Healing Interaction (7 Tools)](#group-12-auth-health--resilient-self-healing-interaction-7-tools)
  - [Group 13: Advanced Vision, Layout Geometry & Spatial Semantics (9 Tools)](#group-13-advanced-vision-layout-geometry--spatial-semantics-9-tools)
  - [Group 14: Script Library, Site Adapters & Infinite Harvesting (9 Tools)](#group-14-script-library-site-adapters--infinite-harvesting-9-tools)
  - [Group 15: Unified Vision Modes & Cognitive Page Seeing (3 Tools)](#group-15-unified-vision-modes--cognitive-page-seeing-3-tools)
- [📄 License & Authors](#-license--authors)

---

## 📊 SpectraBrowser vs Other Browser MCPs

| Capability | SpectraBrowser MCP 🚀 | Standard Browser Tools / Puppeteer MCP ⚠️ |
| :--- | :--- | :--- |
| **Tool Count** | **99 Verified Tools** covering DOM, CDP, Memory, Macros, Vision | 10–15 basic tools |
| **DOM Interaction** | **Zero Hardcoding**: Semantic Accessibility `@ref` tags + Coordinates | Fragile CSS selectors (`#btn-1`) & brittle XPaths |
| **Self-Healing Clicks** | **`browser_click_retry`, `browser_click_fallback`, `element_fingerprint`** | Fails immediately on element re-render |
| **Human-in-the-Loop** | **Native `session_ask_human`**: Pauses & asks user for decisions | None (Runs blindly until failure) |
| **Element & Page Waiting**| **Smart Dynamic Wait**: `browser_wait_for` & `browser_wait_idle` | Brittle fixed sleep timers (`time.sleep`) |
| **DevTools Telemetry** | Full request/response, TTFB, P50/P95 latency percentiles, WebSocket, SSE | None or basic HTTP status code only |
| **Test & Macro Engine** | **Built-in Replay Recorder**: Record actions & export replayable JSON | Requires external test framework setup |
| **Memory & Timelines** | `session_memory_set/get`, `action_timeline`, `failed_targets_list` | Stateless; forgets prior steps on re-render |
| **OCR & Vision** | Ultra-fast RapidOCR (ONNX) + `page_understand` zone classification | Heavy PyTorch or Cloud VLM API calls |
| **Open WebUI Support** | Native 1-click FastAPI OpenAPI bridge on Port **`8002`** | Complex manual configuration required |

---

## 🧬 Dynamic Cognitive Reasoning & Combinatorial Pattern Engine

SpectraBrowser is engineered so AI models do not rely on hardcoded automation scripts. The **99 tools** represent orthogonal primitives that can be composed into **infinite emergent patterns** via 4 Fundamental Seed Archetypes:

```
                    ┌────────────────────────────────────────────────────────┐
                    │          THE 4 CORE PRIMITIVE SEED ARCHETYPES          │
                    └───────────────────────────┬────────────────────────────┘
                                                │
         ┌──────────────────────┬───────────────┴───────────────┬──────────────────────┐
         ▼                      ▼                               ▼                      ▼
┌──────────────────┐ ┌───────────────────────────┐ ┌──────────────────┐ ┌────────────────────────┐
│  [Archetype 1]   │ │       [Archetype 2]       │ │  [Archetype 3]   │ │     [Archetype 4]      │
│Sensory Observation│ │   Dynamic Sync, Waits &   │ │   Human-Cadence  │ │    State Memory,       │
│& Layout Geometry │ │    Telemetry Radar (CDP)  │ │ Action & Recovery│ │  Macros & Forensics    │
│  (The Eyes)      │ │        (The Senses)       │ │   (The Hands)    │ │   (The Brain & Log)    │
└──────────────────┘ └───────────────────────────┘ └──────────────────┘ └────────────────────────┘
```

From these 4 seeds, agents dynamically synthesize emergent workflows on the fly:
* **Zero-Failure Mutation Pattern ($1 \rightarrow 3 \rightarrow 2 \rightarrow 3_{\text{retry}} \rightarrow 4$)**: Inspect accessibility tree ➔ type/click with human physics ➔ dynamic wait for network settle ➔ self-heal via fingerprint relocation if DOM shifted.
* **Infinite Feeds Harvester ($1 \rightarrow 3_{\text{scroll}} \rightarrow 1_{\text{table}} \rightarrow 4_{\text{mem}}$)**: Classify layout zones ➔ perform sinusoidal scroll harvesting ➔ extract structured JSON table data ➔ persist into session memory.
* **Flaky Interaction Test Case Generator ($4 \rightarrow 1 \rightarrow 3 \rightarrow 2 \rightarrow 4$)**: Start test recorder ➔ interact with targets ➔ intercept network 4xx/5xx anomalies ➔ export replayable JSON test case with full CDP timings.
* **Human-in-the-Loop Safe Mutation ($1 \rightarrow 4_{\text{ask}} \rightarrow 3 \rightarrow 4_{\text{report}}$)**: Flag destructive keywords (`delete`, `pay`) ➔ pause and prompt human with choices ➔ resume on approval and generate forensic audit trail.

---

## 🌟 Core Architectural Highlights

* 🧠 **Cognitive Screen Diagnosis & Zones (`page_understand`)**: Classifies layout into `header`, `nav`, `sidebar`, `main`, `footer`, `modal` from geometry.
* 🤝 **Human-in-the-Loop ("Pooch Kar Karo")**: Dedicated `session_ask_human()` pauses execution, presents choices to the human user, and logs the decision.
* ⏳ **Smart Dynamic Waiting**: `browser_wait_for()` and `browser_wait_idle()` dynamically wait for target elements and network settling.
* 🎯 **Zero Hardcoding (`@ref` Priority)**: Inspects accessibility trees to assign stable references (`@1`, `@2`, `@3`) with 0 disk bytes used.
* 🛡️ **Self-Healing Actions**: `browser_click_retry`, `browser_click_fallback`, and `element_fingerprint` / `relocate_element` survive page re-renders.
* ⚡ **DevTools Telemetry & Forensics**: Intercepts complete CDP transactions (Request -> TTFB -> Response -> Bodies) with structure-preserving secret redaction.
* 📊 **Evidence-Backed QA Reports**: One-click generation of executive markdown QA audit reports with latency percentiles (P50, P95).

---

## 🚀 60-Second Quick Start

### Windows (1-Click Automated Setup)
1. **Run `install.bat`** (Creates `.venv`, installs dependencies, and downloads Playwright Chromium).
2. **Run `run_bridge.bat`** (Starts the OpenAPI Bridge on port **`8002`**).

### Linux / macOS
```bash
# 1. Clone repository & run setup
git clone https://github.com/virajverse/spectra-browser-mcp.git
cd spectra-browser-mcp
chmod +x install.sh
./install.sh

# 2. Start the bridge
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
4. All **99 tools** are instantly available to your AI models!

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

## 🛠️ Complete 99-Tool Reference Catalog (15 Groups)

### Group 0: Chrome Extension Bridge & Profile Registration (8 Tools)
| Tool | Description |
| :--- | :--- |
| **`extension_status`** | Checks connection status of the Spectra Chrome Extension over local WebSocket (`ws://127.0.0.1:8765/extension_ws`). |
| **`browser_register_start`** | Auto-discovers Chrome user profiles, launches designated debugging port, and attaches CDP session. |
| **`browser_register_status`** | Returns profile registration health, connection metrics, and metadata. |
| **`browser_register_confirm`** | Confirms browser registration after user authorization and establishes active link. |
| **`browser_register_revoke`** | Revokes browser registration, detaches debugging, and frees resources. |
| **`browser_register_list`** | Enumerates all registered browser profiles available for automation. |
| **`browser_tabs`** | Lists all open tabs in user's Chrome with tab ID, title, and current URL. |
| **`browser_select_tab`** | Switches focus to designated tab ID (string) and attaches DevTools debugger. |

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

### Group 2: Live Navigation & Semantic Interaction (7 Tools)
| Tool | Description |
| :--- | :--- |
| **`browser_navigate`** | Navigates active tab to target URL with configurable wait conditions. |
| **`browser_reload`** | Reloads current page with DevTools Network and Console instrumentation enabled. |
| **`browser_click`** | Human-cadence click via `@ref` ID (`@5`) or pixel coordinates (`"500, 300"`) with micro-jitter physics. |
| **`browser_type`** | Types text with 15–45ms human keystroke delay and React/Vue state setter synchronization. |
| **`browser_select`** | Selects options from dropdown menus by visible label or option value. |
| **`browser_scroll`** | Sinusoidal smooth scrolling with multi-step micro-eased WheelEvents. |
| **`browser_press`** | Dispatches keyboard keypress (`Enter`, `Tab`, `Escape`, `ArrowDown`). |

### Group 3: Media Extraction, Wait & Vision Inspection (6 Tools)
| Tool | Description |
| :--- | :--- |
| **`browser_extract_images`** | Extracts raw, original full-resolution media directly from DOM/CDN without viewport crops. |
| **`browser_wait`** | Non-blocking sleep delay in milliseconds. |
| **`browser_wait_for`** | Polls dynamically until target element achieves desired state (`visible`, `hidden`, `detached`). |
| **`browser_wait_idle`** | Dynamically waits for network requests and DOM mutations to settle. |
| **`browser_screenshot`** | In-memory base64 screenshot inspection (0 disk bytes written by default). |
| **`browser_ocr`** | Ultra-fast RapidOCR (ONNX) engine to extract text, phone numbers, prices, and bounding boxes in <100ms. |

### Group 4: Page Inspection & Semantic DOM (3 Tools)
| Tool | Description |
| :--- | :--- |
| **`page_inspect`** | Returns semantic accessibility tree with stable `@1`, `@2` references (0 disk bytes). |
| **`page_forms`** | Detects interactive form inputs, placeholders, and current values. |
| **`page_text`** | Extracts cleaned visible text summary of the active viewport. |

### Group 5: DevTools Telemetry & Network Forensics (8 Tools)
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
| **`optimize_media_for_platform`** | Crops, canvas-fits, and compresses images down to <=200KB for `INSTAGRAM`, `STORY`, `EMAIL`, `BLOG`, or `THUMBNAIL`. |
| **`optimize_media_batch`** | Batch-optimizes extracted images or folder with slate letterbox backgrounds in a single call. |

### Group 9: Session Memory, Action Timeline & Failed Targets (9 Tools)
| Tool | Description |
| :--- | :--- |
| **`session_memory_set`** | Stores a key-value pair in session working memory (survives pause/resume). |
| **`session_memory_get`** | Retrieves a value from session working memory. |
| **`session_memory_delete`** | Deletes a key from session working memory. |
| **`session_memory_list`** | Lists all keys/values in session working memory. |
| **`session_memory_clear`** | Clears all session working memory. |
| **`action_timeline`** | Returns recent action history with outcomes, network effects, and console errors. |
| **`action_last`** | Returns the last recorded browser action with outcome. |
| **`failed_targets_list`** | Lists failed click/type targets to avoid retrying blindly. |
| **`failed_targets_clear`** | Clears failed-target memory. |

### Group 10: Multi-Tab & Named Tab Handles (4 Tools)
| Tool | Description |
| :--- | :--- |
| **`tab_create`** | Creates a named tab handle for multi-tab orchestration. |
| **`tab_switch`** | Switches active automation to a named tab handle. |
| **`tab_close`** | Closes/removes a named tab handle. |
| **`tab_list`** | Lists all named tab handles in this session. |

### Group 11: Macros & Test Recording Engine (12 Tools)
| Tool | Description |
| :--- | :--- |
| **`macro_start_recording`** | Starts recording a macro (browser actions captured as replayable steps). |
| **`macro_stop_recording`** | Stops macro recording and returns captured steps. |
| **`macro_list`** | Lists all recorded macros. |
| **`macro_get`** | Returns macro steps for inspection. |
| **`macro_delete`** | Deletes a recorded macro. |
| **`macro_run`** | Replays a recorded macro step-by-step in the given session. |
| **`test_start_recording`** | Starts recording an exportable test case. |
| **`test_stop_recording`** | Stops test recording, capturing steps + network + console evidence. |
| **`test_list`** | Lists all recorded test cases. |
| **`test_get`** | Returns full test case with steps and evidence. |
| **`test_delete`** | Deletes a test case. |
| **`test_export`** | Exports a test case as replayable JSON with reproduction steps. |

### Group 12: Auth, Health & Resilient Self-Healing Interaction (7 Tools)
| Tool | Description |
| :--- | :--- |
| **`auth_status`** | Detects login state (`logged_in: True/False/unknown`) via page signals. |
| **`session_health_check`** | Checks session/extension health and recommends next action. |
| **`browser_click_retry`** | Clicks with auto-retry + exponential backoff on failure. |
| **`browser_click_fallback`** | Tries multiple targets in order until one succeeds (e.g. `['@3', 'text:Login']`). |
| **`element_fingerprint`** | Builds a stable visual+structural fingerprint for an element (survives `@ref` reassignment). |
| **`relocate_element`** | Re-finds an element after re-render using a stored fingerprint object. |
| **`find_element`** | Finds elements by semantic text description (e.g. `'login button'`). |

### Group 13: Advanced Vision, Layout Geometry & Spatial Semantics (9 Tools)
| Tool | Description |
| :--- | :--- |
| **`visual_compare`** | Compares two screenshots -> similarity % + changed regions bounding box. |
| **`screenshot_annotate`** | Draws bounding boxes and labels on a screenshot. |
| **`page_vitals`** | Collects page performance signals (TTFB, FCP, DCL, load, resource transfer) via CDP. |
| **`page_a11y_audit`** | Lightweight WCAG heuristic audit (alt, button names, labels, h1) -> score 0-100. |
| **`extract_table`** | Extracts HTML tables into structured `{headers, rows, records}` JSON. |
| **`page_understand`** | Classifies page into layout zones (`header`, `nav`, `sidebar`, `main`, `footer`, `modal`) from geometry. |
| **`find_element_smart`** | Spatial-aware find: handles `'bottom-right'`, `'third row'`, `'inside pricing'` qualifiers. |
| **`text_with_positions`** | OCR-free layout fusion: visible text nodes WITH bounding boxes via CDP. |
| **`extract_by_description`** | Extracts named fields by description (no CSS): `{'price': 'price in product card'}`. |

### Group 14: Script Library, Site Adapters & Infinite Harvesting (9 Tools)
| Tool | Description |
| :--- | :--- |
| **`script_library_add`** | Stores a reusable JS snippet for later replay. |
| **`script_library_list`** | Lists stored JS snippets. |
| **`script_library_get`** | Returns a stored JS snippet. |
| **`script_library_delete`** | Deletes a stored JS snippet. |
| **`script_library_run`** | Runs a stored JS snippet in the live tab via CDP. |
| **`adapter_save`** | Saves site-specific selector aliases, e.g. `github.com: {'search box': 'input[name=q]'}`. |
| **`adapter_list`** | Lists all site adapters. |
| **`adapter_resolve`** | Resolves friendly name to selector for a site. |
| **`browser_scroll_harvest`** | Scrolls until N items loaded (infinite scroll), then counts matches. |

### Group 15: Unified Vision Modes & Cognitive Page Seeing (3 Tools)
| Tool | Description |
| :--- | :--- |
| **`vision_set_mode`** | Sets visual response mode: `'auto'`, `'visual'` (VLM models), `'text'` (non-VLM token-saving). |
| **`vision_get_mode`** | Returns current visual response mode. |
| **`page_see`** | Unified 'see' combining text positions, layout zones, and optional screenshot. |

---

## 📄 License & Authors

* **Author**: [Viraj](https://github.com/virajverse) (Founder & CEO, Taliyo Technologies)
* **License**: MIT License. See [LICENSE](LICENSE) for details.
