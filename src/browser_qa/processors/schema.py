"""JSON response schema inference and drift detection engine."""

import json
from typing import Any, Dict, List, Optional, Tuple


def infer_schema(data: Any) -> Any:
    """Infers structural schema representation from parsed JSON data."""
    if isinstance(data, dict):
        return {k: infer_schema(v) for k, v in data.items()}
    elif isinstance(data, list):
        if not data:
            return []
        return [infer_schema(data[0])]
    elif isinstance(data, bool):
        return "boolean"
    elif isinstance(data, (int, float)):
        return "number"
    elif isinstance(data, str):
        return "string"
    elif data is None:
        return "null"
    return "unknown"


def diff_schemas(old_schema: Any, new_schema: Any, path: str = "") -> List[str]:
    """Compares two schemas and identifies breaking changes or type alterations."""
    drifts = []

    if type(old_schema) != type(new_schema):
        drifts.append(f"Root/Node at '{path or '.'}' changed type from {type(old_schema).__name__} to {type(new_schema).__name__}")
        return drifts

    if isinstance(old_schema, dict) and isinstance(new_schema, dict):
        all_keys = set(old_schema.keys()) | set(new_schema.keys())
        for k in all_keys:
            subpath = f"{path}.{k}" if path else k
            if k not in new_schema:
                drifts.append(f"Missing field at '{subpath}' (previously '{old_schema[k]}')")
            elif k not in old_schema:
                # Additions are non-breaking, can be noted or ignored
                pass
            else:
                drifts.extend(diff_schemas(old_schema[k], new_schema[k], subpath))

    elif isinstance(old_schema, list) and isinstance(new_schema, list):
        if old_schema and new_schema:
            drifts.extend(diff_schemas(old_schema[0], new_schema[0], f"{path}[]"))

    elif isinstance(old_schema, str) and isinstance(new_schema, str):
        if old_schema != new_schema and old_schema != "null" and new_schema != "null":
            drifts.append(f"Type changed at '{path}': '{old_schema}' -> '{new_schema}'")

    return drifts


class SchemaTracker:
    """Tracks schema versions per normalized endpoint and detects breaking drifts."""

    def __init__(self):
        # Maps endpoint_key -> List[schema_dict]
        self._endpoint_schemas: Dict[str, List[Dict[str, Any]]] = {}

    def record_response(self, method: str, endpoint: str, body_str: Optional[str]) -> Tuple[bool, List[str]]:
        """Parses body, infers schema, and detects drift against previous observations."""
        if not body_str:
            return False, []

        trimmed = body_str.strip()
        if not ((trimmed.startswith("{") and trimmed.endswith("}")) or (trimmed.startswith("[") and trimmed.endswith("]"))):
            return False, []

        try:
            parsed = json.loads(trimmed)
        except Exception:
            return False, []

        current_schema = infer_schema(parsed)
        key = f"{method.upper()} {endpoint}"

        history = self._endpoint_schemas.setdefault(key, [])
        if not history:
            history.append(current_schema)
            return False, []

        previous_schema = history[-1]
        drifts = diff_schemas(previous_schema, current_schema)
        history.append(current_schema)

        if drifts:
            return True, drifts
        return False, []
