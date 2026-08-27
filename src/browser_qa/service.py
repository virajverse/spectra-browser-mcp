"""Unified Core Service Layer powering both MCP Server and OpenAPI Bridge."""

import time
from typing import Any, Dict, List, Optional
from browser_qa.browser.controller import BrowserController
from browser_qa.collectors.lifecycle import EventBus
from browser_qa.models.action import ActionType
from browser_qa.models.event import BaseEvent
from browser_qa.models.session import BrowserMode, BrowserTarget, SessionStatus
from browser_qa.processors.correlator import Correlator
from browser_qa.processors.schema import SchemaTracker
from browser_qa.qa.findings import FindingEngine
from browser_qa.qa.performance import PerformanceEngine
from browser_qa.storage.memory import MemoryStore
from browser_qa.browser.extension_bridge import ExtensionBridge


class BrowserQAService:
    """Singleton-ready Unified Core Engine for Browser QA and Network Telemetry."""

    def __init__(self):
        # FIX BUG-02 (revised): Do NOT call sync_playwright().start() at __init__ time
        # because it fails inside asyncio loops (e.g. tests, FastAPI startup events).
        # Playwright is lazily initialized on first actual use via _get_playwright().
        self._shared_playwright = None  # lazy-init; populated on first use

        self.storage = MemoryStore()
        self.event_bus = EventBus(self.storage)
        self.controller = BrowserController(
            self.storage,
            self.event_bus,
            # Do NOT pass playwright_instance yet — it will be injected lazily
        )
        self.correlator = Correlator(self.storage)
        self.schema_tracker = SchemaTracker()
        self.perf_engine = PerformanceEngine(self.storage)
        # FIX BUG-07: Pass existing perf_engine to FindingEngine — no duplicate instance
        self.finding_engine = FindingEngine(self.storage, perf_engine=self.perf_engine)

        # Track stream cursors per session
        self._stream_cursors: Dict[str, int] = {}

        # Extension Bridge for direct live Chrome tab control without restarts
        self.extension_bridge = ExtensionBridge(self.storage)
        self.extension_bridge.start()

    def _get_playwright(self):
        """Lazily initialize and return shared Playwright instance.

        FIX BUG-02: One shared instance prevents dual sync_playwright() deadlocks.
        Lazy init avoids asyncio-loop error when service is imported in async contexts.
        """
        if self._shared_playwright is None:
            from playwright.sync_api import sync_playwright
            self._shared_playwright = sync_playwright().start()
            # Inject shared playwright into both controller and registration_mgr
            self.controller._playwright = self._shared_playwright
            self.controller.registration_mgr._playwright = self._shared_playwright
        return self._shared_playwright

    def extension_status(self) -> Dict[str, Any]:
        """Returns the connection and attachment status of the SpectraBrowser Chrome Extension."""
        connected = self.extension_bridge.is_connected()
        return {
            "extension_connected": connected,
            "websocket_bridge_url": f"ws://{self.extension_bridge.host}:{self.extension_bridge.port}/extension_ws",
            "instructions": (
                "Chrome Extension is connected! Tool calls will directly control your live Chrome tab."
                if connected else
                "Chrome Extension is waiting. Open Chrome and load unpacked from spectra-browser-mcp/extension."
            )
        }

    # --- Browser Registration & Personal Chrome ---
    def browser_register_start(
        self,
        display_name: str = "Personal Chrome",
        cdp_url: Optional[str] = None,
        port: int = 9222,
        profile_identifier: Optional[str] = None,
        chrome_path: Optional[str] = None,
        auto_launch: bool = True,
        auto_confirm: bool = True
    ) -> Dict[str, Any]:
        """Initiates explicit personal Chrome browser registration, auto-launches Chrome, and connects."""
        return self.controller.registration_mgr.start_registration(
            display_name=display_name,
            cdp_url=cdp_url,
            port=port,
            profile_identifier=profile_identifier,
            chrome_path=chrome_path,
            auto_launch=auto_launch,
            auto_confirm=auto_confirm
        )

    def browser_register_confirm(self, registration_id: str) -> Dict[str, Any]:
        """Finalizes registration after user explicitly confirms and authorizes Chrome connection."""
        return self.controller.registration_mgr.confirm_registration(registration_id)

    def browser_register_status(self, registration_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves safe registration status and connection state."""
        return self.controller.registration_mgr.get_status(registration_id)

    def browser_register_revoke(self, registration_id: str) -> Dict[str, Any]:
        """Explicitly revokes registered browser and releases automation/telemetry."""
        return self.controller.registration_mgr.revoke_registration(registration_id)

    def browser_register_list(self) -> List[Dict[str, Any]]:
        """Lists all known browser registrations."""
        return self.controller.registration_mgr.list_registrations()

    def browser_tabs(self, session_id: str = "default") -> List[Dict[str, Any]]:
        """Lists open tabs in the browser context with safe metadata."""
        return self.controller.list_tabs(session_id)

    def browser_select_tab(self, tab_id: str, session_id: str = "default") -> Dict[str, Any]:
        """Switches the QA session active page to the designated tab."""
        return self.controller.select_tab(session_id, tab_id)

    # --- Session & Authentication ---
    def session_create(
        self,
        session_id: str = "default",
        browser_mode: str = "headed",
        browser_target: str = "managed",
        registration_id: Optional[str] = None,
        tab_id: Optional[str] = None,
        target_origin: Optional[str] = None,
        allowed_origins: Optional[List[str]] = None,
        profile_id: Optional[str] = None
    ) -> Dict[str, Any]:
        mode = BrowserMode.HEADED if browser_mode.lower() == "headed" else BrowserMode.HEADLESS
        target = BrowserTarget.REGISTERED if browser_target.lower() == "registered" else BrowserTarget.MANAGED

        config = self.controller.start_session(
            session_id=session_id,
            browser_mode=mode,
            browser_target=target,
            registration_id=registration_id,
            tab_id=tab_id,
            target_origin=target_origin,
            allowed_origins=allowed_origins,
            profile_id=profile_id
        )
        return {
            "session_id": config.session_id,
            "state": "authenticating" if mode == BrowserMode.HEADED else "active",
            "browser_mode": config.browser_mode.value,
            "browser_target": config.browser_target.value,
            "registration_id": config.registration_id,
            "tab_id": config.tab_id,
            "target_origin": config.target_origin,
            "allowed_origins": config.allowed_origins,
            "profile_id": config.profile_id
        }

    def session_status(self, session_id: str = "default") -> Dict[str, Any]:
        config = self.controller.session_mgr.get_session(session_id)
        if not config:
            return {"session_id": session_id, "state": "closed", "error": "Session not initialized"}

        page = self.controller._pages.get(session_id)
        current_url = page.url if page else ""
        # FIX BUG-03: page.title() can throw 'Target closed' if page context was closed
        try:
            title = page.title() if page else ""
        except Exception:
            title = ""

        txs = self.storage.list_transactions(session_id, limit=500)
        anomalies = self.finding_engine.detector.scan(session_id)
        findings = self.storage.list_findings(session_id)

        status = SessionStatus(
            session_id=session_id,
            state=self.controller.session_mgr.get_state(session_id),
            browser_mode=config.browser_mode,
            browser_target=config.browser_target,
            registration_id=config.registration_id,
            tab_id=config.tab_id,
            current_url=current_url,
            title=title,
            target_origin=config.target_origin,
            allowed_origins=config.allowed_origins,
            pause_reason=self.controller.session_mgr.get_pause_reason(session_id),
            created_at=self.controller.session_mgr._created_at.get(session_id, time.time()),
            total_transactions=len(txs),
            anomalies_count=len(anomalies),
            findings_count=len(findings)
        )
        return status.model_dump()

    def session_pause(self, session_id: str = "default", reason: str = "User authentication required") -> Dict[str, Any]:
        success = self.controller.session_mgr.pause_session(session_id, reason)
        return {
            "session_id": session_id,
            "paused": success,
            "reason": reason,
            "instructions": "Automation is paused. Complete manual login, 2FA, or CAPTCHA in the visible browser window, then call session_resume()."
        }

    def session_ask_human(
        self,
        question: str,
        options: Optional[List[str]] = None,
        context_summary: Optional[str] = None,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """Pauses automation to ask user for instructions, choices, or confirmation before proceeding."""
        self.controller.session_mgr.pause_session(session_id, f"Human Decision: {question}")
        return {
            "session_id": session_id,
            "status": "awaiting_human_decision",
            "question": question,
            "options": options or ["Yes, proceed", "No, cancel"],
            "context_summary": context_summary or "",
            "instructions": (
                "Automation is paused. Display this question clearly to the user. "
                "Once the user gives an answer, call session_resume(user_decision='...') to continue."
            )
        }

    def session_resume(self, session_id: str = "default", user_decision: Optional[str] = None) -> Dict[str, Any]:
        success = self.controller.session_mgr.resume_session(session_id)
        return {
            "session_id": session_id,
            "resumed": success,
            "state": "active",
            "user_decision": user_decision,
            "message": f"User confirmed decision: {user_decision or 'Proceed'}. Agent automation resumed."
        }

    def session_save(self, session_id: str = "default", profile_id: Optional[str] = None) -> Dict[str, Any]:
        path = self.controller.save_storage_state(session_id, profile_id)
        return {
            "session_id": session_id,
            "profile_id": profile_id or session_id,
            "storage_state_path": path,
            "message": "Browser profile cookies and localStorage persisted successfully."
        }

    def session_close(self, session_id: str = "default") -> Dict[str, Any]:
        self.controller.close_session(session_id)
        return {"session_id": session_id, "state": "closed"}

    # --- Browser Control & Action Execution ---
    def browser_navigate(self, url: str, session_id: str = "default") -> Dict[str, Any]:
        if self.extension_bridge.is_connected():
            res = self.extension_bridge.navigate(url)
            return {"success": True, "message": f"Navigated via Chrome Extension to {url}", "current_url": res.get("url", url)}
        success, msg = self.controller.navigate(session_id, url)
        return {"success": success, "message": msg, "current_url": url if success else ""}

    def browser_click(
        self,
        target: str,
        observation_id: Optional[str] = None,
        session_id: str = "default",
        confirm_destructive: bool = False
    ) -> Dict[str, Any]:
        if self.extension_bridge.is_connected():
            res = self.extension_bridge.click(target)
            return {
                "success": res.get("success", False),
                "action": "click",
                "target": target,
                "message": res.get("error") or f"Clicked '{target}' via Chrome Extension"
            }
        page = self.controller.get_page(session_id)
        url_before = page.url
        rec, msg = self.controller.execute_action(
            session_id=session_id,
            action_type=ActionType.CLICK,
            target=target,
            observation_id=observation_id,
            confirm_destructive=confirm_destructive
        )
        url_after = page.url
        # Correlate flow
        flow = self.correlator.correlate(
            session_id=session_id,
            action=rec,
            page_url_before=url_before,
            page_url_after=url_after
        )
        return {
            "action_id": rec.action_id,
            "status": rec.status,
            "message": msg,
            "flow_id": flow.flow_id,
            "correlated_requests": len(flow.network_transactions),
            "anomalies_detected": flow.detected_anomalies
        }

    def browser_type(
        self,
        target: str,
        text: str,
        observation_id: Optional[str] = None,
        clear: bool = False,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        if self.extension_bridge.is_connected():
            res = self.extension_bridge.type(target, text)
            return {
                "success": res.get("success", False),
                "action": "type",
                "target": target,
                "message": res.get("error") or f"Typed into '{target}' via Chrome Extension"
            }
        rec, msg = self.controller.execute_action(
            session_id=session_id,
            action_type=ActionType.TYPE,
            target=target,
            value=text,
            observation_id=observation_id
        )
        return {"action_id": rec.action_id, "status": rec.status, "message": msg}

    def browser_select(
        self,
        target: str,
        option: str,
        observation_id: Optional[str] = None,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        rec, msg = self.controller.execute_action(
            session_id=session_id,
            action_type=ActionType.SELECT,
            target=target,
            value=option,
            observation_id=observation_id
        )
        return {"action_id": rec.action_id, "status": rec.status, "message": msg}

    def browser_scroll(
        self,
        direction: str = "down",
        amount: int = 500,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        rec, msg = self.controller.execute_action(
            session_id=session_id,
            action_type=ActionType.SCROLL,
            value=direction
        )
        return {"status": rec.status, "message": msg}

    def browser_press(self, key: str = "Enter", session_id: str = "default") -> Dict[str, Any]:
        if self.extension_bridge.is_connected():
            res = self.extension_bridge.press_key(key)
            return {"status": "success", "message": f"Pressed key '{key}' via Chrome Extension"}
        rec, msg = self.controller.execute_action(
            session_id=session_id,
            action_type=ActionType.PRESS,
            value=key
        )
        return {"status": rec.status, "message": msg}

    def browser_extract_images(self, save_dir: Optional[str] = None) -> Dict[str, Any]:
        """Extracts and saves all full-resolution images from the active page in original quality without screenshots."""
        import base64
        from browser_qa.config import SCREENSHOTS_DIR
        from pathlib import Path
        if not self.extension_bridge.is_connected():
            raise ConnectionError("Chrome Extension must be connected to extract images.")

        images = self.extension_bridge.extract_images()
        saved = []
        target_dir = Path(save_dir) if save_dir else (SCREENSHOTS_DIR / "extracted_images")
        target_dir.mkdir(parents=True, exist_ok=True)

        for idx, img in enumerate(images):
            b64 = img.get("base64")
            if b64 and "," in b64:
                header, b64_data = b64.split(",", 1)
                ext = "png" if "png" in header else "webp" if "webp" in header else "jpg"
                img_bytes = base64.b64decode(b64_data)
                filepath = target_dir / f"image_{int(time.time())}_{idx+1}.{ext}"
                with open(filepath, "wb") as f:
                    f.write(img_bytes)
                posix_path = filepath.as_posix()
                saved.append({
                    "index": idx + 1,
                    "file_path": str(filepath),
                    "normalized_path": posix_path,
                    "markdown_link": f"![Extracted Image {idx+1}](file:///{posix_path})",
                    "width": img.get("naturalWidth"),
                    "height": img.get("naturalHeight"),
                    "size_bytes": len(img_bytes),
                    "size_kb": round(len(img_bytes) / 1024, 2),
                    "format": ext.upper(),
                    "alt_text": img.get("alt", ""),
                    "src_url": img.get("src", ""),
                    "supabase_ready": True,
                    "taliyo_action": "Pass this 'file_path' directly to taliyo-blog-engine's 'upload_blog_image' or 'create_blog_post' to auto-host on Supabase Storage!"
                })

        return {
            "status": "success",
            "total_extracted": len(saved),
            "images": saved,
            "supabase_ready": True,
            "message": f"Successfully extracted {len(saved)} full-resolution original image(s) from the page. Ready for Supabase upload and Taliyo Blog insertion."
        }

    def browser_wait(self, ms: int = 1000, session_id: str = "default") -> Dict[str, Any]:
        rec, msg = self.controller.execute_action(
            session_id=session_id,
            action_type=ActionType.WAIT,
            value=str(ms)
        )
        return {"status": rec.status, "message": msg}

    def browser_wait_for(
        self,
        target: str,
        state: str = "visible",
        timeout_ms: int = 15000,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """Dynamically waits for an element (@ref, text, or selector) to become visible/hidden/attached."""
        success, msg = self.controller.wait_for(session_id, target, state, timeout_ms)
        return {"success": success, "target": target, "state": state, "message": msg}

    def browser_wait_idle(self, timeout_ms: int = 10000, session_id: str = "default") -> Dict[str, Any]:
        """Waits for network requests to settle and DOM mutations to finish."""
        success, msg = self.controller.wait_idle(session_id, timeout_ms)
        return {"success": success, "message": msg}

    def browser_screenshot(self, session_id: str = "default", full_page: bool = False) -> Dict[str, Any]:
        if self.extension_bridge.is_connected():
            path = self.extension_bridge.screenshot(session_id)
            return {
                "status": "success",
                "message": "Screenshot captured via Chrome Extension",
                "screenshot_path": path
            }
        rec, msg = self.controller.execute_action(
            session_id=session_id,
            action_type=ActionType.SCREENSHOT
        )
        return {
            "status": rec.status,
            "message": msg,
            "screenshot_path": rec.metadata.get("screenshot_path")
        }

    # --- Page Observation ---
    def page_inspect(self, session_id: str = "default") -> Dict[str, Any]:
        if self.extension_bridge.is_connected():
            obs = self.extension_bridge.inspect_page(session_id)
            return {
                "observation_id": obs.observation_id,
                "session_id": obs.session_id,
                "url": obs.url,
                "title": obs.title,
                "headings": obs.headings,
                "interactive_elements": [e.model_dump() for e in obs.interactive_elements],
                "forms": [f.model_dump() for f in obs.forms],
                "screen_diagnosis": obs.screen_diagnosis
            }
        obs = self.controller.inspect_page(session_id)
        return {
            "observation_id": obs.observation_id,
            "session_id": obs.session_id,
            "url": obs.url,
            "title": obs.title,
            "headings": obs.headings,
            "interactive_elements": [e.model_dump() for e in obs.interactive_elements],
            "forms": [f.model_dump() for f in obs.forms],
            "visible_text_summary": obs.visible_text_summary,
            "screen_diagnosis": obs.screen_diagnosis
        }

    def page_forms(self, session_id: str = "default") -> List[Dict[str, Any]]:
        obs = self.controller.page_observer.get_current_observation(session_id)
        if not obs:
            obs = self.controller.inspect_page(session_id)
        return [f.model_dump() for f in obs.forms]

    def page_text(self, session_id: str = "default", max_chars: int = 3000) -> Dict[str, Any]:
        obs = self.controller.page_observer.get_current_observation(session_id)
        if not obs:
            obs = self.controller.inspect_page(session_id)
        return {
            "url": obs.url,
            "title": obs.title,
            "text": obs.visible_text_summary[:max_chars]
        }

    # --- Network & Stream Telemetry ---
    def network_stream(
        self,
        session_id: str = "default",
        filter_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Reads latest events from per-session ring buffer advancing the cursor."""
        # FIX BUG-05: Read full buffer (not capped at 100) so cursor tracks correctly
        all_events = self.storage.get_events(session_id, limit=self.storage.max_buffer_size)
        cursor = self._stream_cursors.get(session_id, 0)

        # Slice events after cursor
        new_events = all_events[cursor:]
        self._stream_cursors[session_id] = len(all_events)  # absolute position in full buffer

        if filter_type:
            new_events = [e for e in new_events if e.event_type.value == filter_type.lower()]

        return [e.to_dict() for e in new_events[-limit:]]

    def network_list(
        self,
        session_id: str = "default",
        filter_type: Optional[str] = None,
        status_code: Optional[int] = None,
        errors_only: bool = False,
        search_query: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Lists captured HTTP transactions mirroring Chrome DevTools Network table columns."""
        txs = self.storage.list_transactions(
            session_id=session_id,
            limit=limit,
            status_code=status_code,
            filter_type=filter_type,
            errors_only=errors_only,
            search_query=search_query
        )
        return [
            {
                "name": t.name or t.request.url.split("/")[-1] or "/",
                "status": t.response.status if t.response else (0 if not t.failure_reason else 500),
                "type": t.request.resource_type,
                "initiator": t.request.initiator or "Other",
                "size": t.size_formatted,
                "time": t.time_formatted,
                "url": t.request.url,
                "method": t.request.method,
                "request_id": t.request_id,
                "is_cached": t.from_cache,
                "is_failed": bool(t.failure_reason or (t.response and t.response.status >= 400))
            }
            for t in txs
        ]

    def network_get(
        self,
        request_id: str,
        session_id: str = "default",
        include_request_body: bool = True,
        include_response_body: bool = True,
        max_body_bytes: int = 100000
    ) -> Optional[Dict[str, Any]]:
        """Retrieves full request details matching Chrome DevTools tabs (Headers, Preview, Response, Initiator, Timing)."""
        tx = self.storage.get_transaction(session_id, request_id)
        if not tx:
            return None

        # 1. Headers Tab (General, Response Headers, Request Headers)
        headers_tab = {
            "general": {
                "request_url": tx.request.url,
                "request_method": tx.request.method,
                "status_code": f"{tx.response.status} {tx.response.status_text}" if tx.response else (tx.failure_reason or "Pending"),
                "referrer_policy": tx.request.headers.get("referer", "strict-origin-when-cross-origin")
            },
            "response_headers": tx.response.headers if tx.response else {},
            "request_headers": tx.request.headers
        }

        # 2. Timing Tab (Waterfall breakdown)
        timing_tab = {
            "queued_ms": tx.timing.queued_ms,
            "stalled_ms": tx.timing.stalled_ms,
            "dns_ms": tx.timing.dns_ms,
            "initial_connection_ms": tx.timing.connect_ms,
            "ssl_ms": tx.timing.tls_ms,
            "request_sent_ms": tx.timing.request_ms,
            "ttfb_ms": tx.timing.ttfb_ms,
            "download_ms": tx.timing.download_ms,
            "total_ms": tx.timing.total_ms,
            "formatted": tx.time_formatted
        }

        # 3. Initiator Tab
        initiator_tab = {
            "initiator": tx.request.initiator or "Other",
            "type": tx.request.initiator_type
        }

        # 4. Preview / Response Tab
        body_content = tx.response.body if (tx.response and include_response_body) else None
        preview_data = None
        if body_content:
            import json
            try:
                preview_data = json.loads(body_content)
            except Exception:
                preview_data = body_content[:500]

        return {
            "name": tx.name,
            "request_id": tx.request_id,
            "headers": headers_tab,
            "preview": preview_data,
            "response": body_content[:max_body_bytes] if body_content else None,
            "initiator": initiator_tab,
            "timing": timing_tab,
            "size": tx.size_formatted,
            "is_cached": tx.from_cache
        }

    def network_summary(self, session_id: str = "default") -> Dict[str, Any]:
        """Returns complete DevTools bottom status bar and performance metrics."""
        txs = self.storage.list_transactions(session_id, limit=self.storage.max_buffer_size)

        total_requests = len(txs)
        total_transferred_bytes = 0
        total_resource_bytes = 0
        status_counts = {}
        type_counts = {}
        failed_list = []
        min_start = float("inf")
        max_end = 0.0

        for t in txs:
            min_start = min(min_start, t.timestamp)
            max_end = max(max_end, t.timestamp + (t.timing.total_ms / 1000.0))

            # Status breakdown
            st = t.response.status if t.response else (500 if t.failure_reason else 0)
            st_key = str(st)
            status_counts[st_key] = status_counts.get(st_key, 0) + 1

            if st >= 400 or t.failure_reason:
                failed_list.append({
                    "name": t.name,
                    "status": st,
                    "url": t.request.url,
                    "error": t.failure_reason or f"HTTP {st}"
                })

            # Type breakdown
            r_type = t.request.resource_type or "other"
            type_counts[r_type] = type_counts.get(r_type, 0) + 1

            # Size calculation
            if t.response:
                total_transferred_bytes += t.response.encoded_data_length
                total_resource_bytes += max(t.response.size, t.response.encoded_data_length)

        finish_time_s = round(max(0.0, max_end - min_start), 2) if total_requests > 0 else 0.0

        def _fmt_size(b: int) -> str:
            if b >= 1024 * 1024:
                return f"{round(b / (1024 * 1024), 1)} MB"
            return f"{round(b / 1024, 1)} kB"

        # Bottom summary bar formatted like Chrome DevTools
        return {
            "devtools_summary_bar": f"{total_requests} requests | {_fmt_size(total_transferred_bytes)} transferred | {_fmt_size(total_resource_bytes)} resources | Finish: {finish_time_s} s",
            "total_requests": total_requests,
            "transferred": _fmt_size(total_transferred_bytes),
            "resources": _fmt_size(total_resource_bytes),
            "finish_time_seconds": finish_time_s,
            "status_breakdown": status_counts,
            "type_breakdown": type_counts,
            "failed_requests_count": len(failed_list),
            "failed_requests": failed_list[:20]
        }

    def network_clear(self, session_id: str = "default") -> Dict[str, Any]:
        self.storage.clear_transactions(session_id)
        self._stream_cursors[session_id] = 0
        return {"session_id": session_id, "cleared": True}

    # --- Console & WebSocket Telemetry ---
    def console_list(
        self,
        session_id: str = "default",
        min_level: str = "info",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        events = self.storage.list_console_events(session_id, limit=limit, min_level=min_level)
        return [c.model_dump() for c in events]

    def websocket_list(self, session_id: str = "default") -> List[Dict[str, Any]]:
        collector = self.controller._ws_collectors.get(session_id)
        if not collector:
            return []
        return [ws.model_dump() for ws in collector.list_websockets()]

    def sse_list(self, session_id: str = "default") -> List[Dict[str, Any]]:
        collector = self.controller._ws_collectors.get(session_id)
        if not collector:
            return []
        return [s.model_dump() for s in collector.list_sse_streams()]

    # --- QA Intelligence & Reporting ---
    def qa_anomalies(self, session_id: str = "default") -> List[Dict[str, Any]]:
        anomalies = self.finding_engine.detector.scan(session_id)
        return [a.model_dump() for a in anomalies]

    def qa_correlate(self, action_id: Optional[str] = None, session_id: str = "default") -> List[Dict[str, Any]]:
        flows = self.storage.list_flows(session_id, limit=20)
        if action_id:
            flows = [f for f in flows if f.action.action_id == action_id]
        return [f.model_dump() for f in flows]

    def qa_report(self, session_id: str = "default", format_type: str = "markdown") -> str:
        return self.finding_engine.generate_report(session_id, format_type)

    # --- System Housekeeping & Storage Purge ---
    def storage_inspect(self) -> Dict[str, Any]:
        """Scans and itemizes all temporary storage consumed by MCPs (screenshots, caches, dumps)."""
        from pathlib import Path
        import sys
        root = Path(__file__).resolve().parent.parent.parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        import clean_mcp_storage
        return clean_mcp_storage.scan_mcp_storage()

    def storage_clean(self, dry_run: bool = False) -> Dict[str, Any]:
        """Safely wipes temporary screenshots, compiler bytecode, and scraper caches to free laptop disk space."""
        from pathlib import Path
        import sys
        root = Path(__file__).resolve().parent.parent.parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        import clean_mcp_storage
        return clean_mcp_storage.purge_mcp_storage(dry_run=dry_run)
