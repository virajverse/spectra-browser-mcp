"""WebSocket Bridge Server enabling Chrome Extension to connect directly to SpectraBrowser MCP."""

import asyncio
import base64
import json
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple
from pathlib import Path
from browser_qa.config import SCREENSHOTS_DIR
from browser_qa.models.event import BaseEvent, EventType
from browser_qa.models.page import FormModel, PageObservation, SemanticElement
from browser_qa.storage.interface import StorageInterface


class ExtensionBridge:
    """Manages WebSocket communication between SpectraBrowser MCP and the Chrome Extension."""

    def __init__(self, storage: StorageInterface, host: str = "127.0.0.1", port: int = 8765):
        self.storage = storage
        self.host = host
        self.port = port
        self._ws = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._is_running = False
        self._last_heartbeat = 0.0
        self._tabs_cache: List[Dict[str, Any]] = []
        self._active_network_tx: Dict[str, Any] = {}

    def start(self):
        """Starts the WebSocket server in a background daemon thread."""
        if self._is_running:
            return

        self._is_running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()

    def _run_server(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def _main():
            import websockets
            try:
                async with websockets.serve(self._handle_client, self.host, self.port):
                    await asyncio.Future()
            except Exception as e:
                pass

        try:
            self._loop.run_until_complete(_main())
        except Exception:
            pass

    async def _handle_client(self, websocket, path=None):
        """Handles connection from the Chrome extension."""
        self._ws = websocket
        self._last_heartbeat = time.time()
        print(f"[ExtensionBridge] Chrome Extension connected from {websocket.remote_address}")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except Exception as e:
                    print(f"[ExtensionBridge] Message processing error: {e}")
        except Exception as e:
            print(f"[ExtensionBridge] Extension disconnected: {e}")
        finally:
            if self._ws == websocket:
                self._ws = None

    async def _process_message(self, data: Dict[str, Any]):
        msg_type = data.get("type")

        # Response to our pending request
        if "id" in data and data["id"] in self._pending_requests:
            fut = self._pending_requests.pop(data["id"])
            if not fut.done():
                if data.get("success"):
                    fut.set_result(data.get("data"))
                else:
                    fut.set_exception(RuntimeError(data.get("error", "Unknown extension error")))
            return

        # Ping
        if msg_type == "ping":
            self._last_heartbeat = time.time()
            if self._ws:
                await self._ws.send(json.dumps({"type": "pong", "timestamp": time.time()}))
            return

        # Extension events
        if msg_type == "event":
            event_type = data.get("eventType")
            payload = data.get("payload", {})

            if event_type == "tab_list_updated":
                self._tabs_cache = payload.get("tabs", [])

            elif event_type == "cdp_event":
                # Handle raw CDP events (Network, Console)
                method = payload.get("method", "")
                params = payload.get("params", {})
                self._handle_cdp_telemetry(method, params)

    def _handle_cdp_telemetry(self, method: str, params: Dict[str, Any], session_id: str = "default"):
        """Pipes live Chrome DevTools telemetry directly into the QA MemoryStore with redaction."""
        try:
            from browser_qa.models.network import NetworkTransaction, RequestData, ResponseData
            from browser_qa.models.flow import ConsoleEvent
            from browser_qa.processors.redactor import Redactor

            # 1. Network Telemetry
            if method == "Network.requestWillBeSent":
                req = params.get("request", {})
                req_id = params.get("requestId", "")
                raw_headers = req.get("headers", {})
                clean_headers = Redactor.redact_headers(raw_headers)
                clean_url = Redactor.redact_url(req.get("url", ""))

                # Parse Initiator (e.g. "+layout.svelte:995", "Preflight", "script")
                init = params.get("initiator", {})
                init_type = init.get("type", "other")
                initiator_str = "Other"
                if init_type == "script":
                    stack = init.get("stack", {})
                    call_frames = stack.get("callFrames", [])
                    if call_frames:
                        top = call_frames[0]
                        url_file = top.get("url", "").split("/")[-1].split("?")[0]
                        line = top.get("lineNumber", 0)
                        initiator_str = f"{url_file}:{line}" if url_file else f"script:{line}"
                    elif init.get("url"):
                        url_file = init.get("url", "").split("/")[-1].split("?")[0]
                        initiator_str = f"{url_file}:{init.get('lineNumber', 0)}"
                    else:
                        initiator_str = "script"
                elif init_type == "preflight":
                    initiator_str = "Preflight"
                elif init_type == "parser":
                    url_file = init.get("url", "").split("/")[-1].split("?")[0]
                    initiator_str = f"{url_file}:{init.get('lineNumber', 0)}" if url_file else "parser"
                else:
                    initiator_str = init_type.capitalize()

                # Parse Name (e.g. "openapi.json", "config", "folders/")
                url_clean = clean_url.split("?")[0].rstrip("/")
                name_str = url_clean.split("/")[-1] if url_clean else clean_url
                if not name_str:
                    name_str = "/"
                if "?" in clean_url:
                    query = clean_url.split("?", 1)[1]
                    name_str = f"{name_str}?{query[:20]}"

                tx = NetworkTransaction(
                    request_id=req_id,
                    session_id=session_id,
                    timestamp=params.get("timestamp", time.time()),
                    name=name_str,
                    request=RequestData(
                        url=clean_url,
                        method=req.get("method", "GET"),
                        resource_type=params.get("type", "other").lower(),
                        headers=clean_headers,
                        initiator=initiator_str,
                        initiator_type=init_type,
                        post_data=Redactor.redact_text(req.get("postData")) if req.get("postData") else None
                    )
                )
                self._active_network_tx[req_id] = tx

            elif method == "Network.responseReceived":
                req_id = params.get("requestId", "")
                resp = params.get("response", {})
                tx = self._active_network_tx.get(req_id)
                if tx:
                    raw_headers = resp.get("headers", {})
                    clean_headers = Redactor.redact_headers(raw_headers)
                    from_disk_cache = resp.get("fromDiskCache", False) or resp.get("fromPrefetchCache", False)
                    from_sw = resp.get("fromServiceWorker", False)
                    encoded_len = resp.get("encodedDataLength", 0)

                    # Size formatted like DevTools
                    if from_disk_cache:
                        size_str = "(disk cache)"
                    elif from_sw:
                        size_str = "(service worker)"
                    elif tx.request.method == "OPTIONS":
                        size_str = "0.0 kB (preflight)"
                    elif encoded_len > 1024 * 1024:
                        size_str = f"{round(encoded_len / (1024 * 1024), 1)} MB"
                    elif encoded_len > 0:
                        size_str = f"{round(encoded_len / 1024, 1)} kB"
                    else:
                        size_str = f"{round(resp.get('dataLength', 200) / 1024, 1)} kB"

                    # Timing calculation
                    t_data = resp.get("timing")
                    timing_obj = TimingData()
                    latency_ms = 1.0
                    if t_data:
                        dns_ms = max(0.0, t_data.get("dnsEnd", 0) - t_data.get("dnsStart", 0))
                        conn_ms = max(0.0, t_data.get("connectEnd", 0) - t_data.get("connectStart", 0))
                        ssl_ms = max(0.0, t_data.get("sslEnd", 0) - t_data.get("sslStart", 0))
                        req_ms = max(0.0, t_data.get("sendEnd", 0) - t_data.get("sendStart", 0))
                        ttfb_ms = max(0.0, t_data.get("receiveHeadersEnd", 0) - t_data.get("sendEnd", 0))
                        total_ms = dns_ms + conn_ms + req_ms + ttfb_ms
                        latency_ms = max(1.0, total_ms)
                        timing_obj = TimingData(
                            dns_ms=round(dns_ms, 1),
                            connect_ms=round(conn_ms, 1),
                            tls_ms=round(ssl_ms, 1),
                            request_ms=round(req_ms, 1),
                            ttfb_ms=round(ttfb_ms, 1),
                            total_ms=round(latency_ms, 1)
                        )
                    else:
                        latency_ms = max(1.0, round((time.time() - tx.timestamp) * 1000, 1))
                        timing_obj = TimingData(total_ms=latency_ms)

                    time_str = f"{int(latency_ms)} ms" if latency_ms < 1000 else f"{round(latency_ms / 1000, 2)} s"

                    tx.response = ResponseData(
                        status=resp.get("status", 200),
                        status_text=resp.get("statusText", "OK"),
                        headers=clean_headers,
                        content_type=resp.get("mimeType", ""),
                        size=resp.get("dataLength", 0),
                        encoded_data_length=encoded_len,
                        from_disk_cache=from_disk_cache,
                        from_service_worker=from_sw
                    )
                    tx.timing = timing_obj
                    tx.from_cache = from_disk_cache
                    tx.from_service_worker = from_sw
                    tx.size_formatted = size_str
                    tx.time_formatted = time_str

                    self.storage.add_transaction(session_id, tx)

            elif method == "Network.loadingFinished":
                req_id = params.get("requestId", "")
                tx = self._active_network_tx.get(req_id)
                if tx and tx.response:
                    encoded_len = params.get("encodedDataLength", tx.response.encoded_data_length)
                    tx.response.encoded_data_length = encoded_len
                    if not tx.from_cache and not tx.from_service_worker and encoded_len > 0:
                        tx.size_formatted = f"{round(encoded_len / 1024, 1)} kB"

            elif method == "Network.loadingFailed":
                req_id = params.get("requestId", "")
                tx = self._active_network_tx.get(req_id)
                if tx:
                    tx.failure_reason = params.get("errorText", "Failed")
                    tx.time_formatted = f"{int(max(1.0, (time.time() - tx.timestamp) * 1000))} ms"
                    self.storage.add_transaction(session_id, tx)

            # 2. Console Telemetry
            elif method == "Console.messageAdded":
                msg = params.get("message", {})
                lvl = msg.get("level", "info").lower()
                if lvl == "warning":
                    lvl = "warn"
                text = Redactor.redact_text(msg.get("text", ""))
                con = ConsoleEvent(
                    session_id=session_id,
                    timestamp=msg.get("timestamp", time.time()),
                    level=lvl,
                    text=text,
                    location=f"{msg.get('url', '')}:{msg.get('line', 0)}"
                )
                self.storage.add_console_event(session_id, con)

            elif method == "Runtime.consoleAPICalled":
                c_type = params.get("type", "log").lower()
                if c_type in ("warning", "warn"):
                    level = "warn"
                elif c_type in ("error", "assert"):
                    level = "error"
                else:
                    level = "info"
                args = [str(a.get("value", a.get("description", ""))) for a in params.get("args", [])]
                text = Redactor.redact_text(" ".join(args))
                con = ConsoleEvent(
                    session_id=session_id,
                    timestamp=time.time(),
                    level=level,
                    text=text,
                    args=[Redactor.redact_text(a) for a in args]
                )
                self.storage.add_console_event(session_id, con)

            elif method == "Runtime.exceptionThrown":
                details = params.get("exceptionDetails", {})
                text = details.get("text", "")
                if "exception" in details and "description" in details["exception"]:
                    text += f": {details['exception']['description']}"
                text = Redactor.redact_text(text)
                con = ConsoleEvent(
                    session_id=session_id,
                    timestamp=time.time(),
                    level="error",
                    text=text,
                    location=f"{details.get('url', '')}:{details.get('lineNumber', 0)}"
                )
                self.storage.add_console_event(session_id, con)
        except Exception as e:
            pass

    def is_connected(self) -> bool:
        """Returns True if Chrome extension is actively connected."""
        return self._ws is not None and (time.time() - self._last_heartbeat < 45)

    def send_command_sync(self, command: str, params: Optional[Dict[str, Any]] = None, timeout: float = 25.0) -> Any:
        """Sends a command to the Chrome extension synchronously."""
        if not self.is_connected():
            raise ConnectionError(
                "Spectra Chrome Extension is not connected. "
                "Please ensure Chrome is open and the SpectraBrowser extension is loaded in chrome://extensions."
            )

        req_id = f"cmd_{uuid.uuid4().hex[:8]}"

        async def _do_send():
            fut = self._loop.create_future()
            self._pending_requests[req_id] = fut
            payload = json.dumps({"id": req_id, "command": command, "params": params or {}})
            await self._ws.send(payload)
            return await asyncio.wait_for(fut, timeout=timeout)

        future = asyncio.run_coroutine_threadsafe(_do_send(), self._loop)
        return future.result(timeout=timeout)

    # ─── High-Level Browser Capabilities ───

    def navigate(self, url: str) -> Dict[str, Any]:
        """Navigates the attached Chrome tab to the specified URL."""
        return self.send_command_sync("navigate", {"url": url}, timeout=30.0)

    def inspect_page(self, session_id: str = "default") -> PageObservation:
        """Extracts semantic DOM tree and @ref assignments from the active tab."""
        data = self.send_command_sync("inspect_page", timeout=15.0)

        elements: List[SemanticElement] = []
        for el in data.get("interactive_elements", []):
            elements.append(SemanticElement(
                ref_id=el.get("ref_id", ""),
                role=el.get("role", "generic"),
                name=el.get("name", ""),
                locator=f"[data-spectra-ref='{el.get('ref_id')}']",
                tag_name=el.get("tag", "div"),
                input_type=el.get("type") or None,
                is_visible=True,
                is_enabled=True,
                bounding_box=el.get("rect", {})
            ))

        forms: List[FormModel] = []
        for f in data.get("forms", []):
            forms.append(FormModel(
                form_id=f.get("form_id", "form_1"),
                action="",
                method="POST",
                inputs=f.get("inputs", [])
            ))

        obs = PageObservation(
            session_id=session_id,
            url=data.get("url", ""),
            title=data.get("title", ""),
            text_preview=data.get("text", "")[:1000],
            interactive_elements=elements,
            forms=forms,
            screen_diagnosis={
                "screen_type": "active_tab",
                "summary": f"Live tab: {data.get('title', '')} with {len(elements)} interactive elements."
            }
        )
        return obs

    def click(self, target: str) -> Dict[str, Any]:
        """Clicks an element by @ref or CSS selector."""
        return self.send_command_sync("click", {"target": target}, timeout=10.0)

    def type(self, target: str, value: str) -> Dict[str, Any]:
        """Types text into an element by @ref or CSS selector."""
        return self.send_command_sync("type", {"target": target, "value": value}, timeout=10.0)

    def screenshot(self, session_id: str = "default") -> str:
        """Captures screenshot of the active Chrome tab and saves to disk."""
        data = self.send_command_sync("screenshot", timeout=10.0)
        data_url = data.get("dataUrl", "")
        if not data_url or "," not in data_url:
            raise RuntimeError("Invalid screenshot data returned from extension.")

        base64_data = data_url.split(",", 1)[1]
        img_bytes = base64.b64decode(base64_data)

        target_dir = SCREENSHOTS_DIR / session_id
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"scr_ext_{session_id}_{int(time.time())}.png"
        filepath = target_dir / filename

        with open(filepath, "wb") as f:
            f.write(img_bytes)

        return str(filepath)

    def list_tabs(self) -> List[Dict[str, Any]]:
        """Lists all open tabs in user's Chrome."""
        return self.send_command_sync("list_tabs", timeout=5.0)

    def attach_tab(self, tab_id: Optional[int] = None) -> Dict[str, Any]:
        """Attaches to a specific tab or the current active tab."""
        return self.send_command_sync("attach_tab", {"tabId": tab_id}, timeout=8.0)

    def detach_tab(self) -> Dict[str, Any]:
        """Detaches from the currently attached tab."""
        return self.send_command_sync("detach_tab", timeout=5.0)

    def press_key(self, key: str = "Enter") -> Dict[str, Any]:
        """Dispatches a keyboard key event (e.g. Enter) to the focused element."""
        return self.send_command_sync("press_key", {"key": key}, timeout=10.0)

    def extract_images(self) -> List[Dict[str, Any]]:
        """Extracts all full-resolution images from the page with base64 data."""
        return self.send_command_sync("extract_images", timeout=25.0)

