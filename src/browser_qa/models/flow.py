"""Flow event model correlating Actions, Network, and Console events."""

import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from browser_qa.models.action import ActionRecord
from browser_qa.models.network import NetworkTransaction


class ConsoleEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"con_{uuid.uuid4().hex[:10]}")
    session_id: str = "default"
    timestamp: float = Field(default_factory=time.time)
    level: str = "info"  # log, info, warn, error, pageerror, unhandledrejection
    text: str = ""
    location: Optional[str] = None
    args: List[str] = Field(default_factory=list)


class FlowEvent(BaseModel):
    flow_id: str = Field(default_factory=lambda: f"flow_{uuid.uuid4().hex[:10]}")
    session_id: str = "default"
    created_at: float = Field(default_factory=time.time)
    action: ActionRecord
    network_transactions: List[NetworkTransaction] = Field(default_factory=list)
    console_events: List[ConsoleEvent] = Field(default_factory=list)
    page_url_before: str = ""
    page_url_after: str = ""
    duration_ms: float = 0.0
    detected_anomalies: List[str] = Field(default_factory=list)
    screenshot_path: Optional[str] = None
