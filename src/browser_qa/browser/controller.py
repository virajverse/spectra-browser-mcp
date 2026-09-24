"""Playwright browser controller integrating page actions, observers, and collectors."""

import time
from typing import Any, Dict, List, Optional, Tuple
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
from browser_qa.config import SCREENSHOTS_DIR
from browser_qa.models.action import ActionRecord, ActionType, ActorType, SafetyLevel
from browser_qa.models.event import BaseEvent, EventType
from browser_qa.models.page import PageObservation
from browser_qa.models.session import BrowserMode, BrowserTarget, SessionConfig, SessionState
from browser_qa.browser.actions import classify_action_safety, resolve_locator
from browser_qa.browser.page_observer import PageObserver
from browser_qa.browser.registration import BrowserRegistrationManager
from browser_qa.browser.session import SessionManager
from browser_qa.collectors.console import ConsoleCollector
from browser_qa.collectors.lifecycle import EventBus
from browser_qa.collectors.network import NetworkCollector
from browser_qa.collectors.websocket_sse import WebSocketSSECollector
from browser_qa.processors.redactor import redact_action_value
from browser_qa.storage.filesystem import FileSystemStore
from browser_qa.storage.interface import StorageInterface


class BrowserController:
    """Manages browser lifecycle, context per session, action execution, and telemetry attachment."""

    def __init__(
        self,
        storage: StorageInterface,
        event_bus: EventBus,
        registration_mgr: Optional[BrowserRegistrationManager] = None,
        playwright_instance=None  # FIX BUG-02: accept shared playwright to avoid dual sync_playwright() instances
    ):
        self.storage = storage
        self.event_bus = event_bus
        self.session_mgr = SessionManager()
        self.page_observer = PageObserver()
        self.registration_mgr = registration_mgr or BrowserRegistrationManager()

        self._playwright = playwright_instance  # FIX BUG-02: use injected instance if provided
        self._browser: Optional[Browser] = None
        self._contexts: Dict[str, BrowserContext] = {}
        self._pages: Dict[str, Page] = {}
        self._created_pages: Dict[str, bool] = {}
        self._network_collectors: Dict[str, NetworkCollector] = {}
        self._console_collectors: Dict[str, ConsoleCollector] = {}
        self._ws_collectors: Dict[str, WebSocketSSECollector] = {}
        # FIX BUG-08: Track pages that already have telemetry listeners attached
        # Key: (session_id, page id) to prevent duplicate listener registration on select_tab()
        self._instrumented_pages: set = set()

    def _ensure_browser(self, headed: bool = False) -> Browser:
        if not self._playwright:
            self._playwright = sync_playwright().start()
        if not self._browser or self._browser.is_connected() is False:
            self._browser = self._playwright.chromium.launch(
                channel="chrome",
                headless=not headed,
                args=["--disable-dev-shm-usage", "--no-sandbox"]
            )
        return self._browser

    def start_session(
        self,
        session_id: str = "default",
        browser_mode: BrowserMode = BrowserMode.HEADED,
        browser_target: BrowserTarget = BrowserTarget.MANAGED,
        registration_id: Optional[str] = None,
        tab_id: Optional[str] = None,
        target_origin: Optional[str] = None,
        allowed_origins: Optional[List[str]] = None,
        profile_id: Optional[str] = None
    ) -> SessionConfig:
        """Starts or attaches an isolated managed or registered personal browser session."""
        config = self.session_mgr.create_session(
            session_id=session_id,
            browser_mode=browser_mode,
            browser_target=browser_target,
            registration_id=registration_id,
            tab_id=tab_id,
            target_origin=target_origin,
            allowed_origins=allowed_origins,
            profile_id=profile_id
        )

        if browser_target == BrowserTarget.REGISTERED:
            # Mode A — Registered Existing Personal Chrome
            browser, reg, err = self.registration_mgr.get_connected_browser(registration_id)
            if not browser or not reg:
                raise ValueError(
                    f"Registered browser connection unavailable: {err}. "
                    "An explicit browser registration is required before using an existing personal browser. "
                    "Call browser_register_start() followed by browser_register_confirm()."
                )

            # Access user's existing Chrome context
            contexts = browser.contexts
            context = contexts[0] if contexts else browser.new_context()
            self._contexts[session_id] = context

            # Resolve or create the QA tab
            target_page: Optional[Page] = None
            if tab_id and tab_id.startswith("tab_") and tab_id[4:].isdigit():
                idx = int(tab_id[4:])
                if 0 <= idx < len(context.pages):
                    target_page = context.pages[idx]

            if not target_page and target_origin:
                for p in context.pages:
                    if SessionManager.get_origin(p.url) == config.target_origin:
                        target_page = p
                        break

            if not target_page:
                # FIX BUG-09: Removed duplicate if/else — both branches were identical
                target_page = context.new_page()
                self._created_pages[session_id] = True

            self._pages[session_id] = target_page

            # Bring the page to front so the user physically observes actions in real time
            try:
                target_page.bring_to_front()
            except Exception:
                pass

        else:
            # Mode B — Dedicated Managed Browser (Isolated Playwright)
            is_headed = (browser_mode == BrowserMode.HEADED)
            browser = self._ensure_browser(headed=is_headed)

            # Profile state restoration if exists
            storage_state = None
            if profile_id:
                storage_state = FileSystemStore.load_profile_state(profile_id)

            context = browser.new_context(
                viewport={"width": config.viewport_width, "height": config.viewport_height},
                storage_state=storage_state
            )
            self._contexts[session_id] = context

            page = context.new_page()
            self._pages[session_id] = page
            self._created_pages[session_id] = True

        page = self._pages[session_id]

        # Attach telemetry collectors strictly to the designated QA tab
        net_col = NetworkCollector(session_id, self.storage, self.event_bus)
        con_col = ConsoleCollector(session_id, self.storage, self.event_bus)
        ws_col = WebSocketSSECollector(session_id, self.event_bus)

        # FIX BUG-08: Only attach listeners if this page hasn't been instrumented yet
        page_key = (session_id, id(page))
        if page_key not in self._instrumented_pages:
            page.on("request", net_col.on_request)
            page.on("response", net_col.on_response)
            page.on("requestfinished", net_col.on_request_finished)
            page.on("requestfailed", net_col.on_request_failed)
            page.on("console", con_col.on_console_message)
            page.on("pageerror", con_col.on_page_error)
            page.on("websocket", ws_col.on_websocket)
            self._instrumented_pages.add(page_key)

        self._network_collectors[session_id] = net_col
        self._console_collectors[session_id] = con_col
        self._ws_collectors[session_id] = ws_col

        self.event_bus.publish(BaseEvent(
            session_id=session_id,
            event_type=EventType.ACTION,
            payload={
                "action": "session_created",
                "browser_mode": browser_mode.value,
                "browser_target": browser_target.value,
                "registration_id": registration_id
            }
        ))

        return config

    def get_page(self, session_id: str) -> Page:
        if session_id not in self._pages:
            # Explicit policy: use registered browser if active and confirmed, else isolated managed
            conn_browser, reg, _ = self.registration_mgr.get_connected_browser()
            if conn_browser and reg:
                self.start_session(
                    session_id=session_id,
                    browser_mode=BrowserMode.HEADED,
                    browser_target=BrowserTarget.REGISTERED,
                    registration_id=reg.registration_id
                )
            else:
                self.start_session(
                    session_id=session_id,
                    browser_mode=BrowserMode.HEADLESS,
                    browser_target=BrowserTarget.MANAGED
                )
        return self._pages[session_id]

    def navigate(self, session_id: str, url: str) -> Tuple[bool, str]:
        """Navigates to URL respecting scope guard."""
        valid, err = self.session_mgr.validate_navigation(session_id, url)
        if not valid:
            return False, err

        page = self.get_page(session_id)
        try:
            page.goto(url, wait_until="load", timeout=30000)
            self.event_bus.publish(BaseEvent(
                session_id=session_id,
                event_type=EventType.PAGE,
                payload={"action": "navigate", "url": url}
            ))
            return True, f"Navigated successfully to {url}"
        except Exception as e:
            return False, f"Navigation failed: {str(e)}"

    def inspect_page(self, session_id: str) -> PageObservation:
        """Takes semantic snapshot and assigns @refs."""
        page = self.get_page(session_id)
        return self.page_observer.inspect(session_id, page)

    def execute_action(
        self,
        session_id: str,
        action_type: ActionType,
        target: str = "",
        value: Optional[str] = None,
        observation_id: Optional[str] = None,
        confirm_destructive: bool = False
    ) -> Tuple[ActionRecord, str]:
        """Executes a capability action with priority target resolution and safety guards."""
        # 1. Check observation staleness
        valid_obs, obs_err = self.page_observer.validate_observation_id(session_id, observation_id)
        if not valid_obs:
            rec = ActionRecord(
                session_id=session_id,
                action_type=action_type,
                target=target,
                status="failed",
                error_message=obs_err,
                observation_id=observation_id
            )
            return rec, obs_err

        page = self.get_page(session_id)
        ref_map = self.page_observer._ref_maps.get(session_id, {})

        # Resolve semantic context for target (e.g. "@4" -> "Delete Account")
        semantic_target = target
        if target.startswith("@") or target.isdigit():
            ref_key = target if target.startswith("@") else f"@{target}"
            meta = ref_map.get(ref_key)
            if meta:
                semantic_target = f"{meta.get('name', '')} {meta.get('selector', '')} {target}"

        # 2. Check destructive action guard
        safety = classify_action_safety(action_type, semantic_target, value)
        if safety == SafetyLevel.DESTRUCTIVE and not confirm_destructive:
            err_msg = (
                f"Destructive Action Guard: Action '{action_type.value}' on target '{target}' ({semantic_target.strip()}) "
                "is flagged as DESTRUCTIVE. To proceed, call with confirm_destructive=True."
            )
            rec = ActionRecord(
                session_id=session_id,
                action_type=action_type,
                target=target,
                safety_level=safety,
                status="failed",
                error_message=err_msg,
                observation_id=observation_id
            )
            return rec, err_msg

        # 3. Secret-aware masking for action record
        masked_val = redact_action_value(semantic_target, value)
        action_record = ActionRecord(
            session_id=session_id,
            action_type=action_type,
            actor=ActorType.AGENT,
            target=target,
            value=masked_val,
            safety_level=safety,
            observation_id=observation_id
        )

        try:
            if action_type == ActionType.CLICK:
                loc, resolve_info = resolve_locator(page, target, ref_map)
                if not loc:
                    raise ValueError(resolve_info)
                loc.scroll_into_view_if_needed()
                loc.click(timeout=5000)
                msg = f"Clicked element ({resolve_info})"

            elif action_type in (ActionType.TYPE, ActionType.FILL):
                loc, resolve_info = resolve_locator(page, target, ref_map)
                if not loc:
                    raise ValueError(resolve_info)
                loc.scroll_into_view_if_needed()
                loc.fill(value or "", timeout=5000)
                msg = f"Typed into element ({resolve_info})"

            elif action_type == ActionType.SELECT:
                loc, resolve_info = resolve_locator(page, target, ref_map)
                if not loc:
                    raise ValueError(resolve_info)
                loc.select_option(value or "")
                msg = f"Selected '{value}' in element ({resolve_info})"

            elif action_type == ActionType.SCROLL:
                direction = (value or "down").lower()
                amount = 500
                delta_y = amount if direction == "down" else -amount
                page.mouse.wheel(0, delta_y)
                msg = f"Scrolled {direction} by {amount}px"

            elif action_type == ActionType.PRESS:
                key = value or "Enter"
                page.keyboard.press(key)
                msg = f"Pressed key '{key}'"

            elif action_type == ActionType.WAIT:
                ms = int(value) if value and value.isdigit() else 1000
                page.wait_for_timeout(ms)
                msg = f"Waited {ms}ms"

            elif action_type == ActionType.SCREENSHOT:
                filename = f"scr_{session_id}_{int(time.time())}.png"
                scr_path = FileSystemStore.get_screenshot_path(session_id, filename)
                page.screenshot(path=str(scr_path), full_page=False)
                action_record.metadata["screenshot_path"] = str(scr_path)
                msg = f"Screenshot saved to {scr_path}"

            else:
                msg = f"Action {action_type.value} performed"

            action_record.status = "success"
            return action_record, msg

        except Exception as e:
            action_record.status = "failed"
            action_record.error_message = str(e)
            return action_record, f"Action failed: {str(e)}"

    def save_storage_state(self, session_id: str, profile_id: Optional[str] = None) -> str:
        """Persists browser authentication storage state for profile."""
        ctx = self._contexts.get(session_id)
        if not ctx:
            return "No active browser context to save."
        target_profile = profile_id or self.session_mgr.get_session(session_id).profile_id or session_id
        state = ctx.storage_state()
        saved_path = FileSystemStore.save_profile_state(target_profile, state)
        return saved_path

    def wait_for(
        self,
        session_id: str,
        target: str,
        state: str = "visible",
        timeout_ms: int = 15000
    ) -> Tuple[bool, str]:
        """Waits dynamically for target element (@ref, text, or selector) to enter state."""
        page = self.get_page(session_id)
        ref_map = self.page_observer._ref_maps.get(session_id, {})
        loc, resolve_info = resolve_locator(page, target, ref_map)
        if not loc:
            try:
                page.wait_for_selector(target, state=state, timeout=timeout_ms)
                return True, f"Element '{target}' is now {state}"
            except Exception as e:
                return False, f"Timeout waiting for '{target}' to become {state}: {str(e)}"

        try:
            loc.wait_for(state=state, timeout=timeout_ms)
            return True, f"Element ({resolve_info}) is now {state}"
        except Exception as e:
            return False, f"Timeout waiting for ({resolve_info}) to become {state}: {str(e)}"

    def wait_idle(self, session_id: str, timeout_ms: int = 10000) -> Tuple[bool, str]:
        """Waits for network idle or DOM stabilization."""
        page = self.get_page(session_id)
        try:
            page.wait_for_load_state("networkidle", timeout=timeout_ms)
            return True, "Page reached network idle state."
        except Exception:
            try:
                page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
                return True, "Page reached DOM loaded state."
            except Exception as e:
                return False, f"Wait for idle timed out: {str(e)}"

    def list_tabs(self, session_id: str = "default") -> List[Dict[str, Any]]:
        """Lists tabs available in the browser context with safe metadata."""
        context = self._contexts.get(session_id)
        if not context:
            browser, _, _ = self.registration_mgr.get_connected_browser()
            if browser and browser.contexts:
                context = browser.contexts[0]

        if not context:
            return []

        tabs = []
        current_page = self._pages.get(session_id)
        for idx, page in enumerate(context.pages):
            try:
                title = page.title()  # FIX BUG-03 (partial): safe but still synchronous; full fix in service.py
            except Exception:
                title = ""
            url = page.url or ""
            origin = SessionManager.get_origin(url)
            safe_url = url.split("?")[0].split("#")[0] if url else ""

            tabs.append({
                "tab_id": f"tab_{idx}",
                "index": idx,
                "title": title,
                "origin": origin,
                "url": safe_url,
                "active": (page == current_page)
            })
        return tabs

    def select_tab(self, session_id: str, tab_id: str) -> Dict[str, Any]:
        """Switches the session's active page to the designated tab."""
        context = self._contexts.get(session_id)
        if not context:
            browser, _, _ = self.registration_mgr.get_connected_browser()
            if browser and browser.contexts:
                context = browser.contexts[0]
                self._contexts[session_id] = context

        if not context or not context.pages:
            return {"success": False, "error": "No open tabs in browser context."}

        target_page = None
        if tab_id.startswith("tab_") and tab_id[4:].isdigit():
            idx = int(tab_id[4:])
            if 0 <= idx < len(context.pages):
                target_page = context.pages[idx]

        if not target_page:
            return {"success": False, "error": f"Tab '{tab_id}' not found. Call browser_tabs() to list open tabs."}

        config = self.session_mgr.get_session(session_id)
        if config and config.allowed_origins:
            origin = SessionManager.get_origin(target_page.url)
            if origin and origin not in config.allowed_origins:
                return {
                    "success": False,
                    "error": f"Scope Guard: Tab origin '{origin}' is not in allowed origins {config.allowed_origins}."
                }

        self._pages[session_id] = target_page
        if config:
            config.tab_id = tab_id

        # Attach telemetry if collectors exist
        net_col = self._network_collectors.get(session_id)
        con_col = self._console_collectors.get(session_id)
        ws_col = self._ws_collectors.get(session_id)

        if not net_col:
            net_col = NetworkCollector(session_id, self.storage, self.event_bus)
            self._network_collectors[session_id] = net_col
        if not con_col:
            con_col = ConsoleCollector(session_id, self.storage, self.event_bus)
            self._console_collectors[session_id] = con_col
        if not ws_col:
            ws_col = WebSocketSSECollector(session_id, self.event_bus)
            self._ws_collectors[session_id] = ws_col

        # FIX BUG-08: Only attach listeners if this specific page hasn't been instrumented yet
        page_key = (session_id, id(target_page))
        if page_key not in self._instrumented_pages:
            if net_col:
                try:
                    target_page.on("request", net_col.on_request)
                    target_page.on("response", net_col.on_response)
                    target_page.on("requestfinished", net_col.on_request_finished)
                    target_page.on("requestfailed", net_col.on_request_failed)
                except Exception:
                    pass
            if con_col:
                try:
                    target_page.on("console", con_col.on_console_message)
                    target_page.on("pageerror", con_col.on_page_error)
                except Exception:
                    pass
            if ws_col:
                try:
                    target_page.on("websocket", ws_col.on_websocket)
                except Exception:
                    pass
            self._instrumented_pages.add(page_key)

        try:
            target_page.bring_to_front()
        except Exception:
            pass

        # BUG-03 companion: wrap title() in select_tab return too
        try:
            tab_title = target_page.title()
        except Exception:
            tab_title = ""

        return {
            "success": True,
            "session_id": session_id,
            "tab_id": tab_id,
            "title": tab_title,
            "url": target_page.url.split("?")[0] if target_page.url else "",
            "message": f"Tab '{tab_id}' selected as active QA page and brought to front."
        }

    def close_session(self, session_id: str) -> None:
        """Cleans up session resources."""
        config = self.session_mgr.get_session(session_id)
        is_registered = config and config.browser_target == BrowserTarget.REGISTERED

        ctx = self._contexts.pop(session_id, None)
        page = self._pages.pop(session_id, None)

        if is_registered:
            # Never close user's Chrome process or context; close tab only if created specifically for QA
            if page and self._created_pages.pop(session_id, False):
                try:
                    page.close()
                except Exception:
                    pass
        else:
            if ctx:
                try:
                    ctx.close()
                except Exception:
                    pass

        self._created_pages.pop(session_id, None)
        self._network_collectors.pop(session_id, None)
        self._console_collectors.pop(session_id, None)
        self._ws_collectors.pop(session_id, None)
        # FIX BUG-08 cleanup: Remove instrumented page entries for this session to prevent memory leak
        self._instrumented_pages = {
            key for key in self._instrumented_pages if key[0] != session_id
        }
        self.session_mgr.close_session(session_id)
