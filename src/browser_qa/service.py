"""Unified 100% Extension-Native Service Layer powering SpectraBrowser MCP.

Controls the user's live Chrome browser directly via the Spectra Chrome Extension
WebSocket Bridge without launching isolated or headless browser instances.
"""

import base64
import hashlib
import json
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime


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


# ==========================================
# Phase 1: New Data Structures
# ==========================================

@dataclass
class SessionMemory:
    """Per-session key-value memory store."""
    session_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class TabHandle:
    """Named tab handle for multi-tab orchestration."""
    name: str
    tab_id: str
    session_id: str
    url: str = ""
    title: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class ActionRecord:
    """Single action with outcome for timeline."""
    action_id: str
    session_id: str
    timestamp: float
    action_type: str  # click, type, navigate, etc.
    target: str
    params: Dict[str, Any]
    success: bool
    error: Optional[str] = None
    network_effects: List[Dict[str, Any]] = field(default_factory=list)
    console_errors: List[Dict[str, Any]] = field(default_factory=list)
    screenshot_before: Optional[str] = None  # base64
    screenshot_after: Optional[str] = None   # base64
    duration_ms: float = 0.0


@dataclass
class Macro:
    """Recorded macro for replay."""
    name: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    description: str = ""


@dataclass
class FailedTarget:
    """Failed click/type target for avoidance."""
    session_id: str
    target: str
    action_type: str
    error: str
    timestamp: float
    observation_id: Optional[str] = None


