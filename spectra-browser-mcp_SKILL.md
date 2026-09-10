---
name: spectra-browser
description: >-
  World-Class Autonomous AI Playbook & Cognitive Reasoning Framework for SpectraBrowser MCP Suite.
  100% Extension-Native live Chrome control, personal profile CDP discovery, human-like AI agent physics,
  smart chat scrolling, visual coordinate clicking, DevTools Inspect-and-Reload network lifecycle instrumentation,
  semantic vision first, pure in-memory ephemeral screenshots (0 disk bytes), high-resolution original image extraction,
  cross-MCP Supabase image hosting, autonomous continuous learning, and evidence-backed QA audit reporting.
---

# 🌐 SpectraBrowser MCP: Autonomous Cognitive Agent Playbook (46 Tools)

This skill provides **rigorous, code-verified operational instructions** for any AI agent (**Open WebUI, Antigravity, Claude 3.7, GPT-4o, DeepSeek-R1/V3, Qwen, Llama 3.3**) to autonomously explore, interact with, extract media from, debug, and audit web applications using the **100% Extension-Native & CDP SpectraBrowser MCP Suite** (`spectra-browser-mcp` on Port 8002).

Every capability is built upon dynamic accessibility tree observation, live Chrome Extension control (`ws://127.0.0.1:8765/extension_ws`), personal browser profile registration, human-like interaction physics, zero-disk ephemeral vision, and full Chrome DevTools Protocol network telemetry—**no hardcoded selectors, no bot-like abrupt movements, and no isolated browser popups**.

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
   1. **Download & Extract**: Download `spectra-browser-extension.zip` from https://mcp3.taliyotechnologies.com/download-extension and unzip it to any folder.
   2. **Open Chrome Extensions**: Open Google Chrome, go to `chrome://extensions`, and enable **"Developer mode"** (top right toggle).
   3. **Load Unpacked**: Click **"Load unpacked"**, select the extracted `extension` folder, and **keep that Chrome profile open** so the AI agent can execute live browser automation!

---

## 🌟 Core Operating Principles (Zero-Hardcoding, Zero-Disk & Human-Like Manifesto)

1. **100% Extension-Native (Your Personal Logged-In Chrome)**:
   * ❌ **NEVER** attempt to launch an isolated Playwright browser or spawn headless windows.
   * ✅ **ALWAYS** control the user's live Chrome browser directly via the Spectra Chrome Extension Bridge (`ws://127.0.0.1:8765/extension_ws`) or registered CDP profile.

2. **Semantic Vision First & Pure In-Memory Ephemeral Vision (Zero Disk Usage)**:
   * ⚡ **Primary (Default): Semantic Vision (`page_inspect`)**:
     - For 95% of tasks (buttons, forms, links, navigation), ALWAYS call `page_inspect()` first.
     - Returns a lightweight 5KB JSON accessibility tree with `@1`, `@2` references in ~5ms.
     - **0 Disk Bytes Used!**
   * 🖼️ **Secondary: Pure In-Memory Ephemeral Screenshot (`browser_screenshot(save_to_disk=False)`)**:
     - When visual layout confirmation is needed, call `browser_screenshot()`.
     - Base64 data URI is inspected directly in memory.
     - **0 Disk Bytes Written to Hard Drive!**
   * 🔍 **Dual Vision Fallback (When in Confusion / Ambiguity)**:
     - If a page contains dynamic canvas, shadow DOM, unlabelled buttons, or visual ambiguity, use **BOTH** `page_inspect()` AND `browser_screenshot(save_to_disk=False)` simultaneously to resolve coordinates and elements with 100% confidence.

3. **Human-Like Interaction Physics (No Bot-Type Movement)**:
   * 🖱️ **Natural Clicking (`browser_click`)**: Hovers first (`pointerover` → `mouseover` → `pointermove`), adds subtle human jitter coordinates (±1–3px from center), applies realistic finger press delay (40ms–70ms), holds (30ms–50ms), and releases (`pointerup` → `mouseup` → `click`).
   * ⌨️ **Natural Typing (`browser_type`)**: Types character-by-character with realistic human typing rhythm (**15ms–45ms per keystroke variable delay**), dispatching `keydown`, `input` (`inputType: "insertText"`), and `keyup` with React/Vue prototype setter compatibility.
   * 📜 **Sinusoidal Smooth Scrolling (`browser_scroll`)**: Dispatches a 6-micro-step sinusoidal eased scroll animation with authentic `WheelEvent` dispatch rather than mechanical single-frame jumps.
   * 🎯 **Keyboard Physics (`browser_press`)**: Dispatches complete `keydown` → `keypress` → 40ms hold → `keyup` cycle.

4. **Visual Coordinate Clicking**:
   * Click by semantic `@ref` (e.g. `@15`), text label (`"Sign In"`), or direct visual pixel coordinates: `browser_click(target="540, 720")`.

5. **Full-Resolution Original Image Extraction**:
   * ❌ **NEVER** use viewport screenshot crops when full-resolution original media is needed.
   * ✅ Call `browser_extract_images()` to extract raw blobs directly from CDN/DOM in original resolution (e.g. 1672x941 PNG/WebP) with SHA-256 byte deduplication.
   * 🔗 **Taliyo Integration:** Pass the returned `file_path` directly to `taliyo-blog-engine` (`upload_blog_image`, `create_blog_post`, `create_our_project`) to auto-upload to Supabase Storage and publish live!

