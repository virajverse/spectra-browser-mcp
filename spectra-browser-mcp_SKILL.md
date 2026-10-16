---
name: spectra-browser
description: >-
  World-Class Autonomous AI Playbook & Cognitive Reasoning Framework for SpectraBrowser MCP Suite (99 Tools).
  100% Extension-Native live Chrome control, personal profile CDP discovery, human-like AI agent physics,
  smart chat scrolling, visual coordinate clicking, DevTools Inspect-and-Reload network lifecycle instrumentation,
  semantic vision first, pure in-memory ephemeral screenshots (0 disk bytes), high-resolution original image extraction,
  cross-MCP Supabase image hosting, autonomous continuous learning, and evidence-backed QA audit reporting.
---

# 🌐 SpectraBrowser MCP: Autonomous Cognitive Agent Playbook (99 Tools — Bridge-Verified)

This skill provides **rigorous, code-verified operational instructions and dynamic cognitive reasoning frameworks** for any AI agent (**Open WebUI, Antigravity, Claude 3.7, GPT-4o, DeepSeek-R1/V3, Qwen, Llama 3.3**) to autonomously explore, interact with, extract media from, debug, and audit web applications using the **100% Extension-Native & CDP SpectraBrowser MCP Suite** (`spectra-browser-mcp` on Port 8002).

Every capability is built upon dynamic accessibility tree observation, live Chrome Extension control (`ws://127.0.0.1:8765/extension_ws`), personal browser profile registration, human-like interaction physics, zero-disk ephemeral vision, ultra-fast RapidOCR (ONNX), smart media canvas optimization, and full Chrome DevTools Protocol network telemetry—**no hardcoded selectors, no bot-like abrupt movements, and no isolated browser popups**.

---

## 🧬 Dynamic Cognitive Reasoning & Combinatorial Pattern Engine