@dataclass
class TestCase:
    """Exportable test case with steps and evidence."""
    name: str
    session_id: str
    created_at: float
    steps: List[ActionRecord]
    screenshots: Dict[str, str] = field(default_factory=dict)  # step_id -> base64
    network_log: List[Dict[str, Any]] = field(default_factory=list)
    console_log: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


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

        # Phase 1: New state
        self._session_memory: Dict[str, SessionMemory] = {}
        self._tab_handles: Dict[str, Dict[str, TabHandle]] = {}  # session_id -> {name -> TabHandle}
        self._action_timeline: Dict[str, List[ActionRecord]] = {}  # session_id -> List[ActionRecord]
        self._macros: Dict[str, Macro] = {}  # macro_name -> Macro
        self._recording_macro: Optional[str] = None
        self._failed_targets: Dict[str, List[FailedTarget]] = {}  # session_id -> List[FailedTarget]
        self._test_cases: Dict[str, TestCase] = {}  # test_name -> TestCase
        self._recording_test_case: Optional[str] = None

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
        started = time.time()
        self._require_extension()
        try:
            res = self.extension_bridge.navigate(url)
            out = {"success": True, "message": f"Navigated via Chrome Extension to {url}", "current_url": res.get("url", url)}
            self._record_action(session_id, "navigate", url, {}, True, None, round((time.time() - started) * 1000, 1))
            return out
        except Exception as e:
            self._record_action(session_id, "navigate", url, {}, False, str(e), round((time.time() - started) * 1000, 1))
            raise

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
        started = time.time()
        self._require_extension()
        try:
            res = self.extension_bridge.click(target)
            out = {
                "success": res.get("success", False),
                "action": "click",
                "target": target,
                "message": res.get("error") or f"Clicked '{target}' via Chrome Extension",
                "details": res
            }
            self._record_action(session_id, "click", target, {"observation_id": observation_id}, bool(out["success"]), None if out["success"] else out["message"], round((time.time() - started) * 1000, 1))
            return out
        except Exception as e:
            self._record_action(session_id, "click", target, {"observation_id": observation_id}, False, str(e), round((time.time() - started) * 1000, 1))
            raise

    def browser_type(
        self,
        target: str,
        text: str,
        observation_id: Optional[str] = None,
        clear: bool = False,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """Fills/types text with React/Vue input setter and contenteditable support."""
        started = time.time()
        self._require_extension()
        try:
            res = self.extension_bridge.type(target, text, clear=clear)
            out = {
                "success": res.get("success", False),
                "action": "type",
                "target": target,
                "message": res.get("error") or f"Typed into '{target}' via Chrome Extension",
                "details": res
            }
            self._record_action(session_id, "type", target, {"value_len": len(text), "clear": clear}, bool(out["success"]), None if out["success"] else out["message"], round((time.time() - started) * 1000, 1))
            return out
        except Exception as e:
            self._record_action(session_id, "type", target, {"clear": clear}, False, str(e), round((time.time() - started) * 1000, 1))
            raise

    def browser_select(
        self,
        target: str,
        option: str,
        observation_id: Optional[str] = None,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """Selects dropdown option."""
        started = time.time()
        self._require_extension()
        try:
            res = self.extension_bridge.select(target, option)
            out = {"success": res.get("success", True), "target": target, "option": option, "details": res}
            self._record_action(session_id, "select", target, {"option": option}, bool(out["success"]), None, round((time.time() - started) * 1000, 1))
            return out
        except Exception as e:
            self._record_action(session_id, "select", target, {"option": option}, False, str(e), round((time.time() - started) * 1000, 1))
            raise

    def browser_scroll(
        self,
        direction: str = "down",
        amount: int = 500,
        target: Optional[str] = None,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """Scrolls window, scrollable containers (e.g. ChatGPT thread), or target element into view."""
        started = time.time()
        self._require_extension()
        try:
            res = self.extension_bridge.scroll(direction=direction, amount=amount, target=target)
            out = {"status": "success", "message": f"Scrolled {direction} by {amount}px via Chrome Extension", "details": res}
            self._record_action(session_id, "scroll", target or direction, {"direction": direction, "amount": amount}, True, None, round((time.time() - started) * 1000, 1))
            return out
        except Exception as e:
            self._record_action(session_id, "scroll", target or direction, {"direction": direction}, False, str(e), round((time.time() - started) * 1000, 1))
            raise

    def browser_press(self, key: str = "Enter", session_id: str = "default") -> Dict[str, Any]:
        """Simulates keyboard key press (Enter, Escape, Tab, Arrow keys)."""
        started = time.time()
        self._require_extension()
        try:
            res = self.extension_bridge.press_key(key)
            out = {"status": "success", "message": f"Pressed key '{key}' via Chrome Extension", "details": res}
            self._record_action(session_id, "press", key, {}, True, None, round((time.time() - started) * 1000, 1))
            return out
        except Exception as e:
            self._record_action(session_id, "press", key, {}, False, str(e), round((time.time() - started) * 1000, 1))
            raise

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

    # ==========================================
    # Phase 1A. Session Memory (Brain Working Memory)
    # ==========================================

    def _ensure_memory(self, session_id: str) -> SessionMemory:
        mem = self._session_memory.get(session_id)
        if mem is None:
            mem = SessionMemory(session_id=session_id)
            self._session_memory[session_id] = mem
        return mem

    def session_memory_set(self, session_id: str = "default", key: str = "", value: Any = None) -> Dict[str, Any]:
        if not key:
            return {"success": False, "error": "key is required"}
        mem = self._ensure_memory(session_id)
        mem.data[key] = value
        mem.updated_at = time.time()
        return {"success": True, "session_id": session_id, "key": key, "value": value}

    def session_memory_get(self, session_id: str = "default", key: str = "", default: Any = None) -> Dict[str, Any]:
        mem = self._ensure_memory(session_id)
        found = key in mem.data
        return {"success": True, "session_id": session_id, "key": key, "value": mem.data.get(key, default), "found": found}

    def session_memory_delete(self, session_id: str = "default", key: str = "") -> Dict[str, Any]:
        mem = self._ensure_memory(session_id)
        existed = key in mem.data
        mem.data.pop(key, None)
        mem.updated_at = time.time()
        return {"success": True, "session_id": session_id, "key": key, "deleted": existed}

    def session_memory_list(self, session_id: str = "default") -> Dict[str, Any]:
        mem = self._ensure_memory(session_id)
        return {"success": True, "session_id": session_id, "keys": list(mem.data.keys()), "data": dict(mem.data)}

    def session_memory_clear(self, session_id: str = "default") -> Dict[str, Any]:
        mem = self._ensure_memory(session_id)
        count = len(mem.data)
        mem.data.clear()
        mem.updated_at = time.time()
        return {"success": True, "session_id": session_id, "cleared_keys": count}

    # ==========================================
    # Phase 1B. Action Timeline + Failed Targets
    # ==========================================

    def _ensure_timeline(self, session_id: str) -> List[ActionRecord]:
        tl = self._action_timeline.get(session_id)
        if tl is None:
            tl = []
            self._action_timeline[session_id] = tl
        return tl

    def _record_action(
        self,
        session_id: str,
        action_type: str,
        target: str,
        params: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error: Optional[str] = None,
        duration_ms: float = 0.0,
    ) -> ActionRecord:
        tl = self._ensure_timeline(session_id)
        rec = ActionRecord(
            action_id=f"act_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            timestamp=time.time(),
            action_type=action_type,
            target=target or "",
            params=params or {},
            success=success,
            error=error,
            duration_ms=duration_ms,
        )
        # Attach lightweight network/console effects (last 5 errors only, no screenshots by default)
        try:
            txs = self.storage.list_transactions(session_id, limit=5)
            rec.network_effects = [{"url": getattr(t.request, "url", ""), "status": t.response.status if t.response else 0} for t in txs[-5:]]
        except Exception:
            pass
        try:
            console_evs = self.storage.list_console_events(session_id, limit=20)
            rec.console_errors = [c.model_dump() for c in console_evs if getattr(c, "level", "") in ("error", "warn")][-5:]
        except Exception:
            pass
        tl.append(rec)
        # Cap timeline at 200 entries (ring buffer)
        if len(tl) > 200:
            del tl[: len(tl) - 200]
        if not success:
            ft = FailedTarget(session_id=session_id, target=target or "", action_type=action_type, error=error or "unknown", timestamp=rec.timestamp)
            self._failed_targets.setdefault(session_id, []).append(ft)
        # Macro recording hook
        if self._recording_macro and self._recording_macro in self._macros:
            self._macros[self._recording_macro].steps.append({"action": action_type, "target": target, "params": params or {}})
        return rec

    def action_timeline(self, session_id: str = "default", limit: int = 20) -> List[Dict[str, Any]]:
        tl = self._ensure_timeline(session_id)
        return [asdict(r) for r in tl[-limit:]]

    def action_last(self, session_id: str = "default") -> Dict[str, Any]:
        tl = self._ensure_timeline(session_id)
        if not tl:
            return {"success": False, "error": "no actions recorded yet"}
        return {"success": True, **asdict(tl[-1])}

    def failed_targets_list(self, session_id: str = "default") -> List[Dict[str, Any]]:
        return [asdict(f) for f in self._failed_targets.get(session_id, [])]

    def failed_targets_clear(self, session_id: str = "default") -> Dict[str, Any]:
        count = len(self._failed_targets.get(session_id, []))
        self._failed_targets[session_id] = []
        return {"success": True, "session_id": session_id, "cleared": count}

    # ==========================================
    # Phase 1C. Named Multi-Tab Orchestration
    # ==========================================

    def _ensure_tabs(self, session_id: str) -> Dict[str, TabHandle]:
        d = self._tab_handles.get(session_id)
        if d is None:
            d = {}
            self._tab_handles[session_id] = d
        return d

    def tab_create(self, name: str, url: str = "", tab_id: str = "", session_id: str = "default") -> Dict[str, Any]:
        if not name:
            return {"success": False, "error": "name is required"}
        tabs = self._ensure_tabs(session_id)
        # Best-effort: resolve real tab_id from live Chrome if not provided
        resolved_tab_id = tab_id
        title = ""
        current_url = url
        if not resolved_tab_id and self.extension_bridge.is_connected():
            try:
                live_tabs = self.extension_bridge.list_tabs() or []
                # Prefer tab matching URL, else active tab
                match = None
                if url:
                    for t in live_tabs:
                        if url.lower() in str(t.get("url", "")).lower():
                            match = t
                            break
                if match is None and live_tabs:
                    match = live_tabs[0]
                if match:
                    resolved_tab_id = str(match.get("id") or match.get("tabId") or match.get("tab_id") or "")
                    title = str(match.get("title", ""))
                    current_url = str(match.get("url", url))
            except Exception:
                pass
        if not resolved_tab_id:
            resolved_tab_id = f"local_{uuid.uuid4().hex[:8]}"
        handle = TabHandle(name=name, tab_id=resolved_tab_id, session_id=session_id, url=current_url, title=title)
        tabs[name] = handle
        self._record_action(session_id, "tab_create", name, {"url": url, "tab_id": resolved_tab_id}, True, None, 0)
        return {"success": True, "session_id": session_id, **asdict(handle)}

    def tab_switch(self, name: str, session_id: str = "default") -> Dict[str, Any]:
        tabs = self._ensure_tabs(session_id)
        handle = tabs.get(name)
        if not handle:
            self._record_action(session_id, "tab_switch", name, {}, False, "tab handle not found", 0)
            return {"success": False, "error": f"tab '{name}' not found. Use tab_list() to see handles."}
        try:
            res = self.browser_select_tab(handle.tab_id, session_id)
            self._record_action(session_id, "tab_switch", name, {"tab_id": handle.tab_id}, True, None, 0)
            return {"success": True, "session_id": session_id, "name": name, "tab_id": handle.tab_id, "details": res}
        except Exception as e:
            self._record_action(session_id, "tab_switch", name, {"tab_id": handle.tab_id}, False, str(e), 0)
            return {"success": False, "error": str(e)}

    def tab_close(self, name: str, session_id: str = "default") -> Dict[str, Any]:
        tabs = self._ensure_tabs(session_id)
        handle = tabs.pop(name, None)
        if not handle:
            return {"success": False, "error": f"tab '{name}' not found"}
        # Best-effort: ask extension to close tab (may not be implemented — ignore failure)
        try:
            if self.extension_bridge.is_connected():
                try:
                    self.extension_bridge.send_command_sync("close_tab", {"tabId": handle.tab_id}, timeout=5.0)
                except Exception:
                    pass
        except Exception:
            pass
        self._record_action(session_id, "tab_close", name, {"tab_id": handle.tab_id}, True, None, 0)
        return {"success": True, "session_id": session_id, "name": name, "closed_tab_id": handle.tab_id}

    def tab_list(self, session_id: str = "default") -> List[Dict[str, Any]]:
        tabs = self._ensure_tabs(session_id)
        return [asdict(h) for h in tabs.values()]

    # ==========================================
    # Phase 1D. Macros (Record / Replay)
    # ==========================================

    def macro_start_recording(self, name: str, description: str = "") -> Dict[str, Any]:
        if not name:
            return {"success": False, "error": "name is required"}
        self._macros[name] = Macro(name=name, description=description)
        self._recording_macro = name
        return {"success": True, "recording": name, "message": f"Recording macro '{name}'. All browser actions will be captured."}

    def macro_stop_recording(self) -> Dict[str, Any]:
        name = self._recording_macro
        self._recording_macro = None
        if not name:
            return {"success": False, "error": "no macro is being recorded"}
        macro = self._macros.get(name)
        return {"success": True, "name": name, "steps_count": len(macro.steps) if macro else 0, "steps": macro.steps if macro else []}

    def macro_list(self) -> List[Dict[str, Any]]:
        return [{"name": m.name, "description": m.description, "steps_count": len(m.steps), "created_at": m.created_at} for m in self._macros.values()]

    def macro_get(self, name: str) -> Dict[str, Any]:
        m = self._macros.get(name)
        if not m:
            return {"success": False, "error": f"macro '{name}' not found"}
        return {"success": True, "name": m.name, "description": m.description, "steps": m.steps}

    def macro_delete(self, name: str) -> Dict[str, Any]:
        existed = self._macros.pop(name, None) is not None
        if self._recording_macro == name:
            self._recording_macro = None
        return {"success": existed, "name": name, "deleted": existed}

    def _dispatch_step(self, step: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        action = str(step.get("action", "")).lower()
        target = str(step.get("target", ""))
        params = step.get("params", {}) or {}
        try:
            if action in ("navigate", "goto"):
                return self.browser_navigate(target or params.get("url", ""), session_id)
            elif action == "click":
                return self.browser_click(target, session_id=session_id)
            elif action == "type":
                return self.browser_type(target, params.get("value", params.get("text", "")), session_id=session_id, clear=params.get("clear", False))
            elif action == "select":
                return self.browser_select(target, params.get("option", ""), session_id=session_id)
            elif action in ("scroll",):
                return self.browser_scroll(params.get("direction", "down"), params.get("amount", 500), target or None, session_id)
            elif action in ("press", "key"):
                return self.browser_press(params.get("key", target or "Enter"), session_id)
            elif action in ("wait", "sleep"):
                return self.browser_wait(params.get("ms", 1000), session_id)
            elif action in ("wait_for",):
                return self.browser_wait_for(target, params.get("state", "visible"), params.get("timeout_ms", 15000), session_id)
            else:
                return {"success": False, "error": f"unsupported macro action '{action}'"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def macro_run(self, name: str, session_id: str = "default") -> Dict[str, Any]:
        m = self._macros.get(name)
        if not m:
            return {"success": False, "error": f"macro '{name}' not found"}
        results: List[Dict[str, Any]] = []
        ok = 0
        for idx, step in enumerate(m.steps):
            res = self._dispatch_step(step, session_id)
            success = bool(res.get("success", res.get("status") == "success"))
            if success:
                ok += 1
            results.append({"index": idx, "step": step, "success": success, "result": res})
            if not success:
                break
        return {"success": ok == len(m.steps), "name": name, "session_id": session_id, "passed": ok, "total": len(m.steps), "results": results}

    # ==========================================
    # Phase 1E. Test Cases (Record / Export)
    # ==========================================

    def test_start_recording(self, name: str, session_id: str = "default", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not name:
            return {"success": False, "error": "name is required"}
        tl = self._ensure_timeline(session_id)
        self._test_cases[name] = TestCase(name=name, session_id=session_id, created_at=time.time(), steps=[], metadata=metadata or {})
        # Store start index via metadata
        self._test_cases[name].metadata["_start_index"] = len(tl)
        self._recording_test_case = name
        return {"success": True, "recording": name, "session_id": session_id}

    def test_stop_recording(self, name: Optional[str] = None) -> Dict[str, Any]:
        tname = name or self._recording_test_case
        if not tname or tname not in self._test_cases:
            return {"success": False, "error": "no test case is being recorded"}
        tc = self._test_cases[tname]
        tl = self._ensure_timeline(tc.session_id)
        start_idx = int(tc.metadata.pop("_start_index", 0))
        tc.steps = list(tl[start_idx:])
        try:
            tc.network_log = [t.name for t in self.storage.list_transactions(tc.session_id, limit=100)]
        except Exception:
            tc.network_log = []
        try:
            tc.console_log = [c.model_dump() for c in self.storage.list_console_events(tc.session_id, limit=100)]
        except Exception:
            tc.console_log = []
        self._recording_test_case = None
        return {"success": True, "name": tname, "steps_count": len(tc.steps)}

    def test_list(self) -> List[Dict[str, Any]]:
        return [{"name": t.name, "session_id": t.session_id, "steps_count": len(t.steps), "created_at": t.created_at} for t in self._test_cases.values()]

    def test_get(self, name: str) -> Dict[str, Any]:
        t = self._test_cases.get(name)
        if not t:
            return {"success": False, "error": f"test '{name}' not found"}
        return {"success": True, "name": t.name, "session_id": t.session_id, "created_at": t.created_at, "steps": [asdict(s) for s in t.steps], "network_log": t.network_log, "console_log": t.console_log, "metadata": t.metadata}

    def test_delete(self, name: str) -> Dict[str, Any]:
        existed = self._test_cases.pop(name, None) is not None
        if self._recording_test_case == name:
            self._recording_test_case = None
        return {"success": existed, "name": name, "deleted": existed}

    def test_export(self, name: str) -> Dict[str, Any]:
        t = self._test_cases.get(name)
        if not t:
            return {"success": False, "error": f"test '{name}' not found"}
        export = {
            "name": t.name,
            "session_id": t.session_id,
            "created_at": datetime.fromtimestamp(t.created_at).isoformat(),
            "steps": [{"action": s.action_type, "target": s.target, "params": s.params, "success": s.success, "error": s.error} for s in t.steps],
            "network_log": t.network_log,
            "console_log": t.console_log,
            "metadata": t.metadata,
            "replay_hint": f"Use macro_run() or re-dispatch steps via browser_* tools in order.",
        }
        return {"success": True, **export}

    # ==========================================
    # Phase 1F. Auth Detection + Session Health
    # ==========================================

    def auth_status(self, session_id: str = "default") -> Dict[str, Any]:
        if not self.extension_bridge.is_connected():
            return {"success": True, "logged_in": None, "state": "unknown", "reason": "extension not connected"}
        try:
            obs = self.extension_bridge.inspect_page(session_id)
            url = (obs.url or "").lower()
            title = obs.title or ""
            names = " ".join([(e.name or "") for e in obs.interactive_elements]).lower()
            login_keywords = ["log in", "login", "sign in", "signin", "password", "otp", "forgot"]
            logout_keywords = ["log out", "logout", "sign out", "signout", "avatar", "profile", "account", "dashboard"]
            has_login = any(k in names for k in login_keywords) or "login" in url or "signin" in url
            has_logout = any(k in names for k in logout_keywords)
            has_password_field = any("password" in str(getattr(e, "input_type", "") or "").lower() or "password" in (e.name or "").lower() for e in obs.interactive_elements)
            logged_in: Optional[bool] = None
            if has_logout and not has_login:
                logged_in = True
            elif has_login and not has_logout:
                logged_in = False
            return {
                "success": True,
                "logged_in": logged_in,
                "url": obs.url,
                "title": title,
                "signals": {"has_login_ui": has_login, "has_logout_ui": has_logout, "has_password_field": has_password_field},
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def session_health_check(self, session_id: str = "default") -> Dict[str, Any]:
        connected = self.extension_bridge.is_connected()
        state = self._session_states.get(session_id, "active" if connected else "disconnected")
        pause_reason = self._pause_reasons.get(session_id)
        try:
            tx_count = len(self.storage.list_transactions(session_id, limit=500))
        except Exception:
            tx_count = 0
        try:
            console_errs = [c for c in self.storage.list_console_events(session_id, limit=100) if getattr(c, "level", "") == "error"]
            console_err_count = len(console_errs)
        except Exception:
            console_err_count = 0
        failed = len(self._failed_targets.get(session_id, []))
        if not connected:
            action = "connect_extension"
        elif state == "paused":
            action = "resume_after_human"
        elif console_err_count > 10:
            action = "inspect_console_errors"
        elif failed > 3:
            action = "review_failed_targets"
        else:
            action = "ok"
        return {
            "success": True,
            "session_id": session_id,
            "extension_connected": connected,
            "state": state,
            "pause_reason": pause_reason,
            "transactions": tx_count,
            "console_errors": console_err_count,
            "failed_targets": failed,
            "recommended_action": action,
        }

    # ==========================================
    # Phase 1G. Smart Retries + Fallbacks
    # ==========================================

    def browser_click_retry(
        self,
        target: str,
        session_id: str = "default",
        max_attempts: int = 3,
        backoff_ms: int = 500,
        observation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        last_error: Optional[str] = None
        for attempt in range(1, max_attempts + 1):
            started = time.time()
            try:
                res = self.browser_click(target, observation_id, session_id)
                ok = bool(res.get("success", False))
                dur = round((time.time() - started) * 1000, 1)
                self._record_action(session_id, "click_retry", target, {"attempt": attempt, "max_attempts": max_attempts}, ok, None if ok else res.get("message"), dur)
                if ok:
                    return {"success": True, "target": target, "attempts": attempt, "result": res}
                last_error = str(res.get("message", "click failed"))
            except Exception as e:
                last_error = str(e)
                dur = round((time.time() - started) * 1000, 1)
                self._record_action(session_id, "click_retry", target, {"attempt": attempt}, False, last_error, dur)
            if attempt < max_attempts:
                time.sleep(max(0.05, backoff_ms / 1000.0))
        return {"success": False, "target": target, "attempts": max_attempts, "error": last_error}

    def browser_click_fallback(
        self,
        targets: List[str],
        session_id: str = "default",
        observation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not targets:
            return {"success": False, "error": "targets list is empty"}
        errors: List[Dict[str, Any]] = []
        for t in targets:
            try:
                res = self.browser_click(t, observation_id, session_id)
                ok = bool(res.get("success", False))
                self._record_action(session_id, "click_fallback", t, {"candidates": targets}, ok, None if ok else res.get("message"), 0)
                if ok:
                    return {"success": True, "used_target": t, "result": res}
                errors.append({"target": t, "error": res.get("message", "failed")})
            except Exception as e:
                errors.append({"target": t, "error": str(e)})
                self._record_action(session_id, "click_fallback", t, {"candidates": targets}, False, str(e), 0)
        return {"success": False, "error": "all fallback targets failed", "attempts": errors}

    # ==========================================
    # Phase 2A. Visual Fingerprinting + Stable Identity
    # ==========================================

    def _raw_elements(self, session_id: str = "default") -> List[Dict[str, Any]]:
        """Returns raw inspect_page elements WITH rect (bypasses pydantic model which drops position)."""
        self._require_extension()
        data = self.extension_bridge.send_command_sync("inspect_page", {}, timeout=15.0)
        els = data.get("interactive_elements", []) or []
        # Attach page url/title for context
        for e in els:
            e["_page_url"] = data.get("url", "")
            e["_page_title"] = data.get("title", "")
        return els

    @staticmethod
    def _norm(s: Any) -> str:
        return str(s or "").strip().lower()

    def element_fingerprint(self, ref_id: str, session_id: str = "default") -> Dict[str, Any]:
        """Builds a stable visual+structural fingerprint for an element (survives @ref reassignment)."""
        if not ref_id:
            return {"success": False, "error": "ref_id is required (e.g. '@3')"}
        try:
            els = self._raw_elements(session_id)
        except Exception as e:
            return {"success": False, "error": str(e)}
        match = next((e for e in els if str(e.get("ref_id", "")) == ref_id), None)
        if not match:
            return {"success": False, "error": f"element '{ref_id}' not found. Re-run page_inspect first."}
        rect = match.get("rect", {}) or {}
        x = float(rect.get("x", 0) or 0)
        y = float(rect.get("y", 0) or 0)
        w = float(rect.get("width", 0) or 0)
        h = float(rect.get("height", 0) or 0)
        name = str(match.get("name", ""))
        role = str(match.get("role", ""))
        tag = str(match.get("tag", ""))
        key_src = f"{self._norm(name)}|{self._norm(role)}|{self._norm(tag)}"
        fp = {
            "ref_id": ref_id,
            "role": role,
            "name": name,
            "tag": tag,
            "type": str(match.get("type", "")),
            "rect": {"x": x, "y": y, "width": w, "height": h},
            "center": {"x": round(x + w / 2, 1), "y": round(y + h / 2, 1)},
            "area": round(w * h, 1),
            "name_hash": hashlib.sha256(key_src.encode("utf-8")).hexdigest()[:16],
            "structural_key": key_src,
            "page_url": match.get("_page_url", ""),
        }
        # Persist for relocate
        mem = self._ensure_memory(session_id)
        mem.data[f"fingerprint:{ref_id}"] = fp
        mem.updated_at = time.time()
        return {"success": True, "session_id": session_id, "fingerprint": fp}

    def relocate_element(self, fingerprint: Any, session_id: str = "default") -> Dict[str, Any]:
        """Re-finds an element after re-render using a stored fingerprint (or '@ref' lookup)."""
        # Resolve fingerprint dict
        fp: Dict[str, Any] = {}
        if isinstance(fingerprint, str):
            # Try stored fingerprint first, else treat as ref_id to re-fingerprint
            mem = self._ensure_memory(session_id)
            stored = mem.data.get(f"fingerprint:{fingerprint}")
            if stored:
                fp = stored
            else:
                return self.element_fingerprint(fingerprint, session_id)
        elif isinstance(fingerprint, dict):
            fp = fingerprint
        else:
            return {"success": False, "error": "fingerprint must be a dict or '@ref' string"}
        try:
            els = self._raw_elements(session_id)
        except Exception as e:
            return {"success": False, "error": str(e)}
        target_name = self._norm(fp.get("name", ""))
        target_role = self._norm(fp.get("role", ""))
        target_tag = self._norm(fp.get("tag", ""))
        fp_rect = fp.get("rect", {}) or {}
        fx = float(fp_rect.get("x", 0) or 0)
        fy = float(fp_rect.get("y", 0) or 0)
        farea = float(fp.get("area", 0) or 0)
        best = None
        best_score = -1.0
        for e in els:
            name = self._norm(e.get("name", ""))
            role = self._norm(e.get("role", ""))
            tag = self._norm(e.get("tag", ""))
            score = 0.0
            if name and name == target_name:
                score += 50
            elif target_name and target_name in name:
                score += 20
            elif name and name in target_name:
                score += 15
            if role == target_role and role:
                score += 20
            if tag == target_tag and tag:
                score += 10
            r = e.get("rect", {}) or {}
            dx = abs(float(r.get("x", 0) or 0) - fx)
            dy = abs(float(r.get("y", 0) or 0) - fy)
            dist = (dx * dx + dy * dy) ** 0.5
            score += max(0.0, 20 - dist / 50.0)
            area = float(r.get("width", 0) or 0) * float(r.get("height", 0) or 0)
            if farea > 0 and area > 0:
                ratio = min(area, farea) / max(area, farea)
                score += ratio * 10
            if score > best_score:
                best_score = score
                best = e
        if not best or best_score < 25:
            return {"success": False, "error": "no confident match found after re-render", "best_score": round(best_score, 1)}
        return {
            "success": True,
            "session_id": session_id,
            "ref_id": best.get("ref_id", ""),
            "role": best.get("role", ""),
            "name": best.get("name", ""),
            "tag": best.get("tag", ""),
            "rect": best.get("rect", {}),
            "score": round(best_score, 1),
        }

    def find_element(self, description: str, session_id: str = "default", limit: int = 5) -> Dict[str, Any]:
        """Finds elements by visual/text description (e.g. 'red delete button in third row')."""
        if not description:
            return {"success": False, "error": "description is required"}
        try:
            els = self._raw_elements(session_id)
        except Exception as e:
            return {"success": False, "error": str(e)}
        tokens = [t for t in self._norm(description).replace(",", " ").split() if len(t) > 2]
        stop = {"the", "with", "inside", "third", "row", "button", "click", "that", "this", "and"}
        keywords = [t for t in tokens if t not in stop] or tokens
        scored = []
        for e in els:
            hay = f"{e.get('name','')} {e.get('role','')} {e.get('tag','')} {e.get('type','')}".lower()
            score = 0
            for kw in keywords:
                if kw in hay:
                    score += 10
            # Boost actionable roles when description mentions click/button
            if any(w in self._norm(description) for w in ("button", "click", "submit", "login")) and str(e.get("role", "")).lower() in ("button", "submit"):
                score += 5
            if score > 0:
                scored.append((score, e))
        scored.sort(key=lambda x: -x[0])
        results = [{"ref_id": e.get("ref_id", ""), "role": e.get("role", ""), "name": str(e.get("name", ""))[:120], "tag": e.get("tag", ""), "rect": e.get("rect", {}), "score": s} for s, e in scored[:limit]]
        return {"success": True, "session_id": session_id, "query": description, "count": len(results), "candidates": results}

    # ==========================================
    # Phase 2B. Visual Diff + Annotated Screenshots (Pillow-only)
    # ==========================================

    @staticmethod
    def _load_image(data: str):
        """Accepts data-URL base64, raw base64, or file path → PIL Image (RGB)."""
        from PIL import Image
        from io import BytesIO
        d = (data or "").strip()
        if not d:
            raise ValueError("empty image input")
        # File path
        if len(d) < 4096 and Path(d).exists():
            return Image.open(d).convert("RGB")
        # Data URL
        if "," in d and d.startswith("data:"):
            d = d.split(",", 1)[1]
        raw = base64.b64decode(d)
        return Image.open(BytesIO(raw)).convert("RGB")

    @staticmethod
    def _encode_image(img) -> str:
        from io import BytesIO
        buf = BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    def visual_compare(self, baseline: str, current: str, threshold: int = 12) -> Dict[str, Any]:
        """Compares two screenshots → similarity % + changed regions (Pillow, no GPU)."""
        try:
            from PIL import ImageChops, Image
        except Exception as e:
            return {"success": False, "error": f"Pillow unavailable: {e}"}
        try:
            a = self._load_image(baseline)
            b = self._load_image(current)
        except Exception as e:
            return {"success": False, "error": f"image decode failed: {e}"}
        if a.size != b.size:
            b = b.resize(a.size)
        diff = ImageChops.difference(a, b).convert("L")
        w, h = a.size
        total = w * h
        # Changed pixels above threshold
        import collections
        hist = diff.histogram()
        changed = sum(hist[threshold:])
        similarity = round(100.0 * (1 - changed / max(1, total)), 2)
        bbox = diff.point(lambda p: 255 if p >= threshold else 0).getbbox()
        # Coarse 4x4 grid of changed cells for spatial hint
        small = diff.resize((4, 4))
        cells = []
        px = small.load()
        for gy in range(4):
            for gx in range(4):
                if px[gx, gy] >= threshold:
                    cells.append({"gx": gx, "gy": gy, "x": int(gx * w / 4), "y": int(gy * h / 4), "w": int(w / 4), "h": int(h / 4)})
        return {
            "success": True,
            "size": {"width": w, "height": h},
            "similarity_percent": similarity,
            "changed_pixels": changed,
            "total_pixels": total,
            "bbox": {"x": bbox[0], "y": bbox[1], "width": bbox[2] - bbox[0], "height": bbox[3] - bbox[1]} if bbox else None,
            "changed_cells": cells,
            "verdict": "same" if similarity >= 99.5 else "minor_change" if similarity >= 95 else "major_change",
        }

    def screenshot_annotate(
        self,
        image: str = "",
        annotations: Optional[List[Dict[str, Any]]] = None,
        session_id: str = "default",
        save_to_disk: bool = False,
    ) -> Dict[str, Any]:
        """Draws boxes+labels on a screenshot (fresh capture if image empty). Returns base64 PNG."""
        try:
            from PIL import ImageDraw, ImageFont
        except Exception as e:
            return {"success": False, "error": f"Pillow unavailable: {e}"}
        annotations = annotations or []
        try:
            if image:
                img = self._load_image(image)
            else:
                self._require_extension()
                shot = self.extension_bridge.screenshot(session_id=session_id, save_to_disk=False, return_base64=True)
                img = self._load_image(shot.get("base64", ""))
        except Exception as e:
            return {"success": False, "error": str(e)}
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        palette = ["#EF4444", "#22C55E", "#3B82F6", "#F59E0B", "#A855F7", "#06B6D4"]
        drawn = 0
        for idx, ann in enumerate(annotations):
            try:
                box = ann.get("bbox") or ann.get("box") or []
                if len(box) == 4:
                    # Accept [x,y,w,h] OR [x1,y1,x2,y2] (heuristic: w,h < x,y magnitude → xywh)
                    x, y, c, d = [float(v) for v in box]
                    if c < x or d < y:
                        x1, y1, x2, y2 = x, y, x + c, y + d
                    else:
                        x1, y1, x2, y2 = x, y, c, d
                else:
                    continue
                color = ann.get("color") or palette[idx % len(palette)]
                label = str(ann.get("label", f"#{idx+1}"))
                draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
                if label:
                    tx1, ty1 = x1, max(0, y1 - 18)
                    tx2, ty2 = x1 + max(40, len(label) * 8), y1
                    draw.rectangle([tx1, ty1, tx2, ty2], fill=color)
                    draw.text((tx1 + 4, ty1 + 2), label, fill="white", font=font)
                drawn += 1
            except Exception:
                continue
        out_b64 = self._encode_image(img)
        result: Dict[str, Any] = {"success": True, "annotated_count": drawn, "size": {"width": img.width, "height": img.height}, "base64": out_b64}
        # Adaptive fallback: non-VLM models ignore base64 → attach text/position understanding (best-effort, never fails call)
        try:
            if self._vision_mode(session_id) in ("auto", "text"):
                tp = self.text_with_positions(session_id, max_items=40)
                if tp.get("success"):
                    result["text_fallback"] = {"count": tp.get("count", 0), "items": tp.get("items", [])}
        except Exception:
            pass
        if save_to_disk:
            try:
                target_dir = SCREENSHOTS_DIR / session_id
                target_dir.mkdir(parents=True, exist_ok=True)
                fp = target_dir / f"annotated_{int(time.time())}.png"
                img.save(fp)
                result["file_path"] = str(fp)
            except Exception as e:
                result["save_error"] = str(e)
        return result

    # ==========================================
    # Phase 2C. CDP Runtime.evaluate Helpers (Vitals, A11y, Tables)
    # ==========================================

    def _cdp_evaluate(self, expression: str, session_id: str = "default", timeout: float = 15.0) -> Any:
        """Runs JS in the live tab via CDP Runtime.evaluate (through extension cdp_command)."""
        self._require_extension()
        res = self.extension_bridge.execute_cdp("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
        # Extension returns {result: {result: {value: ...}}} or direct value depending on bridge
        if isinstance(res, dict):
            # chrome.debugger.sendCommand returns {result: {...}} for Runtime.evaluate
            inner = res.get("result", res)
            if isinstance(inner, dict) and "value" in inner:
                return inner["value"]
            if isinstance(inner, dict) and "result" in inner and isinstance(inner["result"], dict) and "value" in inner["result"]:
                return inner["result"]["value"]
            return inner
        return res

    def page_vitals(self, session_id: str = "default") -> Dict[str, Any]:
        """Collects page performance signals (TTFB, FCP, DOMContentLoaded, load, resources)."""
        js = """(async () => {
          const nav = performance.getEntriesByType('navigation')[0];
          const paints = Object.fromEntries(performance.getEntriesByType('paint').map(p => [p.name, Math.round(p.startTime)]));
          const resources = performance.getEntriesByType('resource');
          let totalBytes = 0;
          const byType = {};
          for (const r of resources) {
            totalBytes += (r.transferSize || r.decodedBodySize || 0);
            const t = r.initiatorType || 'other';
            byType[t] = (byType[t] || 0) + 1;
          }
          return {
            url: location.href,
            ttfb_ms: nav ? Math.round(nav.responseStart) : null,
            dom_content_loaded_ms: nav ? Math.round(nav.domContentLoadedEventEnd) : null,
            load_ms: nav ? Math.round(nav.loadEventEnd) : null,
            first_paint_ms: paints['first-paint'] ?? null,
            first_contentful_paint_ms: paints['first-contentful-paint'] ?? null,
            resources_count: resources.length,
            total_transfer_bytes: totalBytes,
            total_transfer_kb: Math.round(totalBytes / 1024),
            by_initiator: byType
          };
        })()"""
        try:
            val = self._cdp_evaluate(js, session_id)
            if not isinstance(val, dict):
                return {"success": False, "error": f"unexpected vitals payload: {val}"}
            return {"success": True, "session_id": session_id, **val}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def page_a11y_audit(self, session_id: str = "default") -> Dict[str, Any]:
        """Lightweight WCAG heuristic audit (no axe-core dep): alt, names, labels, headings, lang, title."""
        js = """(() => {
          const violations = [];
          const images = Array.from(document.querySelectorAll('img'));
          const imgsNoAlt = images.filter(i => !(i.getAttribute('alt') || '').trim()).slice(0, 10).map(i => (i.src || '').slice(0, 120));
          if (imgsNoAlt.length) violations.push({rule: 'img-alt', severity: 'serious', count: images.filter(i => !(i.getAttribute('alt') || '').trim()).length, sample: imgsNoAlt});
          const buttons = Array.from(document.querySelectorAll('button, [role="button"], a'));
          const noName = buttons.filter(b => !((b.innerText || '').trim() || (b.getAttribute('aria-label') || '').trim())).length;
          if (noName) violations.push({rule: 'button-name', severity: 'critical', count: noName});
          const inputs = Array.from(document.querySelectorAll('input, select, textarea'));
          const noLabel = inputs.filter(i => !(i.getAttribute('aria-label') || '').trim() && !(i.id && document.querySelector(`label[for="${i.id}"]`)) && !(i.getAttribute('placeholder') || '').trim()).length;
          if (noLabel) violations.push({rule: 'input-label', severity: 'serious', count: noLabel});
          const h1s = document.querySelectorAll('h1').length;
          if (h1s !== 1) violations.push({rule: 'h1-count', severity: 'moderate', count: h1s, message: 'page should have exactly one h1'});
          if (!document.documentElement.lang) violations.push({rule: 'html-lang', severity: 'serious', count: 1});
          if (!(document.title || '').trim()) violations.push({rule: 'doc-title', severity: 'serious', count: 1});
          const penalty = violations.reduce((s, v) => s + Math.min(30, (v.count || 1) * (v.severity === 'critical' ? 10 : v.severity === 'serious' ? 5 : 2)), 0);
          return {violations, images: images.length, buttons: buttons.length, inputs: inputs.length, score: Math.max(0, 100 - penalty)};
        })()"""
        try:
            val = self._cdp_evaluate(js, session_id)
            if not isinstance(val, dict):
                return {"success": False, "error": f"unexpected a11y payload: {val}"}
            return {"success": True, "session_id": session_id, "score": val.get("score", 0), "violations": val.get("violations", []), "counts": {"images": val.get("images", 0), "buttons": val.get("buttons", 0), "inputs": val.get("inputs", 0)}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_table(self, table_ref: str = "", session_id: str = "default", max_rows: int = 100) -> Dict[str, Any]:
        """Extracts HTML tables → structured {headers, rows} JSON (no CSS knowledge needed)."""
        # Escape ref for JS string
        safe_ref = (table_ref or "").replace("\\\\", "\\\\\\\\").replace("'", "\\\\'")
        js = f"""(() => {{
          const maxRows = {int(max_rows)};
          const tables = Array.from(document.querySelectorAll('table'));
          if (!tables.length) return {{ found: false, total_tables: 0 }};
          let table = null, tableIndex = -1;
          const ref = '{safe_ref}';
          if (ref && ref.startsWith('@')) {{
            const el = document.querySelector(`[data-spectra-ref="${{ref}}"]`);
            table = el ? el.closest('table') : null;
            if (table) tableIndex = tables.indexOf(table);
          }} else if (ref) {{
            try {{
              const el = document.querySelector(ref);
              table = el ? (el.tagName.toLowerCase() === 'table' ? el : el.closest('table')) : null;
              if (table) tableIndex = tables.indexOf(table);
            }} catch (e) {{}}
          }}
          if (!table) {{
            // Largest table by row count
            let best = 0;
            tables.forEach((t, i) => {{ const n = t.querySelectorAll('tr').length; if (n > best) {{ best = n; table = t; tableIndex = i; }} }});
          }}
          const rows = Array.from(table.querySelectorAll('tr')).slice(0, maxRows);
          let headers = Array.from(table.querySelectorAll('th')).map(th => th.innerText.trim());
          const data = [];
          for (const tr of rows) {{
            const cells = Array.from(tr.querySelectorAll('th, td')).map(c => c.innerText.trim());
            if (cells.length && !(headers.length && cells.every((c, i) => c === headers[i]))) data.push(cells);
          }}
          if (!headers.length && data.length) {{ headers = data.shift(); }}
          return {{ found: true, total_tables: tables.length, table_index: tableIndex, headers, rows: data, row_count: data.length }};
        }})()"""
        try:
            val = self._cdp_evaluate(js, session_id)
            if not isinstance(val, dict):
                return {"success": False, "error": f"unexpected table payload: {val}"}
            if not val.get("found"):
                return {"success": False, "error": "no <table> found on page", "total_tables": val.get("total_tables", 0)}
            headers = val.get("headers", []) or []
            rows = val.get("rows", []) or []
            dict_rows = [dict(zip(headers, r)) for r in rows] if headers else []
            return {"success": True, "session_id": session_id, "total_tables": val.get("total_tables", 0), "table_index": val.get("table_index", 0), "headers": headers, "rows": rows, "records": dict_rows, "row_count": val.get("row_count", len(rows))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==========================================
    # Phase 3H. Heuristic Layout Understanding (no VLM needed)
    # ==========================================

    def page_understand(self, session_id: str = "default") -> Dict[str, Any]:
        """Classifies page into layout zones (header/nav/sidebar/main/footer/modal) from geometry."""
        try:
            els = self._raw_elements(session_id)
        except Exception as e:
            return {"success": False, "error": str(e)}
        try:
            vp = self._cdp_evaluate("({width: window.innerWidth, height: window.innerHeight, url: location.href, title: document.title})", session_id)
            vw = float((vp or {}).get("width", 1280) or 1280)
            vh = float((vp or {}).get("height", 800) or 800)
        except Exception:
            vw, vh = 1280.0, 800.0
            vp = {}
        zones: Dict[str, List[Dict[str, Any]]] = {"header": [], "nav": [], "sidebar": [], "main": [], "footer": [], "modal": [], "other": []}
        for e in els:
            r = e.get("rect", {}) or {}
            x = float(r.get("x", 0) or 0)
            y = float(r.get("y", 0) or 0)
            w = float(r.get("width", 0) or 0)
            h = float(r.get("height", 0) or 0)
            role = str(e.get("role", "")).lower()
            item = {"ref_id": e.get("ref_id", ""), "role": e.get("role", ""), "name": str(e.get("name", ""))[:80], "tag": e.get("tag", ""), "rect": r}
            # Modal heuristic: dialog role OR centered overlay covering 20-90% viewport
            if role in ("dialog", "alertdialog") or (w > vw * 0.2 and w < vw * 0.95 and h > vh * 0.15 and h < vh * 0.95 and x > vw * 0.05 and y > vh * 0.03):
                # Only classify as modal if it looks like an overlay (not full-page main)
                if role in ("dialog", "alertdialog") or (w < vw * 0.9 and h < vh * 0.9):
                    zones["modal"].append(item)
                    continue
            if y < vh * 0.14 and w > vw * 0.5:
                zones["header"].append(item)
            elif y > vh * 0.86:
                zones["footer"].append(item)
            elif x < vw * 0.02 + 300 and w < 360 and h > vh * 0.3:
                zones["sidebar"].append(item)
            elif role in ("navigation", "nav", "link") and y < vh * 0.3:
                zones["nav"].append(item)
            elif x > vw * 0.2 and x < vw * 0.85 and y > vh * 0.1 and y < vh * 0.9:
                zones["main"].append(item)
            else:
                zones["other"].append(item)
        summary = {k: len(v) for k, v in zones.items()}
        return {
            "success": True,
            "session_id": session_id,
            "url": (vp or {}).get("url", ""),
            "title": (vp or {}).get("title", ""),
            "viewport": {"width": vw, "height": vh},
            "zone_counts": summary,
            "zones": {k: v[:25] for k, v in zones.items()},
            "hint": "Use ref_id from the relevant zone for clicks (e.g. main-zone refs for content actions).",
        }

    def find_element_smart(self, description: str, session_id: str = "default", limit: int = 5) -> Dict[str, Any]:
        """Spatial-aware find: handles 'bottom-right', 'third row', 'inside pricing' qualifiers."""
        if not description:
            return {"success": False, "error": "description is required"}
        base = self.find_element(description, session_id, limit=50)
        if not base.get("success"):
            return base
        cands = base.get("candidates", []) or []
        desc = description.lower()
        # Viewport for spatial reasoning (best-effort)
        try:
            vp = self._cdp_evaluate("({width: window.innerWidth, height: window.innerHeight})", session_id)
            vw = float((vp or {}).get("width", 1280) or 1280)
            vh = float((vp or {}).get("height", 800) or 800)
        except Exception:
            vw, vh = 1280.0, 800.0
        # Row qualifier: "third row" / "row 3"
        import re
        row_n = None
        m = re.search(r"(first|second|third|fourth|fifth|\d+)(?:st|nd|rd|th)?\s+row", desc)
        if m:
            word = m.group(1)
            mapping = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}
            row_n = mapping.get(word, int(word) if word.isdigit() else None)
        wants = {
            "bottom": "bottom" in desc or "footer" in desc,
            "top": "top" in desc or "header" in desc,
            "left": "left" in desc or "sidebar" in desc,
            "right": "right" in desc,
        }
        for c in cands:
            r = c.get("rect", {}) or {}
            cx = float(r.get("x", 0) or 0) + float(r.get("width", 0) or 0) / 2
            cy = float(r.get("y", 0) or 0) + float(r.get("height", 0) or 0) / 2
            bonus = 0
            if wants["bottom"] and cy > vh * 0.6:
                bonus += 15
            if wants["top"] and cy < vh * 0.35:
                bonus += 15
            if wants["left"] and cx < vw * 0.4:
                bonus += 10
            if wants["right"] and cx > vw * 0.6:
                bonus += 10
            c["score"] = c.get("score", 0) + bonus
            c["_cy"] = cy
        if row_n:
            # Cluster by Y into rows (60px tolerance), pick nth row
            rows: List[List[Dict[str, Any]]] = []
            for c in sorted(cands, key=lambda c: c["_cy"]):
                placed = False
                for row in rows:
                    if abs(row[0]["_cy"] - c["_cy"]) < 60:
                        row.append(c)
                        placed = True
                        break
                if not placed:
                    rows.append([c])
            if 1 <= row_n <= len(rows):
                cands = rows[row_n - 1]
        for c in cands:
            c.pop("_cy", None)
        cands.sort(key=lambda c: -c.get("score", 0))
        return {"success": True, "session_id": session_id, "query": description, "count": min(limit, len(cands)), "candidates": cands[:limit]}

    def text_with_positions(self, session_id: str = "default", max_items: int = 100) -> Dict[str, Any]:
        """OCR-free layout fusion: visible text nodes WITH bounding boxes via CDP."""
        js = f"""(() => {{
          const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          const out = [];
          let node;
          while ((node = walker.nextNode())) {{
            const t = (node.nodeValue || '').trim().replace(/\\s+/g, ' ');
            if (t.length < 3 || out.length >= {int(max_items)}) continue;
            const el = node.parentElement;
            if (!el) continue;
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') continue;
            const r = el.getBoundingClientRect();
            if (r.width <= 0 || r.height <= 0) continue;
            out.push({{ text: t.slice(0, 200), x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), tag: el.tagName.toLowerCase() }});
          }}
          return {{ url: location.href, items: out }};
        }})()"""
        try:
            val = self._cdp_evaluate(js, session_id)
            if not isinstance(val, dict):
                return {"success": False, "error": f"unexpected payload: {val}"}
            return {"success": True, "session_id": session_id, "url": val.get("url", ""), "count": len(val.get("items", [])), "items": val.get("items", [])}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_by_description(self, fields: Dict[str, str], session_id: str = "default") -> Dict[str, Any]:
        """Extracts named fields by text description (no CSS): {{price: 'price in product card'}}."""
        if not fields:
            return {"success": False, "error": "fields dict is required"}
        result: Dict[str, Any] = {}
        for field_name, desc in fields.items():
            found = self.find_element(str(desc), session_id, limit=3)
            cands = found.get("candidates", []) if found.get("success") else []
            result[field_name] = cands[0].get("name", "") if cands else None
        return {"success": True, "session_id": session_id, "data": result}

    # ==========================================
    # Phase 4A. Script Library + Site Adapters (pure code)
    # ==========================================

    def script_library_add(self, name: str, js_code: str, description: str = "", session_id: str = "default") -> Dict[str, Any]:
        """Stores a reusable JS snippet (e.g. 'close cookie banner') in session memory."""
        if not name or not js_code:
            return {"success": False, "error": "name and js_code are required"}
        mem = self._ensure_memory(session_id)
        mem.data[f"script:{name}"] = {"name": name, "js_code": js_code, "description": description, "updated_at": time.time()}
        mem.updated_at = time.time()
        return {"success": True, "session_id": session_id, "name": name, "size_chars": len(js_code)}

    def script_library_list(self, session_id: str = "default") -> List[Dict[str, Any]]:
        mem = self._ensure_memory(session_id)
        return [{"name": k.split("script:", 1)[1], "description": v.get("description", ""), "size_chars": len(v.get("js_code", ""))} for k, v in mem.data.items() if k.startswith("script:")]

    def script_library_get(self, name: str, session_id: str = "default") -> Dict[str, Any]:
        mem = self._ensure_memory(session_id)
        v = mem.data.get(f"script:{name}")
        if not v:
            return {"success": False, "error": f"script '{name}' not found"}
        return {"success": True, "session_id": session_id, **v}

    def script_library_delete(self, name: str, session_id: str = "default") -> Dict[str, Any]:
        mem = self._ensure_memory(session_id)
        existed = mem.data.pop(f"script:{name}", None) is not None
        return {"success": existed, "name": name, "deleted": existed}

    def script_library_run(self, name: str, session_id: str = "default") -> Dict[str, Any]:
        """Runs a stored JS snippet in the live tab via CDP."""
        mem = self._ensure_memory(session_id)
        v = mem.data.get(f"script:{name}")
        if not v:
            return {"success": False, "error": f"script '{name}' not found. Use script_library_list()."}
        try:
            val = self._cdp_evaluate(v["js_code"], session_id)
            self._record_action(session_id, "script_run", name, {}, True, None, 0)
            return {"success": True, "session_id": session_id, "name": name, "result": val}
        except Exception as e:
            self._record_action(session_id, "script_run", name, {}, False, str(e), 0)
            return {"success": False, "error": str(e)}

    def adapter_save(self, site: str, aliases: Dict[str, str], notes: str = "", session_id: str = "default") -> Dict[str, Any]:
        """Saves site-specific selector aliases, e.g. github.com: {{'search box': 'input[name=q]'}}."""
        if not site or not aliases:
            return {"success": False, "error": "site and aliases dict are required"}
        mem = self._ensure_memory(session_id)
        mem.data[f"adapter:{self._norm(site)}"] = {"site": site, "aliases": aliases, "notes": notes, "updated_at": time.time()}
        mem.updated_at = time.time()
        return {"success": True, "session_id": session_id, "site": site, "aliases_count": len(aliases)}

    def adapter_list(self, session_id: str = "default") -> List[Dict[str, Any]]:
        mem = self._ensure_memory(session_id)
        return [{"site": v.get("site", ""), "aliases": v.get("aliases", {}), "notes": v.get("notes", "")} for k, v in mem.data.items() if k.startswith("adapter:")]

    def adapter_resolve(self, site: str, friendly_name: str, session_id: str = "default") -> Dict[str, Any]:
        """Resolves a friendly name → selector for a site (falls back to smart-find suggestion)."""
        mem = self._ensure_memory(session_id)
        v = mem.data.get(f"adapter:{self._norm(site)}")
        if v and friendly_name in v.get("aliases", {}):
            return {"success": True, "site": site, "name": friendly_name, "selector": v["aliases"][friendly_name], "source": "adapter"}
        # Fallback: smart find suggestion
        found = self.find_element(friendly_name, session_id, limit=1)
        cands = found.get("candidates", []) if found.get("success") else []
        return {"success": bool(cands), "site": site, "name": friendly_name, "selector": cands[0].get("ref_id", "") if cands else "", "source": "smart_find_fallback", "candidates": cands[:1]}

    def browser_scroll_harvest(self, selector: str = "", target_count: int = 50, max_scrolls: int = 15, session_id: str = "default") -> Dict[str, Any]:
        """Scrolls until N items loaded (infinite scroll), then counts matches."""
        started = time.time()
        last_count = 0
        stable_rounds = 0
        for i in range(max(1, max_scrolls)):
            try:
                els = self._raw_elements(session_id)
            except Exception as e:
                return {"success": False, "error": str(e), "scrolls": i}
            if selector:
                norm_sel = selector.strip()
                if norm_sel.startswith("@"):
                    count = sum(1 for e in els if str(e.get("ref_id", "")) == norm_sel)
                else:
                    count = sum(1 for e in els if norm_sel.lower() in f"{e.get('name','')} {e.get('role','')} {e.get('tag','')}".lower())
            else:
                count = len(els)
            if count >= target_count:
                return {"success": True, "session_id": session_id, "count": count, "scrolls": i, "elapsed_ms": round((time.time() - started) * 1000)}
            if count == last_count:
                stable_rounds += 1
                if stable_rounds >= 3:
                    break
            else:
                stable_rounds = 0
            last_count = count
            try:
                self.browser_scroll("down", 800, None, session_id)
            except Exception as e:
                return {"success": False, "error": str(e), "scrolls": i, "count": count}
            time.sleep(0.6)
        return {"success": last_count >= target_count, "session_id": session_id, "count": last_count, "scrolls": max_scrolls, "note": "stopped: no new items or max scrolls reached"}

    # ==========================================
    # Adaptive Vision: VLM model → visual, non-VLM → text/OCR understanding (no VLM key needed)
    # ==========================================

    def vision_set_mode(self, mode: str = "auto", session_id: str = "default") -> Dict[str, Any]:
        """Sets how visual tools respond: 'auto' (both), 'visual' (base64 only), 'text' (OCR/text only)."""
        mode = str(mode or "auto").strip().lower()
        if mode not in ("auto", "visual", "text"):
            return {"success": False, "error": "mode must be one of: auto, visual, text"}
        mem = self._ensure_memory(session_id)
        mem.data["vision_mode"] = mode
        mem.updated_at = time.time()
        return {"success": True, "session_id": session_id, "vision_mode": mode}

    def vision_get_mode(self, session_id: str = "default") -> Dict[str, Any]:
        mem = self._ensure_memory(session_id)
        return {"success": True, "session_id": session_id, "vision_mode": mem.data.get("vision_mode", "auto")}

    def _vision_mode(self, session_id: str) -> str:
        try:
            mem = self._ensure_memory(session_id)
            m = str(mem.data.get("vision_mode", "auto")).lower()
            return m if m in ("auto", "visual", "text") else "auto"
        except Exception:
            return "auto"

    def page_see(self, session_id: str = "default", max_items: int = 60, include_screenshot: bool = True) -> Dict[str, Any]:
        """Unified 'see' for any model: VLM uses visual base64, non-VLM uses text/position understanding. No API key needed."""
        mode = self._vision_mode(session_id)
        out: Dict[str, Any] = {"success": True, "session_id": session_id, "vision_mode": mode}
        # 1. Text understanding (always attempted — works as fallback, cheap)
        try:
            tp = self.text_with_positions(session_id, max_items=max_items)
            if tp.get("success"):
                out["text"] = {"url": tp.get("url", ""), "count": tp.get("count", 0), "items": tp.get("items", [])}
            else:
                out["text"] = {"error": tp.get("error", "text capture failed")}
        except Exception as e:
            out["text"] = {"error": str(e)}
        # 2. Layout zones (best-effort)
        try:
            uz = self.page_understand(session_id)
            if uz.get("success"):
                out["zones"] = {"viewport": uz.get("viewport", {}), "zone_counts": uz.get("zone_counts", {})}
                out["title"] = uz.get("title", "")
                out["url"] = uz.get("url", out.get("text", {}).get("url", "") if isinstance(out.get("text"), dict) else "")
        except Exception:
            pass
        # 3. Visual screenshot (skipped entirely in text mode → saves tokens for non-VLM models)
        if mode != "text" and include_screenshot:
            try:
                self._require_extension()
                shot = self.extension_bridge.screenshot(session_id=session_id, save_to_disk=False, return_base64=True)
                b64 = shot.get("base64", "")
                if mode == "visual":
                    out["visual"] = b64
                else:  # auto: include visual + note for VLM models, text models ignore it
                    out["visual"] = b64
                    out["note"] = "VLM model: use 'visual'. Non-VLM model: ignore 'visual', use 'text' + 'zones'."
            except Exception as e:
                out["visual"] = None
                out["visual_error"] = str(e)
        else:
            out["visual"] = None
            out["note"] = "vision_mode='text': visual omitted to save tokens. Use 'text' + 'zones'."
        return out




