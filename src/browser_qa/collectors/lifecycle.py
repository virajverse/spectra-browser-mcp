"""Central Event Bus for real-time telemetry streaming and ring buffer ingestion."""

from typing import Callable, Dict, List
from browser_qa.models.event import BaseEvent
from browser_qa.storage.interface import StorageInterface


class EventBus:
    """Dispatches events from collectors to storage ring-buffers and active subscribers."""

    def __init__(self, storage: StorageInterface):
        self.storage = storage
        self._subscribers: Dict[str, List[Callable[[BaseEvent], None]]] = {}

    def publish(self, event: BaseEvent) -> None:
        """Stores event in per-session storage and notifies active subscribers."""
        self.storage.add_event(event.session_id, event)
        # Notify subscribers
        session_subs = self._subscribers.get(event.session_id, [])
        for sub in session_subs:
            try:
                sub(event)
            except Exception:
                pass

    def subscribe(self, session_id: str, callback: Callable[[BaseEvent], None]) -> None:
        if session_id not in self._subscribers:
            self._subscribers[session_id] = []
        self._subscribers[session_id].append(callback)

    def unsubscribe(self, session_id: str, callback: Callable[[BaseEvent], None]) -> None:
        if session_id in self._subscribers and callback in self._subscribers[session_id]:
            self._subscribers[session_id].remove(callback)