> **Agent Directive**: Do **NOT** think in rigid, static scripts. Real websites have unpredictable dynamic state changes, modal overlays, bot hurdles, and responsive redesigns.
> The **99 tools** of SpectraBrowser MCP are organized into **4 Fundamental Primitive Archetypes**. By combining these 4 seed primitives, an agent can dynamically synthesize **hundreds of custom, resilient workflow patterns** for any arbitrary browser task!

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
│                  │ │                           │ │                  │ │                        │
│• page_inspect    │ │ • browser_wait_idle       │ │ • browser_click  │ │ • session_memory_set/get│
│• page_understand │ │ • browser_wait_for        │ │ • browser_type   │ │ • action_timeline      │
│• page_see        │ │ • network_list/get/summary│ │ • click_retry    │ │ • macro_start/run      │
│• text_with_pos   │ │ • console_list            │ │ • click_fallback │ │ • test_start/export    │
│• extract_table   │ │ • qa_anomalies            │ │ • element_finger │ │ • qa_report            │
│• browser_ocr     │ │ • page_vitals             │ │ • relocate_elem  │ │ • session_save         │
│• browser_tabs    │ │ • network_stream          │ │ • script_lib_run │ │ • session_ask_human    │
└──────────────────┘ └───────────────────────────┘ └──────────────────┘ └────────────────────────┘
```

### 🧩 Dynamic Pattern Synthesis Algebra
To solve any complex browser automation challenge, construct an emergent pipeline by chaining 2 to 4 primitives:

$$\text{Emergent Automation Pattern} = \text{Seed}_i \xrightarrow{\text{Observation}} \text{Seed}_j \xrightarrow{\text{Action \& Wait}} \text{Seed}_k \xrightarrow{\text{Self-Heal / Persist}} \text{Seed}_m$$

#### 🔮 6 Exemplar Emergent Combinations (Generated on the Fly):

1. **Zero-Failure Form Submission with Self-Healing Loop ($1 \rightarrow 3 \rightarrow 2 \rightarrow [3_{\text{retry}}] \rightarrow 4$)**:
   - `page_inspect()` (Capture fresh `observation_id` & `@ref` IDs)
   - `browser_type(target="@name", text="...")` + `browser_click(target="@submit")`
   - `browser_wait_idle(timeout_ms=8000)` + `network_summary()`
   - *If Stale/Blocked*: Trigger `element_fingerprint()` ➔ `relocate_element()` ➔ `browser_click_fallback(["@submit", "text:Confirm"])`
   - *Result*: Record successful mutation into `action_timeline` with 0% false failures.

2. **Infinite-Scroll Data & Media Harvester ($1 \rightarrow 3 \rightarrow 1 \rightarrow 4$)**:
   - `page_understand()` (Detect main grid container and layout zones)
   - `browser_scroll_harvest(target_count=50, max_scrolls=10)`
   - `extract_table()` OR `browser_extract_images(auto_optimize_platform="INSTAGRAM")`
   - `session_memory_set(key="harvested_dataset", value=...)`
   - *Result*: Completely harvest pagination/infinite feeds without writing junk files to disk.

3. **Flaky Flow Detector & Automated Test Case Exporter ($4 \rightarrow 1 \rightarrow 3 \rightarrow 2 \rightarrow 4$)**:
   - `test_start_recording(name="checkout_flow")`
   - Execute user flow using `browser_click` and `browser_type`
   - Intercept backend failures via `qa_anomalies()` and `console_list(min_level="error")`
   - `test_stop_recording()` ➔ `test_export(name="checkout_flow")`
   - *Result*: Instant, reproducible JSON test script with full DevTools telemetry and network timings for developers.

4. **Human-in-the-Loop Safe Destructive Mutation ($1 \rightarrow 4_{\text{guard}} \rightarrow 3 \rightarrow 4_{\text{audit}}$)**:
   - `page_inspect()` (Detects button text: "Delete Database", "Confirm Payment", or "Purge")
   - Safety Intercept: Call `session_ask_human(question="Confirm deletion of record?", options=["Proceed", "Cancel"])`
   - If confirmed: Execute `browser_click(confirm_destructive=True)`
   - Call `qa_report(format_type="markdown")` to log permanent forensic proof of human authorization.

5. **ProseMirror / React Shadow-DOM Editor Bypass ($1 \rightarrow 3_{\text{script}} \rightarrow 2 \rightarrow 1_{\text{vision}}$)**:
   - When rich text editors (ChatGPT, Notion, Jira) block synthetic keystrokes:
   - Call `script_library_add` with `document.execCommand('insertText', false, text)`
   - Call `script_library_run()` to fire React native state setters
   - `browser_wait_idle()` ➔ `page_see(include_screenshot=True)` to visually confirm text arrival.

6. **Visual Layout Regression & Accessible Audit Radar ($1 \rightarrow 1_{\text{compare}} \rightarrow 4$)**:
   - `browser_screenshot(save_to_disk=True)` (Capture baseline)
   - Apply UI change / trigger state
   - `visual_compare(baseline="...", current="...")` (Compute pixel similarity % & bounding boxes)
   - `page_a11y_audit()` (Lightweight WCAG heuristic scoring 0-100)
   - Pass findings into executive `qa_report`.

---

## 🧠 LLM Quick-Start & Cognitive Decision Flow

```
                     ┌───────────────────────────────────────────────┐
                     │          Browser Automation Request           │
                     └───────────────────────┬───────────────────────┘
                                             │
               ┌─────────────────────────────┴─────────────────────────────┐
               ▼                                                           ▼
    [Check Connection Status]                                    [Media / Visual Task]
               │                                                           │
   1. `extension_status()`                                       1. `browser_navigate(url="...")`
      - If False: Give Setup Hub link & instructions               2. `browser_extract_images()`
               │                                                      Extract full-res uncompressed PNGs
   2. `browser_tabs()` ➔ `browser_select_tab(id)`                3. Pass `file_path` to `taliyo-blog-engine`
               │                                                      Auto-uploads to Supabase CDN!
   3. `page_inspect()` (0 Disk Bytes)
      - Returns `@1`, `@2` semantic tags
               │
   4. Execute Action:
      - Click: `browser_click(target="@12")`
      - Type: `browser_type(target="@5", text="...")`
      - Scroll: `browser_scroll(direction="down")`
               │
   5. Dynamic Wait:
      `browser_wait_idle()` or `browser_wait_for("@submit")`
