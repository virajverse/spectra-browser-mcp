"""Deterministic anomaly detector for HTTP, CORS, latency, and duplicates."""

from collections import defaultdict
from typing import List
from browser_qa.models.finding import Anomaly, AnomalyType, Severity
from browser_qa.models.network import NetworkTransaction
from browser_qa.storage.interface import StorageInterface


class AnomalyDetector:
    """Detects deterministic anomalies across network and console events."""

    def __init__(self, storage: StorageInterface):
        self.storage = storage

    def scan(self, session_id: str) -> List[Anomaly]:
        """Scans session transactions and console logs for anomalies."""
        anomalies: List[Anomaly] = []
        txs = self.storage.list_transactions(session_id, limit=200)
        console_events = self.storage.list_console_events(session_id, limit=200)

        # 1. 5xx and Network / CORS Failures
        url_counts = defaultdict(int)
        for tx in txs:
            url_counts[tx.request.url] += 1

            if tx.response and tx.response.status >= 500:
                anomalies.append(Anomaly(
                    session_id=session_id,
                    anomaly_type=AnomalyType.HTTP_5XX,
                    title=f"HTTP {tx.response.status} Server Error",
                    description=f"{tx.request.method} {tx.request.url} returned status {tx.response.status}",
                    source_id=tx.request_id,
                    severity=Severity.HIGH,
                    confidence=0.95,
                    details={"url": tx.request.url, "status": tx.response.status, "status_text": tx.response.status_text}
                ))

            if tx.security.cors_issue:
                anomalies.append(Anomaly(
                    session_id=session_id,
                    anomaly_type=AnomalyType.CORS_ERROR,
                    title="CORS Policy Failure",
                    description=f"Request to {tx.request.url} failed due to CORS: {tx.security.cors_issue}",
                    source_id=tx.request_id,
                    severity=Severity.HIGH,
                    confidence=0.90,
                    details={"url": tx.request.url, "cors_issue": tx.security.cors_issue}
                ))

            if tx.failure_reason and not tx.security.cors_issue:
                anomalies.append(Anomaly(
                    session_id=session_id,
                    anomaly_type=AnomalyType.NETWORK_FAILURE,
                    title="Network Request Aborted/Failed",
                    description=f"{tx.request.method} {tx.request.url} failed: {tx.failure_reason}",
                    source_id=tx.request_id,
                    severity=Severity.MEDIUM,
                    confidence=0.85,
                    details={"url": tx.request.url, "error": tx.failure_reason}
                ))

            # Latency spike > 3000ms
            if tx.timing.total_ms > 3000:
                anomalies.append(Anomaly(
                    session_id=session_id,
                    anomaly_type=AnomalyType.HIGH_LATENCY,
                    title="High Tail Latency Spike",
                    description=f"Request to {tx.request.url} took {tx.timing.total_ms:.1f}ms (> 3000ms threshold)",
                    source_id=tx.request_id,
                    severity=Severity.MEDIUM,
                    confidence=0.80,
                    details={"url": tx.request.url, "latency_ms": tx.timing.total_ms, "ttfb_ms": tx.timing.ttfb_ms}
                ))

        # 2. Duplicate Identical Requests
        for url, count in url_counts.items():
            if count >= 3 and not any(ext in url for ext in (".png", ".jpg", ".svg", ".css", ".js")):
                anomalies.append(Anomaly(
                    session_id=session_id,
                    anomaly_type=AnomalyType.DUPLICATE_REQUEST,
                    title="Repeated Identical API Calls",
                    description=f"Identical URL requested {count} times within session: {url}",
                    severity=Severity.LOW,
                    confidence=0.70,
                    details={"url": url, "count": count}
                ))

        # 3. Uncaught Exceptions & Console Errors
        for con in console_events:
            if con.level == "pageerror":
                anomalies.append(Anomaly(
                    session_id=session_id,
                    anomaly_type=AnomalyType.UNHANDLED_EXCEPTION,
                    title="Uncaught JavaScript Exception",
                    description=con.text,
                    source_id=con.event_id,
                    severity=Severity.HIGH,
                    confidence=0.90,
                    details={"location": con.location, "error_text": con.text}
                ))
            elif con.level == "error":
                anomalies.append(Anomaly(
                    session_id=session_id,
                    anomaly_type=AnomalyType.CONSOLE_ERROR,
                    title="Browser Console Error",
                    description=con.text,
                    source_id=con.event_id,
                    severity=Severity.MEDIUM,
                    confidence=0.75,
                    details={"location": con.location, "error_text": con.text}
                ))

        return anomalies
