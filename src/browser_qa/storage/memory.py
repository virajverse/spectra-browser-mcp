"""In-memory ring buffer storage implementation."""

from collections import defaultdict, deque
from typing import Any, Dict, List, Optional
from browser_qa.config import RING_BUFFER_MAX_SIZE
from browser_qa.models.event import BaseEvent, EventType
from browser_qa.models.network import NetworkTransaction
from browser_qa.models.flow import ConsoleEvent, FlowEvent
from browser_qa.models.finding import Anomaly, Finding
from browser_qa.storage.interface import StorageInterface


class MemoryStore(StorageInterface):
    """Fast, thread-safe in-memory store backed by deques and indexing dicts."""

    def __init__(self, max_buffer_size: int = RING_BUFFER_MAX_SIZE):
        self.max_buffer_size = max_buffer_size
        self._events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.max_buffer_size))
        self._transactions: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.max_buffer_size))
        self._tx_by_id: Dict[str, Dict[str, NetworkTransaction]] = defaultdict(dict)
        self._console_events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.max_buffer_size))
        self._flows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.max_buffer_size))
        self._flows_by_id: Dict[str, Dict[str, FlowEvent]] = defaultdict(dict)
        self._anomalies: Dict[str, List[Anomaly]] = defaultdict(list)
        self._findings: Dict[str, List[Finding]] = defaultdict(list)
        self._profiles: Dict[str, Dict[str, Any]] = {}

    def add_event(self, session_id: str, event: BaseEvent) -> None:
        self._events[session_id].append(event)

    def get_events(self, session_id: str, limit: int = 50, event_type: Optional[EventType] = None) -> List[BaseEvent]:
        events = list(self._events[session_id])
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def add_transaction(self, session_id: str, tx: NetworkTransaction) -> None:
        self._transactions[session_id].append(tx)
        self._tx_by_id[session_id][tx.request_id] = tx

    def get_transaction(self, session_id: str, request_id: str) -> Optional[NetworkTransaction]:
        return self._tx_by_id[session_id].get(request_id)

    def list_transactions(
        self,
        session_id: str,
        limit: int = 50,
        status_code: Optional[int] = None,
        filter_type: Optional[str] = None,
        errors_only: bool = False,
        search_query: Optional[str] = None
    ) -> List[NetworkTransaction]:
        txs = list(self._transactions[session_id])

        # Filter by status code
        if status_code is not None:
            txs = [t for t in txs if t.response and t.response.status == status_code]

        # Filter by errors only (4xx, 5xx, or failed)
        if errors_only:
            txs = [t for t in txs if (t.response and t.response.status >= 400) or t.failure_reason]

        # Filter by DevTools search query
        if search_query:
            q = search_query.lower()
            txs = [t for t in txs if q in t.request.url.lower() or q in t.name.lower()]

        # Filter by DevTools category (Fetch/XHR, Doc, CSS, JS, Font, Img, Media, Socket, Wasm)
        if filter_type and filter_type.lower() != "all":
            ft = filter_type.lower()
            if ft in ("fetch/xhr", "fetch", "xhr"):
                txs = [t for t in txs if t.request.resource_type in ("fetch", "xhr", "xmlhttprequest")]
            elif ft in ("doc", "document"):
                txs = [t for t in txs if t.request.resource_type in ("document", "doc")]
            elif ft in ("css", "stylesheet"):
                txs = [t for t in txs if t.request.resource_type in ("stylesheet", "css")]
            elif ft in ("js", "script"):
                txs = [t for t in txs if t.request.resource_type in ("script", "js")]
            elif ft in ("font", "fonts"):
                txs = [t for t in txs if t.request.resource_type in ("font", "fonts")]
            elif ft in ("img", "image", "images"):
                txs = [t for t in txs if t.request.resource_type in ("image", "img", "png", "jpeg", "webp", "gif", "svg")]
            elif ft in ("media", "video", "audio"):
                txs = [t for t in txs if t.request.resource_type in ("media", "video", "audio")]
            elif ft in ("socket", "websocket"):
                txs = [t for t in txs if t.request.resource_type in ("websocket", "socket")]
            elif ft in ("wasm",):
                txs = [t for t in txs if t.request.resource_type in ("wasm",)]
            elif ft in ("manifest",):
                txs = [t for t in txs if t.request.resource_type in ("manifest",)]
            else:
                txs = [t for t in txs if t.request.resource_type == ft]

        return txs[-limit:]

    def clear_transactions(self, session_id: str) -> None:
        self._transactions[session_id].clear()
        self._tx_by_id[session_id].clear()

    def add_console_event(self, session_id: str, event: ConsoleEvent) -> None:
        self._console_events[session_id].append(event)

    def list_console_events(self, session_id: str, limit: int = 50, min_level: Optional[str] = None) -> List[ConsoleEvent]:
        events = list(self._console_events[session_id])
        if min_level:
            level_hierarchy = {"log": 0, "info": 1, "warn": 2, "error": 3, "pageerror": 4, "unhandledrejection": 4}
            min_score = level_hierarchy.get(min_level.lower(), 0)
            events = [e for e in events if level_hierarchy.get(e.level.lower(), 0) >= min_score]
        return events[-limit:]

    def add_flow(self, session_id: str, flow: FlowEvent) -> None:
        self._flows[session_id].append(flow)
        self._flows_by_id[session_id][flow.flow_id] = flow

    def get_flow(self, session_id: str, flow_id: str) -> Optional[FlowEvent]:
        return self._flows_by_id[session_id].get(flow_id)

    def list_flows(self, session_id: str, limit: int = 20) -> List[FlowEvent]:
        return list(self._flows[session_id])[-limit:]

    def add_anomaly(self, session_id: str, anomaly: Anomaly) -> None:
        self._anomalies[session_id].append(anomaly)

    def list_anomalies(self, session_id: str) -> List[Anomaly]:
        return list(self._anomalies[session_id])

    def add_finding(self, session_id: str, finding: Finding) -> None:
        self._findings[session_id].append(finding)

    def list_findings(self, session_id: str) -> List[Finding]:
        return list(self._findings[session_id])

    def save_profile(self, profile_id: str, state_dict: Dict[str, Any]) -> str:
        self._profiles[profile_id] = state_dict
        return profile_id

    def load_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        return self._profiles.get(profile_id)
