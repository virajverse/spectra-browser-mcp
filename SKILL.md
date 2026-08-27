---
name: spectra-browser
description: >-
  World-Class Autonomous AI Playbook & Cognitive Reasoning Framework for SpectraBrowser MCP Suite.
  Zero-hardcoding dynamic browser control, semantic DOM observation, full CDP network lifecycle instrumentation,
  Chrome DevTools Network mirroring, high-resolution original image extraction, secret redaction, console correlation,
  endpoint fingerprinting, schema drift detection, screen diagnosis, smart waiting, and evidence-backed QA audit reporting.
---

# 🌐 SpectraBrowser MCP: Autonomous Cognitive Agent Playbook (37 Tools)

This skill provides **rigorous, code-verified operational instructions** for any AI agent (**Open WebUI, Antigravity, Claude 3.7, GPT-4o, DeepSeek-R1/V3, Qwen**) to autonomously explore, interact with, extract media from, debug, and audit web applications using the **SpectraBrowser MCP Suite** (`spectra-browser-mcp`).

Every capability is built upon dynamic accessibility tree observation, live Chrome Extension control, and full Chrome DevTools network telemetry—**no hardcoded selectors, no brittle XPath, and no rigid test scripts**.

---

## 🌟 Core Operating Principles (Zero-Hardcoding Manifesto)

1. **Zero Hardcoding**:
   * ❌ **NEVER** guess or hardcode CSS selectors (`#submit-btn`, `.login-form-input`).
   * ✅ **ALWAYS** call `page_inspect()` first to receive semantic, accessibility-tagged interactive nodes (`@1`, `@2`, `@3`) with their active `observation_id`.
2. **Stale Reference Protection**:
   * Every DOM mutation invalidates previous elements. Interaction tools (`browser_click`, `browser_type`, `browser_select`) require the active `observation_id`. If the DOM changes, re-inspect immediately.
3. **Full-Resolution Original Image Extraction**:
   * ❌ **NEVER** use viewport screenshots when full-resolution original media is needed.
   * ✅ Call `browser_extract_images()` to download raw blobs directly from CDN/DOM in original resolution (PNG/WebP).
   * 🔗 **Taliyo Integration:** Pass the returned `file_path` directly to `taliyo-blog-engine` (`upload_blog_image` or `create_blog_post`) to auto-upload to Supabase Storage and publish live!
4. **Deterministic Human Auth Handoff (No Credential Scraping)**:
   * ❌ **NEVER** ask users for raw passwords or attempt to bypass Google SSO, 2FA, or CAPTCHA.
   * ✅ Call `session_create(browser_mode="headed")` and `session_pause(reason="User login required")`. Wait for the human to log in visibly in the browser window, then resume via `session_resume()`.
5. **Interactive Human-in-the-Loop Protocol ("Pooch-Pooch Kar Karo")**:
   * Before taking critical, ambiguous, or irreversible actions, call `session_ask_human(question="...", options=[...])`.
   * Explain the current page state clearly to the human and await their decision before proceeding.
6. **Automatic Secret Redaction**:
   * Telemetry automatically scrubs passwords, Bearer tokens, cookies, and sensitive keys across headers, URLs, payloads, and typed inputs.

---

## 📊 Chrome DevTools Network Tab Mirroring Engine

SpectraBrowser provides a **1:1 exact mirror of Chrome DevTools Network Tab**:

```
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ Name          │ Status │ Type      │ Initiator          │ Size       │ Time            │
 ├───────────────┼────────┼───────────┼────────────────────┼────────────┼─────────────────┤
 │ openapi.json  │ 200    │ fetch     │ +layout.svelte:995 │ 35.1 kB    │ 42 ms           │
 │ logo.webp     │ 200    │ image     │ img                │ (disk cache│ 0 ms            │
 │ auth/login    │ 401    │ xhr       │ auth.js:142        │ 1.2 kB     │ 180 ms          │
 └───────────────┴────────┴───────────┴────────────────────┴────────────┴─────────────────┘
 Bottom Summary: 204 requests | 138 kB transferred | 7.5 MB resources | Finish: 4.94 s
```

### 1. `network_list` (Live DevTools Table)
* **Parameters:** `limit`, `filter_type` (`"Fetch/XHR"`, `"Doc"`, `"CSS"`, `"JS"`, `"Font"`, `"Img"`, `"Media"`), `errors_only=True` (for red 4xx/5xx failures), `search_query="login"`.
* **Output:** Returns clean table fields: `name`, `status`, `type`, `initiator`, `size`, `time`, `is_cached`, `is_failed`.

### 2. `network_get` (The 5 DevTools Sub-Tabs)
* **Headers Tab:** Status code with status text, Request URL, Request method, Request & Response headers.
* **Preview Tab:** Formatted parsed JSON or body preview.
* **Response Tab:** Complete raw response payload.
* **Initiator Tab:** Script call stack and trigger mechanism (`Preflight`, `parser`, `script`).
* **Timing Tab:** Exact waterfall breakdown: `queued_ms`, `stalled_ms`, `dns_ms`, `connect_ms`, `tls_ms`, `request_ms`, `ttfb_ms`, `download_ms`, `total_ms`.

### 3. `network_summary` (DevTools Bottom Summary Bar)
* Returns exact string: `204 requests | 138 kB transferred | 7.5 MB resources | Finish: 4.94 s`.

