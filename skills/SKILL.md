---
name: browser-qa-agent
description: >-
  World-Class Autonomous AI Playbook & Cognitive Reasoning Framework for Browser QA & Live Network Intelligence MCP Suite.
  Zero-hardcoding dynamic browser control, semantic DOM observation, full CDP network lifecycle instrumentation,
  secret redaction, console error correlation, endpoint fingerprinting, schema drift detection, and evidence-backed QA audit reporting.
---

# 🛡️ Browser QA & Live Network Intelligence: Zero-Hardcoding Autonomous Playbook

This skill provides **rigorous, code-verified operational instructions** for any AI agent (**Antigravity, Claude 3.7, GPT-4o, DeepSeek-R1/V3, Qwen, Open WebUI**) to autonomously explore, interact with, debug, and audit web applications using the **Browser QA MCP Suite** (`browser-qa-mcp`).

Every capability is built upon dynamic accessibility tree observation and CDP network telemetry—**no hardcoded selectors, no brittle XPath, and no rigid test scripts**.

---

## 🌟 Core Operating Principles (Zero-Hardcoding Manifesto)

1. **Zero Hardcoding**:
   - ❌ **NEVER** guess or hardcode CSS selectors (`#submit-btn`, `.login-form-input`).
   - ✅ **ALWAYS** call `page_inspect()` first to receive semantic, accessibility-tagged interactive nodes (`@1`, `@2`, `@3`) with their active `observation_id`.
2. **Stale Reference Protection**:
   - Every DOM mutation invalidates previous elements. Interaction tools (`browser_click`, `browser_type`, `browser_select`) require the active `observation_id`. If the DOM changes, re-inspect immediately.
3. **Deterministic Human Auth Handoff (No Credential Scraping)**:
   - ❌ **NEVER** ask users for raw passwords or attempt to bypass Google SSO, 2FA, or CAPTCHA.
   - ✅ Call `session_create(browser_mode="headed")` and `session_pause(reason="User login required")`. Wait for the human to log in visibly in the browser window, then resume via `session_resume()`.
4. **Automatic Secret Redaction**:
   - Telemetry automatically scrubs passwords, Bearer tokens, cookies, and sensitive keys across headers, URLs, payloads, and typed inputs.
5. **Safety Guards for Destructive Actions**:
   - Actions with keywords like `delete`, `remove`, `pay`, `purchase`, `cancel` are classified as `DESTRUCTIVE` and blocked unless `confirm_destructive=True`.

---

## 🧠 Cognitive Self-Healing & Cloudflare Bypass Protocol

Real web interfaces are non-linear and dynamic. An autonomous AI agent must NEVER assume a single-shot execution or fail silently on intermediate screens.

### 1. The Screen Diagnosis Engine (`screen_diagnosis`)
Every call to `page_inspect()` returns a semantic `screen_diagnosis` object:
* **`"cloudflare"` (`is_blocked: true`)**: Cloudflare Turnstile or *"Just a moment..."* challenge active.
  * **Autonomous Strategy:**
    1. If in `headed` mode, call `browser_wait(4000)` to allow automatic browser verification.
    2. If not cleared after 5s, call `session_ask_human(question="Cloudflare verification screen samne hai. Kripya browser window me checkbox tick kar dijiye.", options=["Tick kar diya", "Ruk jao"])`.
    3. Call `session_resume()` once verified.
* **`"login"`**: Login or Auth gate detected.
  * **Autonomous Strategy:** Call `session_ask_human(question="Login screen detect hui hai. Kya aap pehle login karna chahte hain?", options=["Pehle login karo", "Direct aage badho"])`. Once logged in, call `session_save(profile_id="...")` to permanently save cookies and session tokens.
* **`"loading"`**: SPA hydration or skeleton loading in progress.
  * **Autonomous Strategy:** Call `browser_wait_idle(timeout_ms=10000)` or `browser_wait(2000)` instead of clicking prematurely.
* **`"interactive"`**: Standard interactive state with valid `@ref` tags. Proceed with intended action.

