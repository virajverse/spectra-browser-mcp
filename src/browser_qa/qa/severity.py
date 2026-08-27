"""Severity and confidence scoring matrix."""

from typing import Tuple
from browser_qa.models.finding import AnomalyType, Severity


def score_finding(
    anomaly_type: AnomalyType,
    is_user_flow_blocking: bool = False,
    frequency_ratio: float = 1.0
) -> Tuple[Severity, float]:
    """Calculates severity and confidence score based on contextual impact."""
    if anomaly_type == AnomalyType.HTTP_5XX:
        if is_user_flow_blocking:
            return Severity.CRITICAL, 0.96
        return Severity.HIGH, 0.90

    elif anomaly_type == AnomalyType.CORS_ERROR:
        return Severity.HIGH, 0.92

    elif anomaly_type == AnomalyType.UNHANDLED_EXCEPTION:
        if is_user_flow_blocking:
            return Severity.HIGH, 0.94
        return Severity.MEDIUM, 0.85

    elif anomaly_type == AnomalyType.NETWORK_FAILURE:
        if is_user_flow_blocking:
            return Severity.HIGH, 0.90
        return Severity.MEDIUM, 0.80

    elif anomaly_type == AnomalyType.SCHEMA_DRIFT:
        return Severity.MEDIUM, 0.82

    elif anomaly_type == AnomalyType.HIGH_LATENCY:
        if frequency_ratio > 0.5:
            return Severity.HIGH, 0.85
        return Severity.MEDIUM, 0.75

    elif anomaly_type == AnomalyType.DUPLICATE_REQUEST:
        return Severity.LOW, 0.65

    return Severity.LOW, 0.60
