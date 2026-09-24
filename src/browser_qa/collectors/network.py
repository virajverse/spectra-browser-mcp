"""Playwright network lifecycle collector capturing complete request-response transactions."""

import time
import urllib.parse
from typing import Dict, Optional
from playwright.sync_api import Request, Response
from browser_qa.config import BINARY_CONTENT_PREFIXES, MAX_BODY_BYTES
from browser_qa.models.event import BaseEvent, EventType
from browser_qa.models.network import (
    NetworkTransaction, RequestData, ResponseData, SecurityData, TimingData
)
from browser_qa.processors.redactor import redact_body_string, redact_headers
from browser_qa.collectors.lifecycle import EventBus
from browser_qa.storage.interface import StorageInterface


class NetworkCollector:
    """Instruments page network traffic and compiles complete NetworkTransactions."""

    def __init__(self, session_id: str, storage: StorageInterface, event_bus: EventBus):
        self.session_id = session_id
        self.storage = storage
        self.event_bus = event_bus
        # Map internal playwright request pointer -> NetworkTransaction
        self._in_flight: Dict[int, NetworkTransaction] = {}
        self._start_times: Dict[int, float] = {}

    def on_request(self, request: Request) -> None:
        """Invoked when an HTTP request starts."""
        now = time.time()
        req_id = id(request)
        self._start_times[req_id] = now

        # Parse query params
        parsed_url = urllib.parse.urlparse(request.url)
        query_dict = urllib.parse.parse_qs(parsed_url.query)

        # Sanitize headers & post_data
        headers = redact_headers(dict(request.headers))
        # FIX: request.post_data can raise UnicodeDecodeError for binary payloads (gzip, protobuf etc)
        try:
            raw_post = request.post_data
        except Exception:
            raw_post = None
        post_data = redact_body_string(raw_post) if raw_post else None

        req_data = RequestData(
            url=request.url,
            method=request.method,
            resource_type=request.resource_type,
            headers=headers,
            query_params=query_dict,
            post_data=post_data,
            initiator=request.url
        )

        redirect_chain = []
        curr = request.redirected_from
        while curr:
            redirect_chain.append(curr.url)
            curr = curr.redirected_from

        tx = NetworkTransaction(
            session_id=self.session_id,
            timestamp=now,
            request=req_data,
            redirect_chain=redirect_chain
        )
        self._in_flight[req_id] = tx

    def on_response(self, response: Response) -> None:
        """Invoked when response headers arrive."""
        req_id = id(response.request)
        tx = self._in_flight.get(req_id)
        if not tx:
            return

        headers = redact_headers(dict(response.headers))
        content_type = headers.get("content-type", "").lower()
        is_binary = any(content_type.startswith(prefix) for prefix in BINARY_CONTENT_PREFIXES)

        body_str = None
        body_size = 0

        # Safely try fetching body (non-binary and bounded size)
        if not is_binary:
            try:
                raw_bytes = response.body()
                body_size = len(raw_bytes)
                if body_size <= MAX_BODY_BYTES:
                    body_str = raw_bytes.decode("utf-8", errors="replace")
                    body_str = redact_body_string(body_str)
                else:
                    body_str = f"[TRUNCATED: Body size {body_size} bytes exceeds limit of {MAX_BODY_BYTES} bytes]"
            except Exception:
                body_str = None
        else:
            body_size = int(headers.get("content-length", 0)) or 0
            body_str = f"[BINARY CONTENT: {content_type}, size: {body_size} bytes]"

        timing_data = TimingData()
        try:
            raw_timing = response.request.timing
            if raw_timing and isinstance(raw_timing, dict):
                # FIX BUG-10: Playwright timing fields are absolute offsets from navigation start (ms),
                # NOT durations. Must compute deltas to get actual phase durations.
                dns_start = raw_timing.get("domainLookupStart", -1)
                dns_end = raw_timing.get("domainLookupEnd", -1)
                conn_start = raw_timing.get("connectStart", -1)
                conn_end = raw_timing.get("connectEnd", -1)
                tls_start = raw_timing.get("secureConnectionStart", -1)
                req_start = raw_timing.get("requestStart", -1)
                res_start = raw_timing.get("responseStart", -1)
                res_end = raw_timing.get("responseEnd", -1)

                timing_data = TimingData(
                    dns_ms=max(0.0, dns_end - dns_start) if dns_start >= 0 and dns_end >= 0 else 0.0,
                    connect_ms=max(0.0, conn_end - conn_start) if conn_start >= 0 and conn_end >= 0 else 0.0,
                    tls_ms=max(0.0, conn_end - tls_start) if tls_start > 0 and conn_end >= 0 else 0.0,
                    request_ms=max(0.0, res_start - req_start) if req_start >= 0 and res_start >= 0 else 0.0,
                    ttfb_ms=max(0.0, res_start - req_start) if req_start >= 0 and res_start >= 0 else 0.0,
                    download_ms=max(0.0, res_end - res_start) if res_start >= 0 and res_end >= 0 else 0.0,
                    total_ms=max(0.0, res_end - req_start) if req_start >= 0 and res_end >= 0 else 0.0,
                )
        except Exception:
            pass

        security_data = SecurityData(
            has_tls=response.url.startswith("https"),
            protocol=response.headers.get(":protocol", "HTTP/1.1")
        )

        tx.response = ResponseData(
            status=response.status,
            status_text=response.status_text,
            headers=headers,
            content_type=content_type,
            body=body_str,
            size=body_size,
            is_binary=is_binary
        )
        tx.timing = timing_data
        tx.security = security_data
        tx.from_service_worker = response.from_service_worker

    def on_request_finished(self, request: Request) -> None:
        """Invoked when request finishes successfully."""
        req_id = id(request)
        tx = self._in_flight.pop(req_id, None)
        if not tx:
            return

        start = self._start_times.pop(req_id, time.time())
        if tx.timing.total_ms <= 0:
            tx.timing.total_ms = (time.time() - start) * 1000

        self.storage.add_transaction(self.session_id, tx)
        self.event_bus.publish(BaseEvent(
            session_id=self.session_id,
            event_type=EventType.NETWORK,
            payload={"request_id": tx.request_id, "url": tx.request.url, "status": tx.response.status if tx.response else 0, "method": tx.request.method}
        ))

    def on_request_failed(self, request: Request) -> None:
        """Invoked when request fails (CORS, network disconnect, DNS error)."""
        req_id = id(request)
        tx = self._in_flight.pop(req_id, None)
        if not tx:
            return

        start = self._start_times.pop(req_id, time.time())
        failure = request.failure
        tx.failure_reason = failure if failure else "Unknown network error"
        tx.timing.total_ms = (time.time() - start) * 1000

        # Check for CORS error
        if failure and "cors" in failure.lower():
            tx.security.cors_issue = failure

        self.storage.add_transaction(self.session_id, tx)
        self.event_bus.publish(BaseEvent(
            session_id=self.session_id,
            event_type=EventType.NETWORK,
            payload={"request_id": tx.request_id, "url": tx.request.url, "error": tx.failure_reason, "method": tx.request.method}
        ))