---

## 🧠 Cognitive Self-Healing & Cloudflare Bypass Protocol

Real web interfaces are non-linear and dynamic. An autonomous AI agent must NEVER assume a single-shot execution or fail silently on intermediate screens.

### 1. Screen Diagnosis (`screen_diagnosis`)
Every call to `page_inspect()` returns a semantic `screen_diagnosis` object:
* **`"cloudflare"` (`is_blocked: true`)**: Cloudflare Turnstile or *"Just a moment..."* challenge active.
  * **Autonomous Strategy:**
    1. If in `headed` mode, call `browser_wait(4000)` to allow automatic verification.
    2. If not cleared after 5s, call `session_ask_human(question="Cloudflare verification screen samne hai. Kripya browser window me checkbox tick kar dijiye.", options=["Tick kar diya", "Ruk jao"])`.
    3. Call `session_resume()` once verified.
* **`"login"`**: Login or Auth gate detected.
  * **Autonomous Strategy:** Call `session_ask_human(question="Login screen detect hui hai. Kya aap pehle login karna chahte hain?", options=["Pehle login karo", "Direct aage badho"])`.
* **`"loading"`**: SPA hydration or skeleton loading in progress.
  * **Autonomous Strategy:** Call `browser_wait_idle(timeout_ms=10000)` or `browser_wait(2000)` instead of clicking prematurely.
* **`"interactive"`**: Standard interactive state with valid `@ref` tags. Proceed with intended action.

---

## 🛠️ Complete Tool Specification (All 37 Tools)

### Group 0: Chrome Extension Bridge & Live Visible Control
* **`extension_status()`**: Checks whether the SpectraBrowser Chrome Extension is connected via WebSocket (`ws://127.0.0.1:8765/extension_ws`).
* **`browser_extract_images(save_dir=None)`**: Extracts all full-resolution images from the active tab in original quality (not screenshots). Returns `file_path`, `normalized_path`, and `markdown_link` ready for Supabase hosting!

### Group 1: Session Lifecycle & Human-in-the-Loop
* **`session_create(...)`**: Initializes browser context (`managed` or `registered`, `headed` or `headless`).
* **`session_status()`**: Returns current session state.
* **`session_ask_human(question, options)`**: Interactive protocol to ask human user before critical actions.
* **`session_pause(reason)`** & **`session_resume()`**: Safe human authentication handoff.
* **`session_save(profile_id)`** & **`session_restore(profile_id)`**: Persist cookies/auth tokens.
* **`session_close()`**: Clean shutdown.

### Group 2: Live Navigation & Inspection
* **`browser_navigate(url)`**: Navigates to target URL with auto-wait for domcontentloaded.
* **`page_inspect()`**: Returns semantic accessibility tree with `@1`, `@2` interactive tags, URL, title, and `screen_diagnosis`.
* **`browser_screenshot(full_page=False)`**: Visual inspection artifact.

### Group 3: Semantic Node Interaction
* **`browser_click(element_id, observation_id)`**: Clicks tagged element with auto-scroll and stale-check.
* **`browser_type(element_id, text, clear=True, press_enter=False)`**: Types text into input field with secret redaction.
* **`browser_select(element_id, value)`**: Selects dropdown option.
* **`browser_hover(element_id)`**: Triggers hover states and dropdowns.
* **`browser_scroll(direction="down", amount=500)`**: Smooth page scrolling.
* **`browser_press_key(key="Enter")`**: Simulates keyboard key presses.

### Group 4: Dynamic Waiting & Synchronization
* **`browser_wait(ms)`**: Static sleep.
* **`browser_wait_for(target, state="visible", timeout_ms=15000)`**: Waits for element condition.
* **`browser_wait_idle(timeout_ms=10000)`**: Waits for network requests to settle and DOM to calm.

### Group 5: Chrome DevTools Network & Console Telemetry
* **`network_list(limit, filter_type, errors_only, search_query)`**: DevTools table mirroring.
* **`network_get(request_id)`**: Full 5 DevTools sub-tabs (Headers, Preview, Response, Initiator, Timing).
* **`network_summary()`**: DevTools bottom summary string.
* **`network_clear()`**: Resets session network storage.
* **`console_list(min_level="info", limit=50)`**: Captured console logs, warnings, and uncaught exceptions.
* **`websocket_list()`** & **`sse_list()`**: Real-time message streaming telemetry.

### Group 6: Automated QA & Forensic Auditing
* **`qa_anomalies()`**: Scans session telemetry for 4xx/5xx errors, console crashes, latency spikes, and schema drift.
* **`qa_correlate(action_id)`**: Correlates user actions with subsequent network transactions and console events.
* **`qa_report(format_type="markdown")`**: Generates full evidence-backed QA audit report with executive summary and reproduction steps.

### Group 7: System Storage Audit & Deep Cache Purge
* **`check_mcp_storage()`**:
  * Scans and itemizes what files, screenshots, extracted images, and compiler caches are consuming disk space on the laptop.
  * Answers: *"Kis-kis cheez ne kitna storage ghera hua hai"* (Breakdown across screenshots, pycache, scraper dumps, and state files).
* **`clean_mcp_storage(dry_run=False)`**:
  * Safely deletes temporary screenshots, extracted raw images, and compiler bytecode to recover laptop disk space.
  * Only runs on explicit user request; never deletes source code, configs, .env, or API keys!
