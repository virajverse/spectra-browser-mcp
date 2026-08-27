"""URL endpoint fingerprinting and path normalizer."""

import re
import urllib.parse
from typing import Dict, Tuple

UUID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
NUMERIC_ID_PATTERN = re.compile(r"^/|\d{1,12}")
HEX_SLUG_PATTERN = re.compile(r"^[0-9a-f]{16,64}$", re.IGNORECASE)


def normalize_endpoint(raw_url: str) -> Tuple[str, Dict[str, str]]:
    """Normalizes URL into a route pattern and extracts query schema.

    Example:
    'https://api.example.com/users/123/profile?tab=billing'
    -> ('/users/:id/profile', {'tab': 'string'})
    """
    parsed = urllib.parse.urlparse(raw_url)
    path = parsed.path.rstrip("/")
    if not path:
        path = "/"

    segments = path.split("/")
    normalized_segments = []

    for seg in segments:
        if not seg:
            continue
        if UUID_PATTERN.fullmatch(seg):
            normalized_segments.append(":uuid")
        elif seg.isdigit():
            normalized_segments.append(":id")
        elif HEX_SLUG_PATTERN.fullmatch(seg):
            normalized_segments.append(":hash")
        elif len(seg) > 20 and any(c.isdigit() for c in seg) and any(c.isalpha() for c in seg):
            normalized_segments.append(":token")
        else:
            normalized_segments.append(seg)

    normalized_path = "/" + "/".join(normalized_segments)

    # Query params schema
    query_params = urllib.parse.parse_qs(parsed.query)
    query_schema = {k: "string" for k in query_params.keys()}

    return normalized_path, query_schema