---

## 🛠️ Complete Tool Reference Specification (All 46 Tools)

### Group 0: Chrome Extension Bridge & Profile Registration (8 Tools)
1. **`extension_status()`**: Checks if Spectra Chrome Extension is connected via WebSocket.
2. **`browser_register_start(display_name="Personal Chrome", cdp_url=None, port=9222, profile_identifier=None, chrome_path=None, auto_launch=True, auto_confirm=True)`**: Auto-discovers Chrome profile, starts CDP port, attaches debugging.
3. **`browser_register_status(registration_id=None)`**: Checks registration health and profile metadata.
4. **`browser_register_confirm(registration_id)`**: Confirms browser registration after user approval.
5. **`browser_register_revoke(registration_id)`**: Revokes browser registration and detaches automation.
6. **`browser_register_list()`**: Lists all registered browser profiles.
7. **`browser_tabs(session_id="default")`**: Lists all open tabs in user's Chrome with tab ID, title, and URL.
8. **`browser_select_tab(tab_id, session_id="default")`**: Switches focus to designated tab and attaches DevTools debugger.

### Group 1: Session Lifecycle & Human-in-the-Loop (7 Tools)
9. **`session_create(session_id="default", browser_mode="headed", browser_target="managed", registration_id=None, tab_id=None, target_origin=None, allowed_origins=None, profile_id=None)`**: Initializes or attaches browser session.
10. **`session_status(session_id="default")`**: Returns active session URL, state, and telemetry count.
11. **`session_pause(session_id="default", reason="User authentication required")`**: Pauses for 2FA / CAPTCHA handoff.
12. **`session_ask_human(question, options=None, context_summary=None, session_id="default")`**: Prompts user for interactive decision.
13. **`session_resume(session_id="default", user_decision=None)`**: Resumes automation after human confirmation.
14. **`session_save(session_id="default", profile_id=None)`**: Persists cookies/storage state.
15. **`session_close(session_id="default")`**: Closes session and frees memory.

---

### Group 2: Live Navigation & Inspection (7 Tools)
16. **`browser_navigate(url, session_id="default")`**: Navigates active tab to target URL.
17. **`browser_reload(ignore_cache=True, session_id="default")`**: Reloads tab with DevTools Network & Console enabled.
18. **`page_inspect(session_id="default")`**: Returns semantic accessibility tree with `@1`, `@2` tags (0 disk bytes).
19. **`page_forms(session_id="default")`**: Detects form inputs, placeholders, and current values.
20. **`page_text(session_id="default", max_chars=3000)`**: Extracts visible text summary of active page.
21. **`browser_screenshot(session_id="default", full_page=False, save_to_disk=False, return_base64=True)`**: In-memory screenshot (0 disk bytes).
22. **`browser_ocr(image_path=None, session_id="default", filter_pattern=None)`**: Ultra-fast RapidOCR (ONNX) engine to extract text, phone numbers, prices, and bounding boxes in <100ms without heavy PyTorch.

### Group 3: Human-Like Semantic Interaction (6 Tools)
23. **`browser_click(target, observation_id=None, session_id="default", confirm_destructive=False)`**: Clicks tagged element (`@5`) or coordinates (`"500, 300"`).
24. **`browser_type(target, text, observation_id=None, clear=False, session_id="default")`**: Types text with 15–45ms human cadence.
25. **`browser_select(target, option, observation_id=None, session_id="default")`**: Selects dropdown option.
26. **`browser_scroll(direction="down", amount=500, target=None, session_id="default")`**: Sinusoidal smooth scrolling.
27. **`browser_press(key="Enter", session_id="default")`**: Dispatches keyboard keypress (`Enter`, `Tab`, `Escape`).
28. **`browser_extract_images(save_dir=None, return_base64=False, session_id="default", auto_optimize_platform=None)`**: Extracts original quality images directly from DOM/CDN. Set `auto_optimize_platform="INSTAGRAM"` or `"EMAIL"` to auto-compress on extraction!

### Group 4: Dynamic Waiting & Synchronization (3 Tools)
29. **`browser_wait(ms=1000, session_id="default")`**: Sleep in milliseconds.
30. **`browser_wait_for(target, state="visible", timeout_ms=15000, session_id="default")`**: Polls until element state is achieved.
31. **`browser_wait_idle(timeout_ms=10000, session_id="default")`**: Waits for network/DOM mutations to settle.

### Group 5: DevTools Telemetry & Logs (8 Tools)
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
45. **`optimize_media_for_platform(image_path, platform="INSTAGRAM", max_size_kb=200, output_format="WEBP", background_color="#0F172A", custom_width=None, custom_height=None)`**: Crops, canvas-fits, and compresses raw heavy ChatGPT or web images down to <=200KB for `INSTAGRAM` (1080x1350), `STORY` (1080x1920), `EMAIL` (650px), `BLOG` (1200x630), `THUMBNAIL` (1280x720), or `CUSTOM`.
46. **`optimize_media_batch(source_dir_or_pattern=None, platform="INSTAGRAM", max_size_kb=200, output_format="WEBP")`**: Batch-optimizes all newly extracted browser images or a folder in one call.