```

---

## 🔌 Mandatory Extension Installation Hub & AI Agent Fallback Protocol

Whenever an AI Agent attempts any SpectraBrowser action and the Chrome Extension is **NOT connected**:
1. 🛑 **NEVER Hallucinate** or fail silently.
2. 📢 **Provide the User Direct Setup Hub & 1-Click Download Links**:
   * 🌐 **Live Setup & Diagnostic Hub**: [https://mcp3.taliyotechnologies.com](https://mcp3.taliyotechnologies.com)
   * 📥 **1-Click ZIP Download**: [https://mcp3.taliyotechnologies.com/download-extension](https://mcp3.taliyotechnologies.com/download-extension)
3. 📖 **Guide the User in 3 Simple Steps**:
   1. **Download & Extract**: Download `spectra-browser-extension.zip` from https://mcp3.taliyotechnologies.com/download-extension and unzip it.
   2. **Open Chrome Extensions**: Go to `chrome://extensions` and enable **"Developer mode"** (top right toggle).
   3. **Load Unpacked**: Click **"Load unpacked"**, select the extracted `extension` folder, and **keep that Chrome profile open**.

---

## 🌟 Core Operating Principles (Zero-Hardcoding, Zero-Disk & Human-Like Manifesto)

1. **100% Extension-Native (Your Personal Logged-In Chrome)**:
   * ❌ **NEVER** launch isolated blank Playwright browsers or spawn headless sandbox windows when user data is needed.
   * ✅ **ALWAYS** control the user's live Chrome browser directly via the Spectra Chrome Extension Bridge (`ws://127.0.0.1:8765/extension_ws`) or registered CDP profile.

2. **Semantic Vision First & Pure In-Memory Ephemeral Vision (Zero Disk Usage)**:
   * ⚡ **Primary (Default): Semantic Vision (`page_inspect`)**:
     - For 95% of tasks (buttons, forms, links, navigation), ALWAYS call `page_inspect()` first.
     - Returns lightweight JSON accessibility tree with `@1`, `@2` references in ~5ms. **0 Disk Bytes Used!**
   * 🖼️ **Secondary: Pure In-Memory Ephemeral Screenshot (`browser_screenshot(save_to_disk=False)`)**:
     - When visual layout confirmation is needed, inspect base64 data URI directly in memory.
   * 🔍 **Dual Vision Fallback (When in Ambiguity)**:
     - Combine `page_inspect()` AND `browser_screenshot()` simultaneously to resolve coordinates and elements with 100% confidence.

3. **Human-Like Interaction Physics (No Bot-Type Movement)**:
   * 🖱️ **Natural Clicking (`browser_click`)**: Hovers first (`pointerover` → `mouseover` → `pointermove`), adds human jitter coordinates (±1–3px from center), realistic press delay (40ms–70ms), and release.
   * ⌨️ **Natural Typing (`browser_type`)**: Types character-by-character with realistic typing rhythm (**15ms–45ms per keystroke variable delay**), dispatching `keydown`, `input`, and `keyup` with React/Vue prototype setter compatibility.
   * 📜 **Sinusoidal Smooth Scrolling (`browser_scroll`)**: 6-micro-step sinusoidal eased scroll animation with authentic `WheelEvent` dispatch.
   * 🎯 **Keyboard Physics (`browser_press`)**: Complete `keydown` → `keypress` → 40ms hold → `keyup` cycle.

4. **Visual Coordinate Clicking**:
   * Click by semantic `@ref` (e.g. `@15`), text label (`"Sign In"`), or direct visual pixel coordinates: `browser_click(target="540, 720")`.

5. **Full-Resolution Original Image Extraction**:
   * ❌ **NEVER** use viewport screenshot crops when full-resolution original media is needed.
   * ✅ Call `browser_extract_images()` to extract raw blobs directly from CDN/DOM in original resolution (e.g. 1672x941 PNG/WebP) with SHA-256 byte deduplication.
   * 🔗 **Taliyo Integration:** Pass the returned `file_path` directly to `taliyo-blog-engine` (`upload_blog_image`, `create_blog_post`) to auto-upload to Supabase Storage and publish live!

---

## 🛠️ Complete 99-Tool Reference Specification (All 15 Operational Groups)

