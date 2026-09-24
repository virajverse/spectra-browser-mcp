"""WebSocket frame tracker and SSE event collector."""

import time
from typing import Dict, List
from playwright.sync_api import WebSocket
from browser_qa.models.event import BaseEvent, EventType
from browser_qa.models.network import SSEEvent, SSEStream, WebSocketFrame, WebSocketSession
from browser_qa.processors.redactor import redact_body_string
from browser_qa.collectors.lifecycle import EventBus


class WebSocketSSECollector:
    """Tracks active WebSocket connections, frame telemetry, and SSE streams."""

    def __init__(self, session_id: str, event_bus: EventBus):
        self.session_id = session_id
        self.event_bus = event_bus
        self._ws_sessions: Dict[str, WebSocketSession] = {}
        self._sse_streams: Dict[str, SSEStream] = {}

    def on_websocket(self, ws: WebSocket) -> None:
        """Invoked when a WebSocket connection opens on the page."""
        ws_session = WebSocketSession(
            session_id=self.session_id,
            url=ws.url,
            created_at=time.time()
        )
        self._ws_sessions[ws_session.ws_id] = ws_session

        def on_frame_sent(payload: str) -> None:
            safe_payload = redact_body_string(str(payload)) or ""
            frame = WebSocketFrame(
                timestamp=time.time(),
                direction="sent",
                payload=safe_payload[:2000],
                size=len(payload)
            )
            ws_session.frames.append(frame)

        def on_frame_received(payload: str) -> None:
            safe_payload = redact_body_string(str(payload)) or ""
            frame = WebSocketFrame(
                timestamp=time.time(),
                direction="received",
                payload=safe_payload[:2000],
                size=len(payload)
            )
            ws_session.frames.append(frame)

        def on_close() -> None:
            ws_session.closed = True

        def on_error(err: str) -> None:
            ws_session.error = str(err)

        ws.on("framesent", on_frame_sent)
        ws.on("framereceived", on_frame_received)
        ws.on("close", on_close)
        ws.on("socketerror", on_error)

        self.event_bus.publish(BaseEvent(
            session_id=self.session_id,
            event_type=EventType.WEBSOCKET,
            payload={"ws_id": ws_session.ws_id, "url": ws.url, "action": "connected"}
        ))

    def record_sse_event(self, stream_url: str, event_name: str, data: str) -> None:
        """Records an SSE event from response streams."""
        stream = None
        for s in self._sse_streams.values():
            if s.url == stream_url and not s.closed:
                stream = s
                break
        if not stream:
            stream = SSEStream(session_id=self.session_id, url=stream_url)
            self._sse_streams[stream.stream_id] = stream

        safe_data = redact_body_string(data) or ""
        stream.events.append(SSEEvent(event_name=event_name, data=safe_data[:2000]))

        self.event_bus.publish(BaseEvent(
            session_id=self.session_id,
            event_type=EventType.SSE,
            payload={"stream_id": stream.stream_id, "event_name": event_name}
        ))

    def list_websockets(self) -> List[WebSocketSession]:
        return list(self._ws_sessions.values())

    def list_sse_streams(self) -> List[SSEStream]:
        return list(self._sse_streams.values())