### 2. Multi-Turn Decision Loop ("Pooch Kar Karo Ya Khud Samjho")
When an element is not immediately found or an unexpected modal/popup appears:
1. **Never Blind-Retry:** Do not repeat the same failed click or type command.
2. **Re-Observe Immediately:** Call `page_inspect()` to get fresh `@ref` tags and the current `screen_diagnosis`.
3. **Formulate Hypothesis:** Determine whether the screen has changed (e.g. cookie consent banner, modal popup, new tab, or error message).
4. **Interactive Ask or Act:**
   * If it is a simple dismissable banner: Click dismiss (`browser_click`).
   * If it is an ambiguous decision: Call `session_ask_human(question="Screen par [X] popup aaya hai. Kya mai isko dismiss karun ya [Y] option chunoo?", options=["Dismiss", "Select Y", "Wait"])`.

---

## 🔄 The 7-Step Autonomous QA Loop

```
  ┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
  │ 1. session_create│ ───>  │2.browser_navigate│ ───>  │ 3. page_inspect │
  └─────────────────┘       └──────────────────┘       └────────┬────────┘
                                                                │
           ┌────────────────────────────────────────────────────┘
           ▼
  ┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
  │4. Action Execution│ ───>│ 5. Telemetry &   │ ───>  │  6. qa_report   │
  │ (click / type)  │       │    Screenshots   │       │ & session_close │
  └─────────────────┘       └──────────────────┘       └─────────────────┘
```

---

## 🛠️ Complete Tool Specification (All 28 Tools)

### Group 1: Session Lifecycle & Human-in-the-Loop ("Puch Puch Kar Karo")
* **`session_create(session_id, browser_mode="headless", target_origin=None, allowed_origins=[], profile_id=None)`**:
  * Initializes browser context. Use `browser_mode="headed"` to open real visible browser window.
* **`session_status(session_id="default")`**: Returns current session state (`active`, `paused`, `closed`).
* **`session_ask_human(question, options=["Yes", "No"], context_summary="", session_id="default")`**:
  * 🤝 **Interactive Protocol:** Pauses execution to ask the human user a question or confirm an action before proceeding.
* **`session_pause(session_id="default", reason="...")`**: Pauses automation so human can complete manual login, 2FA, or CAPTCHA.
* **`session_resume(session_id="default", user_decision=None)`**: Resumes automation after human confirms decision or login completion.
* **`session_save(session_id="default", profile_id=None)`**: Persists authenticated cookies and localStorage to disk (`profiles/<id>/state/`).
* **`session_close(session_id="default")`**: Closes browser context and frees memory cleanly.

### Group 2: Semantic Inspection & Text Extraction
* **`page_inspect(session_id="default")`**:
  * Returns: `{ observation_id: "obs_...", title: "...", interactive_elements: [{"ref": "@1", "role": "button", "name": "Login"}, ...] }`.
  * **Critical:** Use the returned `@ref` and `observation_id` for subsequent actions.
* **`page_forms(session_id="default")`**: Extracts structured form fields, input types, values, and required constraints.
* **`page_text(session_id="default", max_chars=3000)`**: Extracts clean, readable text without noisy HTML tags.

### Group 3: Browser Interaction (Target by `@ref`)
* **`browser_click(target="@1", observation_id="obs_...", session_id="default", confirm_destructive=False)`**:
  * Clicks element by its semantic ref ID. Automatically correlates network and console events.
* **`browser_type(target="@2", text="...", observation_id="obs_...", session_id="default")`**:
  * Types text into target input. Secrets are automatically redacted from logs.
* **`browser_select(target="@3", option="...", observation_id="obs_...", session_id="default")`**: Selects dropdown value.
* **`browser_scroll(direction="down", amount=500, session_id="default")`**: Smoothly scrolls the active viewport.
* **`browser_wait(ms=1000, session_id="default")`**: Simple sleep timer for milliseconds.
* **`browser_wait_for(target="@2"|"Generate", state="visible"|"hidden", timeout_ms=15000, session_id="default")`**:
  * ⏳ **Smart Dynamic Wait:** Waits until target element (@ref, text, button, or CSS selector) appears, disappears, or finishes generating.
