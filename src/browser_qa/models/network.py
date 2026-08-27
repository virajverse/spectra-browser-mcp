"""Network transaction, WebSocket, and SSE telemetry models."""

import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RequestData(BaseModel):
    url: str
    method: str = "GET"
    resource_type: str = "other"
    headers: Dict[str, str] = Field(default_factory=dict)
    query_params: Dict[str, Any] = Field(default_factory=dict)
    post_data: Optional[str] = None
    initiator: Optional[str] = None


class ResponseData(BaseModel):
    status: int = 0
    status_text: str = ""
    headers: Dict[str, str] = Field(default_factory=dict)
    content_type: str = ""
    body: Optional[str] = None
    size: int = 0
    is_binary: bool = False


class TimingData(BaseModel):
    dns_ms: float = 0.0
    connect_ms: float = 0.0
    tls_ms: float = 0.0
    request_ms: float = 0.0
    ttfb_ms: float = 0.0
    download_ms: float = 0.0
    total_ms: float = 0.0


class SecurityData(BaseModel):
    protocol: str = ""
    security_state: str = ""
    has_tls: bool = False
    cors_issue: Optional[str] = None


class NetworkTransaction(BaseModel):
    request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    session_id: str = "default"
    timestamp: float = Field(default_factory=time.time)
    request: RequestData
    response: Optional[ResponseData] = None
    timing: TimingData = Field(default_factory=TimingData)
    security: SecurityData = Field(default_factory=SecurityData)
    redirect_chain: List[str] = Field(default_factory=list)
    from_cache: bool = False
    from_service_worker: bool = False
    failure_reason: Optional[str] = None
    normalized_endpoint: Optional[str] = None


class WebSocketFrame(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    direction: str = "received"  # "sent" or "received"
    opcode: str = "text"
    payload: str = ""
    size: int = 0
    is_binary: bool = False


class WebSocketSession(BaseModel):
    ws_id: str = Field(default_factory=lambda: f"ws_{uuid.uuid4().hex[:10]}")
    session_id: str = "default"
    url: str
    created_at: float = Field(default_factory=time.time)
    handshake_status: int = 101
    frames: List[WebSocketFrame] = Field(default_factory=list)
    error: Optional[str] = None
    closed: bool = False
    close_code: Optional[int] = None


class SSEEvent(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    event_id: Optional[str] = None
    event_name: str = "message"
    data: str = ""


class SSEStream(BaseModel):
    stream_id: str = Field(default_factory=lambda: f"sse_{uuid.uuid4().hex[:10]}")
    session_id: str = "default"
    url: str
    created_at: float = Field(default_factory=time.time)
    events: List[SSEEvent] = Field(default_factory=list)
    error: Optional[str] = None
    closed: bool = False