### Group 0: Chrome Extension Bridge & Profile Registration (8 Tools)
1. **`extension_status()`**: Checks if Spectra Chrome Extension is connected via WebSocket (`ws://127.0.0.1:8765/extension_ws`).
2. **`browser_register_start(display_name="Personal Chrome", port=9222, ...)`**: Auto-discovers Chrome profile, starts CDP port, attaches debugging.
3. **`browser_register_status(registration_id=None)`**: Checks registration health and profile metadata without leaking credentials.
4. **`browser_register_confirm(registration_id)`**: Confirms browser registration after user approval.
5. **`browser_register_revoke(registration_id)`**: Revokes browser registration and detaches automation.
6. **`browser_register_list()`**: Lists all registered browser profiles.
7. **`browser_tabs(session_id="default")`**: Lists all open tabs in user's Chrome with tab ID, title, and current URL.
8. **`browser_select_tab(tab_id, session_id="default")`**: Switches focus to designated tab (pass `tab_id` as **STRING**) and attaches DevTools debugger.

### Group 1: Session Lifecycle & Human-in-the-Loop (7 Tools)
9. **`session_create(session_id="default", browser_mode="headed", browser_target="managed", ...)`**: Initializes or attaches browser session.
10. **`session_status(session_id="default")`**: Returns active session URL, state, origin compliance, and telemetry count.
11. **`session_pause(session_id="default", reason="User authentication required")`**: Pauses for 2FA / CAPTCHA handoff.
12. **`session_ask_human(question, options=None, context_summary=None, session_id="default")`**: Prompts user for interactive decision.
13. **`session_resume(session_id="default", user_decision=None)`**: Resumes automation after human confirmation.
14. **`session_save(session_id="default", profile_id=None)`**: Persists cookies/storage state to disk for profile reuse.
15. **`session_close(session_id="default")`**: Closes session and frees allocated memory.

### Group 2: Live Navigation & Human-Like Interaction (7 Tools)
16. **`browser_navigate(url, session_id="default")`**: Navigates active tab to target URL.
17. **`browser_reload(ignore_cache=True, session_id="default")`**: Reloads tab with DevTools Network & Console enabled.
18. **`browser_click(target, observation_id=None, session_id="default", confirm_destructive=False)`**: Clicks tagged element (`@5`) or coordinates (`"500, 300"`).
19. **`browser_type(target, text, observation_id=None, clear=False, session_id="default")`**: Types text with 15–45ms human cadence.
20. **`browser_select(target, option, observation_id=None, session_id="default")`**: Selects dropdown option by visible label or value.
21. **`browser_scroll(direction="down", amount=500, target=None, session_id="default")`**: Sinusoidal smooth scrolling with micro-eased WheelEvents.
22. **`browser_press(key="Enter", session_id="default")`**: Dispatches keyboard keypress (`Enter`, `Tab`, `Escape`).

### Group 3: Media Extraction, Wait & Vision Inspection (6 Tools)
23. **`browser_extract_images(save_dir=None, return_base64=False, session_id="default", auto_optimize_platform=None)`**: Extracts full-res images directly from DOM/CDN. Set `auto_optimize_platform="INSTAGRAM"` or `"EMAIL"` to auto-compress!
24. **`browser_wait(ms=1000, session_id="default")`**: Sleep in milliseconds.
25. **`browser_wait_for(target, state="visible", timeout_ms=15000, session_id="default")`**: Polls dynamically until element achieves state.
26. **`browser_wait_idle(timeout_ms=10000, session_id="default")`**: Waits for network/DOM mutations to settle.
27. **`browser_screenshot(session_id="default", full_page=False, save_to_disk=False, return_base64=True)`**: In-memory screenshot (0 disk bytes).
28. **`browser_ocr(image_path=None, session_id="default", filter_pattern=None)`**: Ultra-fast RapidOCR (ONNX) engine to extract text, phone numbers, prices, and bounding boxes in <100ms without heavy PyTorch.

### Group 4: Page Inspection & Semantic DOM (3 Tools)
29. **`page_inspect(session_id="default")`**: Generates structured semantic snapshot with new observation_id and assigned `@ref` IDs (`@1`, `@2`).
30. **`page_forms(session_id="default")`**: Returns detected forms, fields, types, placeholders, and current values.
31. **`page_text(session_id="default", max_chars=3000)`**: Extracts visible text summary of active page.

