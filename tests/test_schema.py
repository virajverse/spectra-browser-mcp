"""Tests for URL normalization and schema drift detector."""

import json
import sys
from pathlib import Path

# Setup PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from browser_qa.processors.normalizer import normalize_endpoint
from browser_qa.processors.schema import SchemaTracker, diff_schemas, infer_schema


def test_endpoint_normalization():
    # Numeric ID
    ep, q = normalize_endpoint("https://api.example.com/v1/users/42/settings?dark_mode=true")
    assert ep == "/v1/users/:id/settings"
    assert "dark_mode" in q

    # UUID
    ep2, _ = normalize_endpoint("https://api.example.com/orders/550e8400-e29b-41d4-a716-446655440000/items")
    assert ep2 == "/orders/:uuid/items"


def test_schema_drift():
    tracker = SchemaTracker()

    res1 = json.dumps({"id": 1, "name": "Item A", "price": 29.99})
    is_drift, drifts = tracker.record_response("GET", "/items/:id", res1)
    assert not is_drift
    assert len(drifts) == 0

    # Type change: price number -> string
    res2 = json.dumps({"id": 2, "name": "Item B", "price": "29.99"})
    is_drift, drifts = tracker.record_response("GET", "/items/:id", res2)
    assert is_drift
    assert any("price" in d for d in drifts)


if __name__ == "__main__":
    test_endpoint_normalization()
    test_schema_drift()
    print("All normalization & schema drift tests passed successfully! [PASSED]")
