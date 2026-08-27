"""Persistent Browser Registration models for user-authorized personal Chrome profiles."""

from enum import Enum
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RegistrationStatus(str, Enum):
    UNREGISTERED = "UNREGISTERED"
    REGISTERING = "REGISTERING"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    REVOKED = "REVOKED"


class BrowserRegistration(BaseModel):
    """Model representing an explicitly registered personal or external browser."""
    registration_id: str
    display_name: str = "Personal Chrome"
    browser_type: str = "chrome"
    profile_identifier: Optional[str] = None
    connection_type: str = "cdp"
    cdp_url: str = "http://127.0.0.1:9222"
    port: int = 9222
    status: RegistrationStatus = RegistrationStatus.WAITING_FOR_USER
    created_at: float = Field(default_factory=time.time)
    last_seen: float = Field(default_factory=time.time)
    capabilities: List[str] = Field(default_factory=lambda: [
        "cdp",
        "live_visible_control",
        "semantic_dom",
        "network_telemetry",
        "console_telemetry",
        "tab_management",
    ])
    metadata: Dict[str, Any] = Field(default_factory=dict)