### Group 5: DevTools Telemetry & Network Forensics (8 Tools)
32. **`network_list(session_id="default", filter_type=None, status_code=None, errors_only=False, search_query=None, limit=100)`**: DevTools network request table.
33. **`network_get(request_id, session_id="default", include_request_body=True, include_response_body=True, max_body_bytes=100000)`**: Full request/response details.
34. **`network_summary(session_id="default")`**: Latency percentiles (P50/P95) and error breakdown.
35. **`network_clear(session_id="default")`**: Resets telemetry buffer.
36. **`network_stream(session_id="default", filter_type=None, limit=20)`**: Consumes real-time stream.
37. **`console_list(session_id="default", min_level="info", limit=50)`**: Console logs and uncaught errors.
38. **`websocket_list(session_id="default")`**: Active WebSocket frame metrics.
39. **`sse_list(session_id="default")`**: Server-Sent Events stream messages.

### Group 6: Automated QA & Forensic Auditing (3 Tools)
40. **`qa_anomalies(session_id="default")`**: Scans for 4xx/5xx errors, CORS issues, and crashes.
41. **`qa_correlate(action_id=None, session_id="default")`**: Maps user clicks to network transactions.
42. **`qa_report(session_id="default", format_type="markdown")`**: Generates evidence-backed QA markdown report.

### Group 7: System Storage Audit & Disk Purge (2 Tools)
43. **`check_mcp_storage()`**: Scans disk space used by temporary screenshots and logs.
44. **`clean_mcp_storage(dry_run=False)`**: Safely purges temporary files to free laptop storage.

### Group 8: Media Optimization & Smart Canvas Engine (2 Tools)
45. **`optimize_media_for_platform(image_path, platform="INSTAGRAM", max_size_kb=200, output_format="WEBP", background_color="#0F172A", ...)`**: Crops, canvas-fits, and compresses raw heavy images down to <=200KB for `INSTAGRAM` (1080x1350), `STORY` (1080x1920), `EMAIL` (650px), `BLOG` (1200x630), `THUMBNAIL` (1280x720), or `CUSTOM`.
46. **`optimize_media_batch(source_dir_or_pattern=None, platform="INSTAGRAM", max_size_kb=200, output_format="WEBP")`**: Batch-optimizes all newly extracted browser images or a folder in one call.

### Group 9: Session Memory, Action Timeline & Failed Targets (9 Tools)
47. **`session_memory_set(session_id="default", key="", value=None)`**: Stores key-value pair in session memory (survives pause/resume).
48. **`session_memory_get(session_id="default", key="", default=None)`**: Retrieves value from session memory.
49. **`session_memory_delete(session_id="default", key="")`**: Deletes key from session memory.
50. **`session_memory_list(session_id="default")`**: Lists all keys and stored values.
51. **`session_memory_clear(session_id="default")`**: Clears all session working memory.
52. **`action_timeline(session_id="default", limit=20)`**: Returns action history with outcomes, network effects, and console errors.
53. **`action_last(session_id="default")`**: Returns last recorded browser action with outcome.
54. **`failed_targets_list(session_id="default")`**: Lists failed click/type targets to avoid retrying blindly.
55. **`failed_targets_clear(session_id="default")`**: Clears failed-target memory.

### Group 10: Multi-Tab & Named Tab Handles (4 Tools)
56. **`tab_create(name, url="", tab_id="", session_id="default")`**: Creates a named tab handle for multi-tab orchestration.
57. **`tab_switch(name, session_id="default")`**: Switches active automation to a named tab handle.
58. **`tab_close(name, session_id="default")`**: Closes/removes a named tab handle.
59. **`tab_list(session_id="default")`**: Lists all named tab handles in this session.

### Group 11: Macros & Test Recording Engine (12 Tools)
60. **`macro_start_recording(name, description="")`**: Starts capturing browser actions as replayable steps.
61. **`macro_stop_recording()`**: Stops macro recording and returns captured steps.
62. **`macro_list()`**: Lists all recorded macros.
63. **`macro_get(name)`**: Returns macro steps for inspection.
64. **`macro_delete(name)`**: Deletes a recorded macro.
65. **`macro_run(name, session_id="default")`**: Replays a recorded macro step-by-step.
66. **`test_start_recording(name, session_id="default", metadata=None)`**: Starts recording an exportable test case.
67. **`test_stop_recording(name=None)`**: Stops test recording, capturing steps + network + console evidence.
68. **`test_list()`**: Lists all recorded test cases.
69. **`test_get(name)`**: Returns full test case with steps and evidence.
70. **`test_delete(name)`**: Deletes a test case.
71. **`test_export(name)`**: Exports a test case as replayable JSON with reproduction steps.

