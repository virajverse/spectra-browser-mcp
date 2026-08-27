"""Action-Network-Console Flow Correlation Engine."""

import time
from typing import List, Optional
from browser_qa.config import CORRELATION_WINDOW_SECONDS
from browser_qa.models.action import ActionRecord
from browser_qa.models.flow import ConsoleEvent, FlowEvent
from browser_qa.models.network import NetworkTransaction
from browser_qa.storage.interface import StorageInterface


class Correlator:
    """Correlates user or agent actions with resulting network transactions and console exceptions."""

    def __init__(self, storage: StorageInterface):
        self.storage = storage

    def correlate(
        self,
        session_id: str,
        action: ActionRecord,
        window_seconds: float = CORRELATION_WINDOW_SECONDS,
        page_url_before: str = "",
        page_url_after: str = "",
        screenshot_path: Optional[str] = None
    ) -> FlowEvent:
        """Finds all network transactions and console events within action's time window."""
        t_start = action.timestamp - 0.1  # slight margin for immediate triggers
        t_end = action.timestamp + window_seconds

        all_txs = self.storage.list_transactions(session_id, limit=100)
        correlated_txs: List[NetworkTransaction] = [
            t for t in all_txs if t_start <= t.timestamp <= t_end
        ]

        all_console = self.storage.list_console_events(session_id, limit=100)
        correlated_console: List[ConsoleEvent] = [
            c for c in all_console if t_start <= c.timestamp <= t_end
        ]

        anomalies: List[str] = []
        for tx in correlated_txs:
            if tx.response and tx.response.status >= 500:
                anomalies.append(f"HTTP {tx.response.status} on {tx.request.method} {tx.request.url}")
            elif tx.failure_reason:
                anomalies.append(f"Network Failure: {tx.failure_reason} on {tx.request.url}")

        for con in correlated_console:
            if con.level in ("error", "pageerror", "unhandledrejection"):
                anomalies.append(f"Console {con.level.upper()}: {con.text[:120]}")

        flow = FlowEvent(
            session_id=session_id,
            action=action,
            network_transactions=correlated_txs,
            console_events=correlated_console,
            page_url_before=page_url_before,
            page_url_after=page_url_after,
            duration_ms=window_seconds * 1000,
            detected_anomalies=anomalies,
            screenshot_path=screenshot_path
        )

        self.storage.add_flow(session_id, flow)
        return flow
