"""Performance metric aggregator calculating latency percentiles and distribution."""

from collections import defaultdict
import math
from typing import Any, Dict, List
from browser_qa.models.network import NetworkTransaction
from browser_qa.processors.normalizer import normalize_endpoint
from browser_qa.storage.interface import StorageInterface


def calculate_percentile(sorted_data: List[float], percentile: float) -> float:
    if not sorted_data:
        return 0.0
    k = (len(sorted_data) - 1) * percentile
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[int(f)] * (c - k)
    d1 = sorted_data[int(c)] * (k - f)
    return d0 + d1


class PerformanceEngine:
    """Computes endpoint-level and global latency distributions."""

    def __init__(self, storage: StorageInterface):
        self.storage = storage

    def analyze(self, session_id: str) -> Dict[str, Any]:
        txs = self.storage.list_transactions(session_id, limit=500)
        if not txs:
            return {"total_requests": 0, "endpoints": {}}

        endpoint_latencies = defaultdict(list)
        endpoint_status = defaultdict(lambda: {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "failed": 0})

        all_latencies = []
        for tx in txs:
            lat = tx.timing.total_ms
            all_latencies.append(lat)

            norm_path, _ = normalize_endpoint(tx.request.url)
            ep_key = f"{tx.request.method} {norm_path}"
            endpoint_latencies[ep_key].append(lat)

            if tx.response:
                status = tx.response.status
                if 200 <= status < 300:
                    endpoint_status[ep_key]["2xx"] += 1
                elif 300 <= status < 400:
                    endpoint_status[ep_key]["3xx"] += 1
                elif 400 <= status < 500:
                    endpoint_status[ep_key]["4xx"] += 1
                elif status >= 500:
                    endpoint_status[ep_key]["5xx"] += 1
            else:
                endpoint_status[ep_key]["failed"] += 1

        all_latencies.sort()
        global_stats = {
            "total_requests": len(txs),
            "min_ms": round(all_latencies[0], 2) if all_latencies else 0.0,
            "max_ms": round(all_latencies[-1], 2) if all_latencies else 0.0,
            "mean_ms": round(sum(all_latencies) / len(all_latencies), 2) if all_latencies else 0.0,
            "p50_ms": round(calculate_percentile(all_latencies, 0.50), 2),
            "p75_ms": round(calculate_percentile(all_latencies, 0.75), 2),
            "p90_ms": round(calculate_percentile(all_latencies, 0.90), 2),
            "p95_ms": round(calculate_percentile(all_latencies, 0.95), 2),
            "p99_ms": round(calculate_percentile(all_latencies, 0.99), 2),
        }

        endpoint_reports = {}
        for ep, latencies in endpoint_latencies.items():
            latencies.sort()
            endpoint_reports[ep] = {
                "count": len(latencies),
                "status_distribution": endpoint_status[ep],
                "min_ms": round(latencies[0], 2),
                "max_ms": round(latencies[-1], 2),
                "mean_ms": round(sum(latencies) / len(latencies), 2),
                "p50_ms": round(calculate_percentile(latencies, 0.50), 2),
                "p95_ms": round(calculate_percentile(latencies, 0.95), 2),
            }

        return {
            "global": global_stats,
            "endpoints": endpoint_reports
        }