### Group 12: Auth, Health & Resilient Self-Healing Interaction (7 Tools)
72. **`auth_status(session_id="default")`**: Detects login state (`logged_in: True/False/unknown`) via page signals.
73. **`session_health_check(session_id="default")`**: Checks session/extension health and recommends next action.
74. **`browser_click_retry(target, session_id="default", max_attempts=3, backoff_ms=500)`**: Clicks with auto-retry + exponential backoff.
75. **`browser_click_fallback(targets, session_id="default")`**: Tries multiple targets in order until one succeeds (e.g. `['@3', 'text:Login', 'css:button[type=submit]']`).
76. **`element_fingerprint(ref_id, session_id="default")`**: Builds stable visual+structural fingerprint (survives `@ref` reassignment).
77. **`relocate_element(fingerprint, session_id="default")`**: Re-finds an element after page re-render using stored fingerprint object.
78. **`find_element(description, session_id="default", limit=5)`**: Finds elements by semantic text description.

### Group 13: Advanced Vision, Layout Geometry & Spatial Semantics (9 Tools)
79. **`visual_compare(baseline, current, threshold=12)`**: Compares two screenshots -> similarity % + changed regions bounding box.
80. **`screenshot_annotate(image="", annotations=None, session_id="default", save_to_disk=False)`**: Draws bounding boxes and labels on screenshot.
81. **`page_vitals(session_id="default")`**: Collects performance signals (TTFB, FCP, DCL, resource transfer KB) via CDP.
82. **`page_a11y_audit(session_id="default")`**: Lightweight WCAG heuristic audit (alt, button names, labels, h1) -> score 0-100.
83. **`extract_table(table_ref="", session_id="default", max_rows=100)`**: Extracts HTML tables into structured `{headers, rows, records}` JSON.
84. **`page_understand(session_id="default")`**: Classifies page into layout zones (`header`, `nav`, `sidebar`, `main`, `footer`, `modal`) from geometry.
85. **`find_element_smart(description, session_id="default", limit=5)`**: Spatial-aware find: handles `"bottom-right"`, `"third row"`, `"inside pricing"` qualifiers.
86. **`text_with_positions(session_id="default", max_items=100)`**: Visible text nodes WITH bounding boxes `(x, y)` via CDP without OCR overhead.
87. **`extract_by_description(fields, session_id="default")`**: Extracts named fields by description without CSS: `{"price": "price in product card"}`.

### Group 14: Script Library, Site Adapters & Infinite Harvesting (9 Tools)
88. **`script_library_add(name, js_code, description="", session_id="default")`**: Stores reusable JS snippet for later replay.
89. **`script_library_list(session_id="default")`**: Lists stored JS snippets.
90. **`script_library_get(name, session_id="default")`**: Returns stored JS snippet.
91. **`script_library_delete(name, session_id="default")`**: Deletes stored JS snippet.
92. **`script_library_run(name, session_id="default")`**: Runs stored JS snippet in the live tab via CDP.
93. **`adapter_save(site, aliases, notes="", session_id="default")`**: Saves site-specific selector aliases, e.g. `github.com: {'search box': 'input[name=q]'}`.
94. **`adapter_list(session_id="default")`**: Lists all site adapters.
95. **`adapter_resolve(site, friendly_name, session_id="default")`**: Resolves friendly name to selector for a site.
96. **`browser_scroll_harvest(selector="", target_count=50, max_scrolls=15, session_id="default")`**: Scrolls until N items loaded (infinite scroll), then counts matches.

### Group 15: Unified Vision Modes & Cognitive Page Seeing (3 Tools)
97. **`vision_set_mode(mode="auto", session_id="default")`**: Sets visual response mode: `'auto'`, `'visual'` (VLM models), `'text'` (non-VLM token-saving).
98. **`vision_get_mode(session_id="default")`**: Returns current visual response mode.
99. **`page_see(session_id="default", max_items=60, include_screenshot=True)`**: Unified 'see' combining text positions, layout zones, and optional screenshot.