* **`browser_wait_idle(timeout_ms=10000, session_id="default")`**:
  * ⏳ **Network Settle:** Waits for in-flight network transactions and DOM mutations to completely settle.
* **`browser_screenshot(session_id="default", full_page=True)`**:
  * Saves high-resolution snapshot to `browser-qa-mcp/screenshots/` and returns `{ status, screenshot_path }`.

### Group 4: Network & Console Intelligence
* **`network_list(session_id="default", filter_type=None, status_code=None, limit=50)`**:
  * Lists captured HTTP requests/responses with method, URL, status, and latency.
* **`network_get(request_id, session_id="default")`**:
  * Returns full transaction payload with headers, query parameters, request body, and response body.
* **`network_summary(session_id="default")`**:
  * Calculates P50, P95, min, max latencies, total payload bytes, and status distribution.
* **`network_stream(session_id="default", limit=20)`**: Streams real-time network ring buffer.
* **`network_clear(session_id="default")`**: Flushes captured network logs.
* **`console_list(session_id="default", min_level="error")`**: Lists uncaught JavaScript exceptions and console errors.
* **`websocket_list(session_id="default")`** / **`sse_list(session_id="default")`**: Inspects live real-time streams and frame counts.

### Group 5: QA Diagnostics & Reporting
* **`qa_anomalies(session_id="default")`**:
  * Detects 4xx/5xx HTTP errors, CORS violations, slow requests (>3000ms), and console exceptions.
* **`qa_correlate(action_id, session_id="default")`**:
  * Traces which network requests and errors were triggered by a specific user click/action.
* **`qa_report(session_id="default", format_type="markdown")`**:
  * Generates an executive, evidence-backed QA audit report with latency benchmarks and error reproduction steps.

---

## ⚡ Canonical Autonomous QA Recipes

### Recipe 1: Full Automated Health & Performance Audit
```python
# Step 1: Create session
session_create(session_id="audit_run", browser_mode="headless")

# Step 2: Navigate to target website
browser_navigate(url="https://app.example.com", session_id="audit_run")

# Step 3: Inspect accessibility tree & discover elements
obs = page_inspect(session_id="audit_run")
# obs contains observation_id and list of elements [@1, @2, @3...]

# Step 4: Capture full-page visual evidence
shot = browser_screenshot(session_id="audit_run", full_page=True)

# Step 5: Check network performance & anomalies
summary = network_summary(session_id="audit_run")
anomalies = qa_anomalies(session_id="audit_run")

# Step 6: Generate executive markdown QA report
report = qa_report(session_id="audit_run", format_type="markdown")

# Step 7: Clean shutdown
session_close(session_id="audit_run")
```

---

### Recipe 2: Secure Headed Authentication Handoff (Human-in-the-Loop)
```python
# Step 1: Launch headed browser so user can see screen
session_create(session_id="user_login", browser_mode="headed")
browser_navigate(url="https://app.example.com/login", session_id="user_login")

# Step 2: Pause and notify user
session_pause(session_id="user_login", reason="Please complete login and 2FA in the opened browser window.")

# [AGENT WAITS FOR USER CONFIRMATION: "Maine login kar liya hai"]

# Step 3: Resume and save session state
session_resume(session_id="user_login")
session_save(session_id="user_login", profile_id="client_admin")

# Step 4: Proceed with authenticated testing
page_inspect(session_id="user_login")
```

---

## 🚫 Negative Constraints & Common Traps

1. ❌ **NEVER use hardcoded CSS/XPath selectors** ➔ Always call `page_inspect()` and target `@1`, `@2`, `@3`.
2. ❌ **NEVER reuse stale observation IDs** ➔ After a click or page navigation, call `page_inspect()` again to get the fresh `observation_id`.
3. ❌ **NEVER execute destructive actions without authorization** ➔ Buttons for deleting data or making payments require `confirm_destructive=True`.
4. ❌ **NEVER leave headless browser sessions open** ➔ Always invoke `session_close(session_id)` to prevent memory leaks.
5. ❌ **NEVER ask for raw credentials** ➔ For SSO / 2FA, use `session_create(browser_mode="headed")` and `session_pause()`.
