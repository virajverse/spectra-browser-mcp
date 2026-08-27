"""QA Anomaly, Finding, and Evidence models."""

from enum import Enum
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyType(str, Enum):
    HTTP_5XX = "http_5xx"
    CORS_ERROR = "cors_error"
    HIGH_LATENCY = "high_latency"
    CONSOLE_ERROR = "console_error"
    SCHEMA_DRIFT = "schema_drift"
    DUPLICATE_REQUEST = "duplicate_request"
    UNHANDLED_EXCEPTION = "unhandled_exception"
    NETWORK_FAILURE = "network_failure"


class Anomaly(BaseModel):
    anomaly_id: str = Field(default_factory=lambda: f"anom_{uuid.uuid4().hex[:10]}")
    session_id: str = "default"
    timestamp: float = Field(default_factory=time.time)
    anomaly_type: AnomalyType
    title: str
    description: str
    source_id: Optional[str] = None  # request_id, console_id, or flow_id
    severity: Severity = Severity.MEDIUM
    confidence: float = 0.8
    details: Dict[str, Any] = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    evidence_id: str = Field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:10]}")
    evidence_type: str  # "network", "console", "screenshot", "flow"
    ref_id: str
    title: str
    snippet: Dict[str, Any] = Field(default_factory=dict)


class Finding(BaseModel):
    finding_id: str = Field(default_factory=lambda: f"fnd_{uuid.uuid4().hex[:10]}")
    session_id: str = "default"
    timestamp: float = Field(default_factory=time.time)
    title: str
    description: str
    severity: Severity = Severity.MEDIUM
    confidence: float = 0.85
    impact: str = ""
    frequency: str = "1/1"
    affected_endpoints: List[str] = Field(default_factory=list)
    flow_id: Optional[str] = None
    evidence: List[EvidenceItem] = Field(default_factory=list)
    reproduction_steps: List[str] = Field(default_factory=list)