---

## 🧪 Field-Verified Addendum — 99-Tool OpenAPI Bridge Payloads & Gotchas

> Bridge: `http://127.0.0.1:8002` — every tool accepts `POST /<tool_name>` with JSON body. Default: `{"session_id": "default"}`.

### Verified Payloads (Copy-Paste Ready)

```json
// Tabs
POST /browser_tabs  {}
POST /browser_select_tab {"tab_id":"148775211","session_id":"default"}  // NOTE: tab_id MUST be a string!

// Session
POST /session_create {"session_id":"default","browser_mode":"headed","browser_target":"managed"}
POST /session_status {"session_id":"default"}

// Navigation + Wait
POST /browser_navigate {"url":"https://example.com/path","session_id":"default"}
POST /browser_reload   {"ignore_cache":true,"session_id":"default"}
POST /browser_wait_idle {"timeout_ms":8000,"session_id":"default"}
POST /browser_wait      {"ms":2500,"session_id":"default"}

// Inspection
POST /page_inspect {"session_id":"default"}
POST /page_understand {"session_id":"default"}
POST /page_see {"session_id":"default"}
POST /extract_table {"session_id":"default"}

// Resilient Interaction
POST /browser_click  {"target":"@5","observation_id":"obs_...","session_id":"default"}
POST /browser_click_fallback {"targets":["@30","818, 175"],"session_id":"default"}
POST /browser_click_retry {"target":"@30","session_id":"default","max_attempts":3}
POST /browser_type   {"target":"@2","text":"hello","observation_id":"obs_...","clear":true,"session_id":"default"}
POST /browser_scroll {"direction":"down","amount":900,"session_id":"default"}

// Telemetry & Auditing
POST /network_list    {"search_query":"admin/blogs","limit":100,"session_id":"default"}
POST /network_summary {"session_id":"default"}
POST /console_list    {"min_level":"error","limit":20,"session_id":"default"}
POST /qa_anomalies    {"session_id":"default"}
POST /qa_report       {"session_id":"default","format_type":"markdown"}

// Script Library (ProseMirror & React Bypass)
POST /script_library_add {"session_id":"default","name":"fill-send","js_code":"document.title"}
POST /script_library_run {"session_id":"default","name":"fill-send"}

// Rapid OCR (ONNX)
POST /browser_ocr {"session_id":"default"}
```

### ⚠️ Critical Gotchas (Avoid Costly Mistakes)

1. **`tab_id` MUST be a STRING:**
   - In `browser_select_tab` / `session_create`, passing an integer returns `422 "Input should be a valid string"`. Always pass `"148775063"`.
2. **`find_element_smart` expects `description`, NOT `query`:**
   - Passing `{"query": "..."}` returns a `422 missing body.description` error.
3. **`element_fingerprint` expects `ref_id`, NOT `target`:**
   - Pass `{"ref_id": "@37", "observation_id": "obs_..."}`.
4. **`relocate_element` expects `fingerprint` OBJECT:**
   - Pass the dictionary returned by `element_fingerprint`, not just the ref string.
5. **`network_clear` detaches DevTools debugger:**
   - After calling `network_clear`, always trigger `browser_reload` to re-attach the CDP network listener.
6. **Destructive Actions Guard:**
   - Always verify and request human confirmation for actions that alter production data (e.g. `delete`, `pay`, `revoke`).

---

## 🤝 Decoupled Agentic Symbiosis: Spectra-Browser + Infinity-Scraper MCP

