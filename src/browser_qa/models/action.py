"""Action models and safety classifications."""

from enum import Enum
import time
import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    CLICK = "click"
    TYPE = "type"
    FILL = "fill"
    SELECT = "select"
    SCROLL = "scroll"
    PRESS = "press"
    WAIT = "wait"
    NAVIGATE = "navigate"
    UPLOAD = "upload"
    SCREENSHOT = "screenshot"


class ActorType(str, Enum):
    AGENT = "agent"
    HUMAN = "human"
    BROWSER = "browser"


class SafetyLevel(str, Enum):
    READ = "read"
    INTERACT = "interact"
    WRITE = "write"
    DESTRUCTIVE = "destructive"
    AUTH = "auth"


class ActionRecord(BaseModel):
    action_id: str = Field(default_factory=lambda: f"act_{uuid.uuid4().hex[:10]}")
    session_id: str = "default"
    timestamp: float = Field(default_factory=time.time)
    action_type: ActionType
    actor: ActorType = ActorType.AGENT
    target: str = ""
    value: Optional[str] = None  # Always redacted if sensitive
    safety_level: SafetyLevel = SafetyLevel.INTERACT
    status: str = "success"  # "success" or "failed"
    error_message: Optional[str] = None
    observation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
