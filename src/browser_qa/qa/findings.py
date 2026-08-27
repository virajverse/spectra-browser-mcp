"""Finding synthesis engine and deterministic QA report generator."""

import json
import time
from typing import Any, Dict, List, Optional
from browser_qa.evidence.manager import EvidenceManager
from browser_qa.models.finding import AnomalyType, Finding, Severity
from browser_qa.qa.detector import AnomalyDetector
from browser_qa.qa.performance import PerformanceEngine
from browser_qa.qa.severity import score_finding
from browser_qa.storage.interface import StorageInterface


class FindingEngine:
    """Transforms raw anomalies and correlated flow events into evidence-backed findings."""

    def __init__(self, storage: StorageInterface, perf_engine: Optional["PerformanceEngine"] = None):
        self.storage = storage
        self.detector = AnomalyDetector(storage)
        # FIX BUG-07: Reuse injected perf_engine if provided — avoids creating duplicate instance
        self.perf_engine = perf_engine if perf_engine is not None else PerformanceEngine(storage)

    def synthesize_findings(self, session_id: str) -> List[Finding]:
        """Runs the lifecycle: Raw Events -> Anomalies -> Correlated Anomalies -> Findings."""
        anomalies = self.detector.scan(session_id)
        flows = self.storage.list_flows(session_id, limit=50)

        findings: List[Finding] = []

        # 1. Correlate anomalies with user flows
        for anom in anomalies:
            matching_flow = None
            for fl in flows:
                if anom.source_id and any(t.request_id == anom.source_id for t in fl.network_transactions):
                    matching_flow = fl
                    break
                if anom.source_id and any(c.event_id == anom.source_id for c in fl.console_events):
                    matching_flow = fl
                    break

            is_user_flow_blocking = (matching_flow is not None)
            severity, confidence = score_finding(anom.anomaly_type, is_user_flow_blocking)

            # Build reproduction steps
            repro_steps = []
            if matching_flow:
                repro_steps.append(f"1. Navigate to: {matching_flow.page_url_before}")
                repro_steps.append(f"2. Perform action: {matching_flow.action.action_type.value} on '{matching_flow.action.target}'")
                repro_steps.append(f"3. Observe resulting error: {anom.title}")
            else:
                repro_steps.append(f"1. Trigger background request or page event: {anom.title}")

            # Collect evidence
            evidence_items = []
            if anom.source_id:
                tx = self.storage.get_transaction(session_id, anom.source_id)
                if tx:
                    evidence_items.append(EvidenceManager.from_network_transaction(tx))

            if matching_flow:
                evidence_items.append(EvidenceManager.from_flow(matching_flow))
                if matching_flow.screenshot_path:
                    evidence_items.append(EvidenceManager.from_screenshot(matching_flow.screenshot_path))

            affected_eps = [anom.details.get("url")] if "url" in anom.details else []

            finding = Finding(
                session_id=session_id,
                title=f"[{severity.value.upper()}] {anom.title}",
                description=anom.description,
                severity=severity,
                confidence=confidence,
                impact="Breaks user interaction flow" if is_user_flow_blocking else "Degrades application health or telemetry",
                affected_endpoints=affected_eps,
                flow_id=matching_flow.flow_id if matching_flow else None,
                evidence=evidence_items,
                reproduction_steps=repro_steps
            )
            findings.append(finding)
            self.storage.add_finding(session_id, finding)

        return findings

    def generate_report(self, session_id: str, format_type: str = "markdown") -> str:
        """Generates a comprehensive deterministic QA report."""
        findings = self.synthesize_findings(session_id)
        perf_data = self.perf_engine.analyze(session_id)

        if format_type.lower() == "json":
            return json.dumps({
                "session_id": session_id,
                "timestamp": time.time(),
                "performance": perf_data,
                "total_findings": len(findings),
                "findings": [f.model_dump() for f in findings]
            }, indent=2)

        # Markdown format
        md = []
        md.append(f"# Browser QA & Network Intelligence Audit Report")
        md.append(f"**Session ID:** `{session_id}` | **Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
        md.append("")

        # Executive Summary
        md.append("## Executive Summary")
        glob = perf_data.get("global", {})
        md.append(f"- **Total Network Transactions:** {glob.get('total_requests', 0)}")
        md.append(f"- **P50 Latency:** {glob.get('p50_ms', 0)}ms | **P95 Latency:** {glob.get('p95_ms', 0)}ms | **Max:** {glob.get('max_ms', 0)}ms")
        md.append(f"- **Total Findings Flagged:** {len(findings)}")

        crit_count = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high_count = sum(1 for f in findings if f.severity == Severity.HIGH)
        med_count = sum(1 for f in findings if f.severity == Severity.MEDIUM)
        low_count = sum(1 for f in findings if f.severity == Severity.LOW)

        md.append(f"  - Critical: {crit_count} | High: {high_count} | Medium: {med_count} | Low: {low_count}")
        md.append("")

        # Findings Section
        md.append("## Evidence-Backed Findings")
        if not findings:
            md.append("*No defects or anomalies detected during this session. All transactions completed cleanly.*")
            md.append("")
        else:
            for idx, f in enumerate(findings, 1):
                md.append(f"### {idx}. {f.title}")
                md.append(f"- **Severity:** `{f.severity.value.upper()}` | **Confidence:** `{f.confidence * 100:.0f}%`")
                md.append(f"- **Description:** {f.description}")
                md.append(f"- **Impact:** {f.impact}")
                if f.affected_endpoints:
                    md.append(f"- **Affected Endpoints:** {', '.join(f.affected_endpoints)}")
                if f.reproduction_steps:
                    md.append("- **Reproduction Steps:**")
                    for step in f.reproduction_steps:
                        md.append(f"  {step}")
                if f.evidence:
                    md.append("- **Evidence Attached:**")
                    for ev in f.evidence:
                        md.append(f"  - `{ev.evidence_type.upper()}`: {ev.title} (Ref: `{ev.ref_id}`)")
                md.append("")

        # Endpoint Latency Breakdown
        md.append("## Endpoint Latency Breakdown")
        endpoints = perf_data.get("endpoints", {})
        if not endpoints:
            md.append("*No HTTP endpoint calls recorded.*")
        else:
            md.append("| Endpoint | Calls | P50 (ms) | P95 (ms) | 2xx | 4xx | 5xx |")
            md.append("|---|---|---|---|---|---|---|")
            for ep, stats in endpoints.items():
                dist = stats.get("status_distribution", {})
                md.append(f"| `{ep}` | {stats.get('count')} | {stats.get('p50_ms')} | {stats.get('p95_ms')} | {dist.get('2xx', 0)} | {dist.get('4xx', 0)} | {dist.get('5xx', 0)} |")

        md.append("")
        return "\n".join(md)