> **Core Agent Directive (Zero Hardcoded Coupling):**
> SpectraBrowser and InfinityScrape are **100% decoupled, independent MCP servers**. Neither server hardcodes calls to the other.
> **The AI AGENT is the Brain & Sole Orchestrator:**
> 1. **Default High Speed:** The AI Agent runs high-speed research, search, sitemaps, and bulk scraping using **InfinityScrape** (<150ms per page, 33 tools).
> 2. **Signal Detection:** If InfinityScrape encounters an interactive anti-bot wall (Cloudflare Turnstile, Reddit "Prove your humanity", or 403 challenge), it returns an explicit **Anti-Bot Advisory Signal** (`requires_browser_escalation: true`).
> 3. **Agent-Driven Escalation:** The **AI Agent** reads this signal and autonomously decides to shift that single blocked target to **SpectraBrowser** (`browser_navigate(url=...)`, followed by `page_understand()` or `page_inspect()`).
> 4. **Bypass & Resume:** SpectraBrowser accesses the URL via the user's real human Chrome context. The AI Agent ingests the rendered markdown and immediately resumes high-speed bulk operations with InfinityScrape!

```
┌────────────────────────────────────────────────────────────────────────┐
│             DECOUPLED AGENTIC WATERFALL ARCHITECTURE                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                               [AI AGENT]
                         (The Brain & Decision Maker)
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         ▼                                                     ▼
┌─────────────────────────────────┐           ┌─────────────────────────────────┐
│     INFINITY SCRAPER (MCP)      │           │      SPECTRA BROWSER (MCP)      │
│ • Ultra-Fast TLS Engine (<150ms)│           │ • Live Chrome Extension / CDP   │
│ • 33 Tools: OSINT, Search, Docs │           │ • 99 Tools: DOM & Visual QA     │
│ • Fast, Lightweight (20MB RAM)  │           │ • Human Cookies & GPU Canvas    │
└────────────────┬────────────────┘           └────────────────┬────────────────┘
                 │                                             ▲
                 │ (If Anti-Bot Challenge Signal Raised)       │
                 └────────────► [AI AGENT SHIFTS] ─────────────┘
```

### 🔬 Honest Reality Check: 5 Remaining Bottlenecks (Zero Cheating)
Web scraping is an ongoing cat-and-mouse dynamic. No architecture in the world is "100% unblockable forever". Here are the true bottlenecks and how this dual suite handles them:

1. **IP / ASN Reputation Ban (Network-Level Bottleneck):**
   - *Reality*: Even with a genuine Chrome session in SpectraBrowser, if the machine's public IP address belongs to a blacklisted cloud datacenter (AWS, DigitalOcean, Hetzner) or an abused residential VPN, Cloudflare/Akamai drops connections at the TCP SYN / TLS layer.
   - *Mitigation*: Supply rotating residential or 4G/5G mobile proxies to `proxy` in InfinityScrape or launch SpectraBrowser with `--proxy-server`.

2. **Hard Interactive Visual Puzzles (Human Interaction Bottleneck):**
   - *Reality*: Cloudflare Managed Challenges pass automatically in real Chrome. However, complex 3D rotating animal puzzles, sliding jigsaws, or hCaptcha image grids cannot be solved by simple headless scripts.
   - *Mitigation*: SpectraBrowser uses `page_screenshot` for visual inspection, or triggers `session_ask_human` to allow the user to click the puzzle once in their open Chrome tab while retaining automated control.

3. **Memory & Concurrency Scaling (Resource Bottleneck):**
   - *Reality*: InfinityScrape can scrape 100 pages concurrently with 25MB RAM. SpectraBrowser runs full Chrome processes requiring 200MB–400MB RAM per tab.
   - *Rule*: Never crawl bulk sitemaps or batch scrape with SpectraBrowser. Always use InfinityScrape for volume (Tiers 1-2) and escalate ONLY challenging URLs to SpectraBrowser (Tier 3).

4. **Session Invalidation & 2FA Expiry (State Bottleneck):**
   - *Reality*: Gated platforms (LinkedIn, Twitter, banking portals) invalidate session cookies on a regular schedule or after unusual navigation velocity.
   - *Mitigation*: SpectraBrowser connects to the user's live profile (`browser_register_start`) so that whenever the user logs in once, the agent inherits all active cookies without storing raw passwords.

5. **Advanced Telemetry & Behavioral Cadence (Heuristic Bottleneck):**
   - *Reality*: Datadome and Akamai Bot Manager measure micro-jitters in mouse trajectories and keystroke interval distributions.
   - *Mitigation*: SpectraBrowser implements human-cadence physics (Bezier mouse curves, randomized typing delays, DevTools CDP synthetic events) rather than raw DOM `.click()` mutations.

