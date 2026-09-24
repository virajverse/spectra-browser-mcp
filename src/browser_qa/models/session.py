"""Session and profile lifecycle models."""

from enum import Enum
import time
from typing import List, Optional
from pydantic import BaseModel, Field


class BrowserMode(str, Enum):
    HEADED = "headed"
    HEADLESS = "headless"


class BrowserTarget(str, Enum):
    REGISTERED = "registered"
    MANAGED = "managed"


class SessionState(str, Enum):
    INITIALIZING = "initializing"
    AUTHENTICATING = "authenticating"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class SessionConfig(BaseModel):
    session_id: str = "default"
    browser_mode: BrowserMode = BrowserMode.HEADED
    browser_target: BrowserTarget = BrowserTarget.MANAGED
    registration_id: Optional[str] = None
    tab_id: Optional[str] = None
    target_origin: Optional[str] = None
    allowed_origins: List[str] = Field(default_factory=list)
    profile_id: Optional[str] = None
    viewport_width: int = 1280
    viewport_height: int = 800
    timeout_ms: int = 30000


class SessionStatus(BaseModel):
    session_id: str
    state: SessionState
    browser_mode: BrowserMode
    browser_target: BrowserTarget = BrowserTarget.MANAGED
    registration_id: Optional[str] = None
    tab_id: Optional[str] = None
    current_url: str = ""
    title: str = ""
    target_origin: Optional[str] = None
    allowed_origins: List[str] = Field(default_factory=list)
    pause_reason: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    active_requests_count: int = 0
    total_transactions: int = 0
    anomalies_count: int = 0
    findings_count: int = 0
