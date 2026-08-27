"""Unified Core Service Layer powering both MCP Server and OpenAPI Bridge."""

import time
from typing import Any, Dict, List, Optional
from browser_qa.browser.controller import BrowserController
from browser_qa.collectors.lifecycle import EventBus
from browser_qa.models.action import ActionType
from browser_qa.models.event import BaseEvent
from browser_qa.models.session import BrowserMode, SessionStatus
from browser_qa.processors.correlator import Correlator
from browser_qa.processors.schema import SchemaTracker
from browser_qa.qa.findings import FindingEngine
from browser_qa.qa.performance import PerformanceEngine
from browser_qa.storage.memory import MemoryStore


class BrowserQAService:
    """Singleton-ready Unified Core Engine for Browser QA and Network Telemetry."""

    def __init__(self):
        self.storage = MemoryStore()
        self.event_bus = EventBus(self.storage)
        self.controller = BrowserController(self.storage, self.event_bus)
        self.correlator = Correlator(self.storage)
        self.schema_tracker = SchemaTracker()
        self.finding_engine = FindingEngine(self.storage)
        self.perf_engine = PerformanceEngine(self.storage)

        # Track stream cursors per session
        self._stream_cursors: Dict[str, int] = {}

    # --- Session & Authentication ---
    def session_create(
        self,
        session_id: str = "default",
        browser_mode: str = "headed",
        target_origin: Optional[str] = None,
        allowed_origins: Optional[List[str]] = None,
        profile_id: Optional[str] = None
    ) -> Dict[str, Any]:
        mode = BrowserMode.HEADED if browser_mode.lower() == "headed" else BrowserMode.HEADLESS
        config = self.controller.start_session(
            session_id=session_id,
            browser_mode=mode,
            target_origin=target_origin,
            allowed_origins=allowed_origins,
            profile_id=profile_id
        )
        return {
            "session_id": config.session_id,
            "state": "authenticating" if mode == BrowserMode.HEADED else "active",
            "browser_mode": config.browser_mode.value,
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
        title = page.title() if page else ""

        txs = self.storage.list_transactions(session_id, limit=500)
        anomalies = self.finding_engine.detector.scan(session_id)
        findings = self.storage.list_findings(session_id)

        status = SessionStatus(
            session_id=session_id,
            state=self.controller.session_mgr.get_state(session_id),
            browser_mode=config.browser_mode,
            current_url=current_url,
            title=title,
            target_origin=config.target_origin,
            allowed_origins=config.allowed_origins,
            pause_reason=self.controller.session_mgr._pause_reasons.get(session_id),
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
        success, msg = self.controller.navigate(session_id, url)
        return {"success": success, "message": msg, "current_url": url if success else ""}

    def browser_click(
        self,
        target: str,
        observation_id: Optional[str] = None,
        session_id: str = "default",
        confirm_destructive: bool = False
    ) -> Dict[str, Any]:
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
        rec, msg = self.controller.execute_action(
            session_id=session_id,
            action_type=ActionType.PRESS,
            value=key
        )
        return {"status": rec.status, "message": msg}

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
        events = self.storage.get_events(session_id, limit=100)
        cursor = self._stream_cursors.get(session_id, 0)

        # Slice events after cursor
        new_events = events[cursor:]
        self._stream_cursors[session_id] = len(events)

        if filter_type:
            new_events = [e for e in new_events if e.event_type.value == filter_type.lower()]

        return [e.to_dict() for e in new_events[-limit:]]

    def network_list(
        self,
        session_id: str = "default",
        filter_type: Optional[str] = None,
        status_code: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        txs = self.storage.list_transactions(session_id, limit=limit, status_code=status_code, filter_type=filter_type)
        return [
            {
                "request_id": t.request_id,
                "timestamp": t.timestamp,
                "method": t.request.method,
                "url": t.request.url,
                "resource_type": t.request.resource_type,
                "status": t.response.status if t.response else 0,
                "latency_ms": round(t.timing.total_ms, 1),
                "content_type": t.response.content_type if t.response else "",
                "is_failed": bool(t.failure_reason)
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
        tx = self.storage.get_transaction(session_id, request_id)
        if not tx:
            return None

        tx_dict = tx.model_dump()
        if not include_request_body:
            tx_dict["request"]["post_data"] = None
        if not include_response_body and tx_dict.get("response"):
            tx_dict["response"]["body"] = None
        elif tx_dict.get("response") and tx_dict["response"].get("body"):
            body = tx_dict["response"]["body"]
            if len(body) > max_body_bytes:
                tx_dict["response"]["body"] = body[:max_body_bytes] + f"\n[TRUNCATED to {max_body_bytes} bytes]"

        return tx_dict

    def network_summary(self, session_id: str = "default") -> Dict[str, Any]:
        return self.perf_engine.analyze(session_id)

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
