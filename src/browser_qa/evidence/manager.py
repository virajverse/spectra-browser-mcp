"""Evidence Manager linking transactions, console logs, and screenshots."""

from typing import Any, Dict, List, Optional
from browser_qa.models.finding import EvidenceItem
from browser_qa.models.flow import ConsoleEvent, FlowEvent
from browser_qa.models.network import NetworkTransaction


class EvidenceManager:
    """Creates structured evidence items for inclusion in Findings and QA reports."""

    @staticmethod
    def from_network_transaction(tx: NetworkTransaction) -> EvidenceItem:
        req_headers_snippet = {k: v for k, v in list(tx.request.headers.items())[:6]}
        res_headers_snippet = {k: v for k, v in list(tx.response.headers.items())[:6]} if tx.response else {}

        snippet: Dict[str, Any] = {
            "method": tx.request.method,
            "url": tx.request.url,
            "status": tx.response.status if tx.response else "FAILED",
            "latency_ms": tx.timing.total_ms,
            "request_headers": req_headers_snippet,
            "response_headers": res_headers_snippet,
        }
        if tx.request.post_data:
            snippet["request_body_snippet"] = tx.request.post_data[:500]
        if tx.response and tx.response.body:
            snippet["response_body_snippet"] = tx.response.body[:1000]
        if tx.failure_reason:
            snippet["failure_reason"] = tx.failure_reason

        return EvidenceItem(
            evidence_type="network",
            ref_id=tx.request_id,
            title=f"{tx.request.method} {tx.request.url}",
            snippet=snippet
        )

    @staticmethod
    def from_console_event(con: ConsoleEvent) -> EvidenceItem:
        return EvidenceItem(
            evidence_type="console",
            ref_id=con.event_id,
            title=f"Console {con.level.upper()}: {con.text[:80]}",
            snippet={
                "level": con.level,
                "text": con.text,
                "location": con.location,
                "timestamp": con.timestamp
            }
        )

    @staticmethod
    def from_screenshot(screenshot_path: str, caption: str = "Page State Screenshot") -> EvidenceItem:
        return EvidenceItem(
            evidence_type="screenshot",
            ref_id=screenshot_path,
            title=caption,
            snippet={"path": screenshot_path}
        )

    @staticmethod
    def from_flow(flow: FlowEvent) -> EvidenceItem:
        return EvidenceItem(
            evidence_type="flow",
            ref_id=flow.flow_id,
            title=f"Flow: {flow.action.action_type.value} on {flow.action.target}",
            snippet={
                "action": flow.action.model_dump(),
                "requests_count": len(flow.network_transactions),
                "console_errors_count": len(flow.console_events),
                "page_url_before": flow.page_url_before,
                "page_url_after": flow.page_url_after,
                "anomalies": flow.detected_anomalies
            }
        )
