"""Universal Event model for Browser QA & Network Intelligence."""

from enum import Enum
import time
import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    PAGE = "page"
    ACTION = "action"
    NETWORK = "network"
    CONSOLE = "console"
    WEBSOCKET = "websocket"
    SSE = "sse"
    ANOMALY = "anomaly"
    FINDING = "finding"


class BaseEvent(BaseModel):
    """Base event model shared across all telemetry."""
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    session_id: str = "default"
    timestamp: float = Field(default_factory=time.time)
    event_type: EventType
    payload: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "payload": self.payload,
        }
