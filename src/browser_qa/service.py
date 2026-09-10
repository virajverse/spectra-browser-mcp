"""Unified 100% Extension-Native Service Layer powering SpectraBrowser MCP.

Controls the user's live Chrome browser directly via the Spectra Chrome Extension
WebSocket Bridge without launching isolated or headless browser instances.
"""

import base64
import hashlib
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


from browser_qa.browser.extension_bridge import ExtensionBridge
from browser_qa.collectors.lifecycle import EventBus
from browser_qa.config import SCREENSHOTS_DIR
from browser_qa.models.action import ActionType
from browser_qa.models.event import BaseEvent
from browser_qa.models.session import BrowserMode, BrowserTarget, SessionStatus
from browser_qa.processors.correlator import Correlator
from browser_qa.processors.media_optimizer import optimize_image, optimize_batch
from browser_qa.processors.schema import SchemaTracker
from browser_qa.qa.findings import FindingEngine
from browser_qa.qa.performance import PerformanceEngine
from browser_qa.storage.memory import MemoryStore


class BrowserQAService:
    """Singleton-ready Core Engine for Extension-Native Browser Control and QA Intelligence."""

    _instance: Optional["BrowserQAService"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.storage = MemoryStore()
        self.event_bus = EventBus(self.storage)
        self.correlator = Correlator(self.storage)
        self.schema_tracker = SchemaTracker()
        self.perf_engine = PerformanceEngine(self.storage)
        self.finding_engine = FindingEngine(self.storage, perf_engine=self.perf_engine)

        # Track stream cursors per session
        self._stream_cursors: Dict[str, int] = {}
        self._session_states: Dict[str, str] = {}
        self._pause_reasons: Dict[str, str] = {}
        self._created_at: Dict[str, float] = {}

        # Extension Bridge for direct live Chrome tab control without restarts
        self.extension_bridge = ExtensionBridge(self.storage)
        self.extension_bridge.start()


    def _require_extension(self):
        """Ensures the Chrome extension is connected before executing actions."""
        if not self.extension_bridge.is_connected():
            import os
            hub_url = os.getenv("SPECTRA_HUB_URL", os.getenv("PUBLIC_URL", "http://127.0.0.1:8002")).strip().rstrip("/")
            raise ConnectionError(
                "⚠️ SpectraBrowser Chrome Extension is NOT connected!\n"
                f"👉 Setup Hub: {hub_url}/install\n"
                f"👉 Download ZIP: {hub_url}/download-extension\n"
                "Quick Steps: 1. Download & Unzip the extension. "
                "2. Open Chrome -> chrome://extensions -> Toggle 'Developer mode' ON. "
                "3. Click 'Load unpacked' -> Select the extracted extension folder, and keep that Chrome profile open!"
            )


    # ==========================================
    # 0. Extension & Browser Registration Status
    # ==========================================

    def extension_status(self) -> Dict[str, Any]:
        """Returns the connection and attachment status of the SpectraBrowser Chrome Extension."""
        connected = self.extension_bridge.is_connected()
        return {
            "extension_connected": connected,
            "mode": "extension_native",
            "download_url": "https://mcp3.taliyotechnologies.com/download-extension",
            "setup_hub": "https://mcp3.taliyotechnologies.com",
            "instructions": (
                "🟢 Chrome Extension is CONNECTED! Browser commands will execute in your live Chrome profile tabs."
                if connected else
                "⚠️ Chrome Extension NOT connected! Please visit https://mcp3.taliyotechnologies.com to download & load unpacked the extension in Chrome."
            )
        }

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
        """Extension-native registration confirmation."""
        connected = self.extension_bridge.is_connected()
        return {
            "registration_id": "reg_personal_chrome",
            "status": "connected" if connected else "waiting_for_extension",
            "display_name": display_name,
            "mode": "extension_bridge",
            "extension_connected": connected,
            "instructions": (
                "SpectraBrowser is operating in 100% Extension-Native mode. No separate browser launch required."
                if connected else
                "Please enable SpectraBrowser MCP Bridge in chrome://extensions to connect."
            )
        }

    def browser_register_confirm(self, registration_id: str) -> Dict[str, Any]:
        return {
            "registration_id": registration_id,
            "status": "connected",
            "message": "Chrome Extension is actively controlling your personal browser tabs."
        }

    def browser_register_status(self, registration_id: Optional[str] = None) -> Dict[str, Any]:
        connected = self.extension_bridge.is_connected()
        return {
            "registration_id": registration_id or "reg_personal_chrome",
            "status": "connected" if connected else "disconnected",
            "mode": "extension_native",
            "extension_connected": connected
        }

    def browser_register_revoke(self, registration_id: str) -> Dict[str, Any]:
        return {"registration_id": registration_id, "status": "revoked", "success": True}


    def browser_register_list(self) -> List[Dict[str, Any]]:
        connected = self.extension_bridge.is_connected()
        return [{
            "registration_id": "reg_personal_chrome",
            "display_name": "Personal Chrome (Extension Bridge)",
            "status": "connected" if connected else "disconnected",
            "mode": "extension_native"
        }]

    def browser_tabs(self, session_id: str = "default") -> List[Dict[str, Any]]:
        """Lists open tabs in user's Chrome."""
        self._require_extension()
        return self.extension_bridge.list_tabs()

    def browser_select_tab(self, tab_id: str, session_id: str = "default") -> Dict[str, Any]:
        """Switches active focus to designated tab."""
        self._require_extension()
        t_id = int(tab_id) if str(tab_id).isdigit() else None
        res = self.extension_bridge.attach_tab(t_id)
        return {"success": True, "active_tab_id": tab_id, "details": res}

    # ==========================================
    # 1. Session Management
    # ==========================================

    def session_create(
        self,
        session_id: str = "default",
        browser_mode: str = "headed",
        browser_target: str = "extension",
        registration_id: Optional[str] = None,
        tab_id: Optional[str] = None,
        target_origin: Optional[str] = None,
        allowed_origins: Optional[List[str]] = None,
        profile_id: Optional[str] = None
    ) -> Dict[str, Any]:
        self._session_states[session_id] = "active"
        self._created_at[session_id] = time.time()
        connected = self.extension_bridge.is_connected()
        return {
            "session_id": session_id,
            "state": "active" if connected else "waiting_for_extension",
            "browser_mode": "headed",
            "browser_target": "extension_bridge",
            "extension_connected": connected,
            "message": "Session initialized directly in user's personal Chrome via Extension Bridge."
        }

    def session_status(self, session_id: str = "default") -> Dict[str, Any]:
        connected = self.extension_bridge.is_connected()
        txs = self.storage.list_transactions(session_id, limit=500)
        anomalies = self.finding_engine.detector.scan(session_id)
        findings = self.storage.list_findings(session_id)

        obs_url = ""
        obs_title = ""
        if connected:
            try:
                obs = self.extension_bridge.inspect_page(session_id)
                obs_url = obs.url
                obs_title = obs.title
            except Exception:
                pass

        return {
            "session_id": session_id,
            "state": self._session_states.get(session_id, "active" if connected else "disconnected"),
            "browser_mode": "headed",
            "browser_target": "extension_bridge",
            "extension_connected": connected,
            "current_url": obs_url,
            "title": obs_title,
            "pause_reason": self._pause_reasons.get(session_id),
            "created_at": self._created_at.get(session_id, time.time()),
            "total_transactions": len(txs),
            "anomalies_count": len(anomalies),
            "findings_count": len(findings)
        }

    def session_pause(self, session_id: str = "default", reason: str = "User authentication required") -> Dict[str, Any]:
        self._session_states[session_id] = "paused"
        self._pause_reasons[session_id] = reason
        return {
            "session_id": session_id,
            "paused": True,
            "reason": reason,
            "instructions": "Automation is paused. Complete manual actions in your Chrome tab, then call session_resume()."
        }

    def session_ask_human(
        self,
        question: str,
        options: Optional[List[str]] = None,
        context_summary: Optional[str] = None,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        self._session_states[session_id] = "paused"
        self._pause_reasons[session_id] = f"Human Decision: {question}"
        return {
            "session_id": session_id,
            "status": "awaiting_human_decision",
            "question": question,
            "options": options or ["Yes, proceed", "No, cancel"],
            "context_summary": context_summary or "",
            "instructions": "Automation is paused for user decision. Call session_resume(user_decision='...') to continue."
        }

    def session_resume(self, session_id: str = "default", user_decision: Optional[str] = None) -> Dict[str, Any]:
        self._session_states[session_id] = "active"
        self._pause_reasons.pop(session_id, None)
        return {
            "session_id": session_id,
            "resumed": True,
            "state": "active",
            "user_decision": user_decision,
            "message": f"User confirmed decision: {user_decision or 'Proceed'}. Automation resumed."
        }

    def session_save(self, session_id: str = "default", profile_id: Optional[str] = None) -> Dict[str, Any]:
        return {
            "session_id": session_id,
            "profile_id": profile_id or session_id,
            "message": "Chrome Extension operates directly on your live Chrome profile — state is automatically persisted in your browser."
        }

    def session_close(self, session_id: str = "default") -> Dict[str, Any]:
        self._session_states[session_id] = "closed"
        return {"session_id": session_id, "state": "closed"}

    # ==========================================
    # 2. Browser Navigation & Safe Interaction
    # ==========================================

    def browser_navigate(self, url: str, session_id: str = "default") -> Dict[str, Any]:
        """Navigates active Chrome tab directly."""
        self._require_extension()
        res = self.extension_bridge.navigate(url)
        return {"success": True, "message": f"Navigated via Chrome Extension to {url}", "current_url": res.get("url", url)}

    def browser_reload(self, ignore_cache: bool = True, session_id: str = "default") -> Dict[str, Any]:
        """Reloads the active tab with DevTools Network monitoring enabled to capture complete traffic from start."""
        self._require_extension()
        res = self.extension_bridge.reload(ignore_cache=ignore_cache)
        return {
            "success": True,
            "message": f"Reloaded active tab with DevTools Network monitoring active (ignore_cache={ignore_cache})",
            "url": res.get("url", ""),
            "title": res.get("title", ""),
            "details": res
        }

    def browser_click(
        self,
        target: str,
        observation_id: Optional[str] = None,
        session_id: str = "default",
        confirm_destructive: bool = False
    ) -> Dict[str, Any]:
        """Clicks an element by @ref, CSS selector, or accessible name with synthetic pointer events."""
        self._require_extension()
        res = self.extension_bridge.click(target)
        return {
            "success": res.get("success", False),
            "action": "click",
            "target": target,
            "message": res.get("error") or f"Clicked '{target}' via Chrome Extension",
            "details": res
        }

    def browser_type(
        self,
        target: str,
        text: str,
        observation_id: Optional[str] = None,
        clear: bool = False,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """Fills/types text with React/Vue input setter and contenteditable support."""
        self._require_extension()
        res = self.extension_bridge.type(target, text, clear=clear)
        return {
            "success": res.get("success", False),
            "action": "type",
            "target": target,
            "message": res.get("error") or f"Typed into '{target}' via Chrome Extension",
            "details": res
        }

    def browser_select(
        self,
        target: str,
        option: str,
        observation_id: Optional[str] = None,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """Selects dropdown option."""
        self._require_extension()
        res = self.extension_bridge.select(target, option)
        return {"success": res.get("success", True), "target": target, "option": option, "details": res}

    def browser_scroll(
        self,
        direction: str = "down",
        amount: int = 500,
        target: Optional[str] = None,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """Scrolls window, scrollable containers (e.g. ChatGPT thread), or target element into view."""
        self._require_extension()
        res = self.extension_bridge.scroll(direction=direction, amount=amount, target=target)
        return {"status": "success", "message": f"Scrolled {direction} by {amount}px via Chrome Extension", "details": res}

    def browser_press(self, key: str = "Enter", session_id: str = "default") -> Dict[str, Any]:
        """Simulates keyboard key press (Enter, Escape, Tab, Arrow keys)."""
        self._require_extension()
        res = self.extension_bridge.press_key(key)
        return {"status": "success", "message": f"Pressed key '{key}' via Chrome Extension", "details": res}

    def browser_wait(self, ms: int = 1000, session_id: str = "default") -> Dict[str, Any]:
        """Waits for specified milliseconds."""
        time.sleep(max(0.05, ms / 1000.0))
        return {"status": "success", "waited_ms": ms}

    def browser_wait_for(
        self,
        target: str,
        state: str = "visible",
        timeout_ms: int = 15000,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """Dynamically polls until target element reaches state (visible, hidden, attached)."""
        self._require_extension()
        res = self.extension_bridge.wait_for(target, state=state, timeout_ms=timeout_ms)
        return {"success": res.get("success", False), "target": target, "state": state, "details": res}

    def browser_wait_idle(self, timeout_ms: int = 10000, session_id: str = "default") -> Dict[str, Any]:
        """Waits for DOM mutations to settle."""
        self._require_extension()
        res = self.extension_bridge.wait_idle(timeout_ms=timeout_ms)
        return {"success": res.get("success", True), "details": res}

    def browser_screenshot(
        self,
        session_id: str = "default",
        full_page: bool = False,
        save_to_disk: bool = False,
        return_base64: bool = True
    ) -> Dict[str, Any]:
        """Captures screenshot with Pure In-Memory Ephemeral Stream (0 disk bytes used by default).
        
        Args:
            session_id: Browser session identifier
            full_page: Full page capture flag
            save_to_disk: If True, saves to disk with a Rolling Ring Buffer (Max 2 files). Defaults to False (0 disk usage).
            return_base64: If True, returns in-memory base64 string for multimodal visual analysis. Defaults to True.
        """
        self._require_extension()
        return self.extension_bridge.screenshot(
            session_id=session_id,
            save_to_disk=save_to_disk,
            return_base64=return_base64
        )

    def browser_extract_images(
        self,
        save_dir: Optional[str] = None,
        return_base64: bool = False,
        session_id: str = "default",
        auto_optimize_platform: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extracts and saves all full-resolution images from the active page with SHA-256 deduplication."""
        self._require_extension()
        images = self.extension_bridge.extract_images()

        saved = []
        target_dir = Path(save_dir) if save_dir else (SCREENSHOTS_DIR / "extracted_images")
        target_dir.mkdir(parents=True, exist_ok=True)

        seen_hashes = set()
        seen_urls = set()

        for ef in target_dir.glob("*.*"):
            if ef.is_file():
                try:
                    with open(ef, "rb") as f:
                        seen_hashes.add(hashlib.sha256(f.read()).hexdigest())
                except Exception:
                    pass

        for idx, img in enumerate(images or []):
            b64 = img.get("base64")
            src_url = img.get("src", "")

            # URL deduplication
            clean_url = src_url.split("&sig=")[0] if "&sig=" in src_url else src_url
            if clean_url and clean_url in seen_urls:
                continue
            if clean_url:
                seen_urls.add(clean_url)

            img_bytes = None
            ext = "png"

            # Method A: Base64 decode
            if b64 and "," in b64:
                try:
                    header, b64_data = b64.split(",", 1)
                    ext = "png" if "png" in header else "webp" if "webp" in header else "jpg"
                    img_bytes = base64.b64decode(b64_data)
                except Exception:
                    img_bytes = None

            # Method B: Direct URL download fallback
            if not img_bytes and src_url and src_url.startswith(("http://", "https://")):
                try:
                    req = urllib.request.Request(
                        src_url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"}
                    )
                    with urllib.request.urlopen(req, timeout=12) as resp:
                        img_bytes = resp.read()
                        ctype = resp.headers.get("content-type", "")
                        ext = "png" if "png" in ctype else "webp" if "webp" in ctype else "jpg"
                except Exception:
                    img_bytes = None

            if img_bytes:
                content_hash = hashlib.sha256(img_bytes).hexdigest()
                if content_hash in seen_hashes:
                    continue
                seen_hashes.add(content_hash)

                filepath = target_dir / f"image_{int(time.time())}_{len(saved)+1}.{ext}"
                with open(filepath, "wb") as f:
                    f.write(img_bytes)
                posix_path = filepath.as_posix()
                item = {
                    "index": len(saved) + 1,
                    "file_path": str(filepath),
                    "normalized_path": posix_path,
                    "markdown_link": f"![Extracted Image {len(saved)+1}](file:///{posix_path})",
                    "width": img.get("naturalWidth"),
                    "height": img.get("naturalHeight"),
                    "size_bytes": len(img_bytes),
                    "size_kb": round(len(img_bytes) / 1024, 2),
                    "format": ext.upper(),
                    "alt_text": img.get("alt", ""),
                    "src_url": src_url,
                    "supabase_ready": True,
                    "taliyo_action": "Pass this 'file_path' directly to taliyo-blog-engine's 'upload_blog_image' or 'create_blog_post' to auto-host on Supabase Storage!"
                }
                if auto_optimize_platform:
                    try:
                        opt_res = optimize_image(image_path=str(filepath), platform=auto_optimize_platform)
                        if opt_res.get("status") == "success":
                            item["optimized"] = opt_res
                    except Exception:
                        pass
                if return_base64 and b64:
                    item["base64"] = b64
                saved.append(item)

        return {
            "status": "success",
            "total_extracted": len(saved),
            "save_directory": str(target_dir),
            "images": saved,
            "supabase_ready": True,
            "message": f"Successfully extracted {len(saved)} full-resolution original image(s) to '{target_dir}'. Ready for Supabase upload and Taliyo Blog insertion."
        }

    # ==========================================
    # 3. Page Observation
    # ==========================================

    def page_inspect(self, session_id: str = "default") -> Dict[str, Any]:
        """Generates structured semantic snapshot with assigned @ref IDs."""
        self._require_extension()
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

    def page_forms(self, session_id: str = "default") -> List[Dict[str, Any]]:
        """Returns detected forms and fields on active page."""
        self._require_extension()
        obs = self.extension_bridge.inspect_page(session_id)
        return [f.model_dump() for f in obs.forms]

    def page_text(self, session_id: str = "default", max_chars: int = 3000) -> Dict[str, Any]:
        """Extracts visible, readable text summary of active page."""
        self._require_extension()
        obs = self.extension_bridge.inspect_page(session_id)
        return {
            "url": obs.url,
            "title": obs.title,
            "text": obs.visible_text_summary[:max_chars]
        }

    def browser_ocr(
        self,
        image_path: Optional[str] = None,
        session_id: str = "default",
        filter_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """Runs ultra-fast RapidOCR (ONNX) on the current browser tab or a local image path.
        Extracts detected text, confidence ratings, and bounding boxes without heavy PyTorch.
        """
        import numpy as np
        from io import BytesIO
        from PIL import Image

        raw_bytes = None
        if image_path and Path(image_path).exists():
            raw_bytes = Path(image_path).read_bytes()
        else:
            self._require_extension()
            res = self.extension_bridge.send_command_sync("screenshot", {}, timeout=15.0)
            data_url = res.get("dataUrl", "")
            if "," in data_url:
                raw_bytes = base64.b64decode(data_url.split(",")[1])

        if not raw_bytes:
            raise ValueError("No image data available for OCR analysis.")

        pil_img = Image.open(BytesIO(raw_bytes)).convert("RGB")
        img_np = np.array(pil_img)

        try:
            from rapidocr_onnxruntime import RapidOCR
            engine = RapidOCR()
            ocr_result, elapse = engine(img_np)
        except Exception as e:
            raise RuntimeError(f"RapidOCR engine initialization failed: {e}")

        lines = []
        full_text = []
        if ocr_result:
            for item in ocr_result:
                box, text, score = item[0], item[1], float(item[2])
                if filter_pattern and filter_pattern.lower() not in text.lower():
                    continue
                lines.append({
                    "text": text,
                    "confidence": round(score, 4),
                    "box": box
                })
                full_text.append(text)

        return {
            "success": True,
            "detected_lines_count": len(lines),
            "full_text": "\n".join(full_text),
            "lines": lines,
            "engine": "RapidOCR-ONNX"
        }

    # ==========================================
    # 4. Network & Stream Telemetry
    # ==========================================


    def network_stream(
        self,
        session_id: str = "default",
        filter_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Reads latest events from ring buffer advancing the cursor."""
        all_events = self.storage.get_events(session_id, limit=self.storage.max_buffer_size)
        cursor = self._stream_cursors.get(session_id, 0)
        new_events = all_events[cursor:]
        self._stream_cursors[session_id] = len(all_events)

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
        """Lists captured HTTP transactions mirroring Chrome DevTools Network table."""
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
        """Retrieves full request details matching Chrome DevTools tabs."""
        tx = self.storage.get_transaction(session_id, request_id)
        if not tx:
            return None

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

        initiator_tab = {
            "initiator": tx.request.initiator or "Other",
            "type": tx.request.initiator_type
        }

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
        """Returns DevTools bottom summary status bar."""
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

            r_type = t.request.resource_type or "other"
            type_counts[r_type] = type_counts.get(r_type, 0) + 1

            if t.response:
                total_transferred_bytes += t.response.encoded_data_length
                total_resource_bytes += max(t.response.size, t.response.encoded_data_length)

        finish_time_s = round(max(0.0, max_end - min_start), 2) if total_requests > 0 else 0.0

        def _fmt_size(b: int) -> str:
            if b >= 1024 * 1024:
                return f"{round(b / (1024 * 1024), 1)} MB"
            return f"{round(b / 1024, 1)} kB"

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

    # ==========================================
    # 5. Console & Streaming Telemetry
    # ==========================================

    def console_list(
        self,
        session_id: str = "default",
        min_level: str = "info",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        events = self.storage.list_console_events(session_id, limit=limit, min_level=min_level)
        return [c.model_dump() for c in events]

    def websocket_list(self, session_id: str = "default") -> List[Dict[str, Any]]:
        return []

    def sse_list(self, session_id: str = "default") -> List[Dict[str, Any]]:
        return []

    # ==========================================
    # 6. QA Intelligence & Reporting
    # ==========================================

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

    # ==========================================
    # 7. System Storage & Purge
    # ==========================================

    def storage_inspect(self) -> Dict[str, Any]:
        """Scans and itemizes all temporary storage consumed by MCPs."""
        items = []
        total_bytes = 0

        if SCREENSHOTS_DIR.exists():
            for f in SCREENSHOTS_DIR.rglob("*.*"):
                if f.is_file():
                    sz = f.stat().st_size
                    total_bytes += sz
                    items.append({"name": f.name, "size_bytes": sz, "size_kb": round(sz / 1024, 2), "path": str(f)})

        return {
            "status": "success",
            "storage_path": str(SCREENSHOTS_DIR),
            "screenshots_count": len(items),
            "total_files": len(items),
            "total_bytes": total_bytes,
            "total_kb": round(total_bytes / 1024, 2),
            "total_mb": round(total_bytes / (1024 * 1024), 2),
            "files": items[:25]
        }

    def storage_clean(self, dry_run: bool = False) -> Dict[str, Any]:
        """Safely wipes temporary screenshots and caches."""
        deleted_count = 0
        freed_bytes = 0

        if SCREENSHOTS_DIR.exists():
            for f in SCREENSHOTS_DIR.rglob("*.*"):
                if f.is_file():
                    sz = f.stat().st_size
                    freed_bytes += sz
                    deleted_count += 1
                    if not dry_run:
                        try:
                            f.unlink()
                        except Exception:
                            pass

        return {
            "status": "success",
            "dry_run": dry_run,
            "deleted_count": deleted_count,
            "freed_bytes": freed_bytes,
            "freed_mb": round(freed_bytes / (1024 * 1024), 2),
            "message": f"Storage clean complete. Freed {round(freed_bytes / (1024 * 1024), 2)} MB across {deleted_count} files."
        }

    # ==========================================
    # 8. Media Optimization & Smart Canvas
    # ==========================================

    def optimize_media_for_platform(
        self,
        image_path: str,
        platform: str = "INSTAGRAM",
        max_size_kb: int = 200,
        output_format: str = "WEBP",
        background_color: str = "#0F172A",
        custom_width: Optional[int] = None,
        custom_height: Optional[int] = None,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compresses, crops, and canvas-fits images for target platforms (INSTAGRAM, STORY, SQUARE, EMAIL, BLOG, THUMBNAIL, CUSTOM)."""
        return optimize_image(
            image_path=image_path,
            platform=platform,
            max_size_kb=max_size_kb,
            output_format=output_format,
            background_color=background_color,
            custom_width=custom_width,
            custom_height=custom_height,
            output_dir=output_dir
        )

    def optimize_media_batch(
        self,
        source_dir_or_files: Optional[Any] = None,
        platform: str = "INSTAGRAM",
        max_size_kb: int = 200,
        output_format: str = "WEBP",
        background_color: str = "#0F172A"
    ) -> Dict[str, Any]:
        """Batch-optimizes images in extracted_images directory or a custom path."""
        return optimize_batch(
            source_dir_or_files=source_dir_or_files,
            platform=platform,
            max_size_kb=max_size_kb,
            output_format=output_format,
            background_color=background_color
        )


