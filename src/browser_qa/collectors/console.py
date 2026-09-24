"""Console message and uncaught page error collector."""

import time
from typing import Optional
from playwright.sync_api import ConsoleMessage, Error
from browser_qa.models.event import BaseEvent, EventType
from browser_qa.models.flow import ConsoleEvent
from browser_qa.processors.redactor import redact_body_string
from browser_qa.collectors.lifecycle import EventBus
from browser_qa.storage.interface import StorageInterface


class ConsoleCollector:
    """Captures console logs, errors, warnings, and unhandled page exceptions."""

    def __init__(self, session_id: str, storage: StorageInterface, event_bus: EventBus):
        self.session_id = session_id
        self.storage = storage
        self.event_bus = event_bus

    def on_console_message(self, msg: ConsoleMessage) -> None:
        """Handles browser console.log / info / warn / error."""
        text = redact_body_string(msg.text) or ""
        location = f"{msg.location.get('url', '')}:{msg.location.get('lineNumber', '')}" if msg.location else None

        event = ConsoleEvent(
            session_id=self.session_id,
            timestamp=time.time(),
            level=msg.type,
            text=text,
            location=location,
            args=[str(a) for a in msg.args] if msg.args else []
        )
        self.storage.add_console_event(self.session_id, event)
        self.event_bus.publish(BaseEvent(
            session_id=self.session_id,
            event_type=EventType.CONSOLE,
            payload={"event_id": event.event_id, "level": event.level, "text": event.text}
        ))

    def on_page_error(self, error: Error) -> None:
        """Handles uncaught JS exceptions and crash events."""
        err_str = redact_body_string(str(error)) or "Unknown page error"
        event = ConsoleEvent(
            session_id=self.session_id,
            timestamp=time.time(),
            level="pageerror",
            text=err_str,
            location=None
        )
        self.storage.add_console_event(self.session_id, event)
        self.event_bus.publish(BaseEvent(
            session_id=self.session_id,
            event_type=EventType.CONSOLE,
            payload={"event_id": event.event_id, "level": "pageerror", "text": event.text}
        ))
