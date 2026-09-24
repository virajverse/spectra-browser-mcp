"""Browser action execution with priority target resolution and safety guards."""

import re
from typing import Any, Dict, Optional, Tuple
from playwright.sync_api import Locator, Page
from browser_qa.models.action import ActionRecord, ActionType, ActorType, SafetyLevel
from browser_qa.processors.redactor import redact_action_value

DESTRUCTIVE_KEYWORDS = {
    "delete", "remove", "destroy", "drop", "terminate",
    "pay", "purchase", "checkout", "buy", "place order",
    "cancel subscription", "erase"
}


def classify_action_safety(action_type: ActionType, target_str: str, value_str: Optional[str] = None) -> SafetyLevel:
    """Classifies safety level based on action intent and target."""
    combined = f"{target_str} {value_str or ''}".lower()
    for kw in DESTRUCTIVE_KEYWORDS:
        if kw in combined:
            return SafetyLevel.DESTRUCTIVE
    if action_type in (ActionType.TYPE, ActionType.FILL, ActionType.SELECT, ActionType.UPLOAD):
        return SafetyLevel.WRITE
    if action_type in (ActionType.CLICK, ActionType.PRESS, ActionType.SCROLL, ActionType.WAIT):
        return SafetyLevel.INTERACT
    return SafetyLevel.READ


def resolve_locator(page: Page, target: str, ref_map: Dict[str, Dict[str, Any]]) -> Tuple[Optional[Locator], str]:
    """Resolves target in order of priority:

    1. Observation ref (@1, @2)
    2. Accessible role/name (role=button, name="Checkout")
    3. Semantic text (text="Checkout")
    4. Explicit selector / testid / id fallback
    """
    clean_target = target.strip()

    # 1. Observation Ref (@1, @2, etc.)
    if clean_target.startswith("@") or clean_target.isdigit():
        ref_key = clean_target if clean_target.startswith("@") else f"@{clean_target}"
        meta = ref_map.get(ref_key)
        if meta:
            selector = meta.get("selector")
            role = meta.get("role")
            name = meta.get("name")
            # If selector available, try it first
            if selector:
                try:
                    loc = page.locator(selector).first
                    if loc.count() > 0:
                        return loc, f"selector: {selector}"
                except Exception:
                    pass
            # Fallback to role + name
            if role and name:
                try:
                    loc = page.get_by_role(role, name=name).first
                    if loc.count() > 0:
                        return loc, f"role: {role}, name: {name}"
                except Exception:
                    pass
            # Fallback to name/text
            if name:
                try:
                    loc = page.get_by_text(name, exact=False).first
                    if loc.count() > 0:
                        return loc, f"text: {name}"
                except Exception:
                    pass

    # 2. Structured role=..., name=... syntax
    role_match = re.search(r"role\s*=\s*['\"]?([a-zA-Z]+)['\"]?", clean_target, re.IGNORECASE)
    name_match = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", clean_target, re.IGNORECASE)
    if role_match and name_match:
        role = role_match.group(1)
        name = name_match.group(1)
        try:
            loc = page.get_by_role(role, name=name).first
            if loc.count() > 0:
                return loc, f"role: {role}, name: {name}"
        except Exception:
            pass

    # 3. Direct semantic text match
    try:
        loc = page.get_by_text(clean_target, exact=False).first
        if loc.count() > 0:
            return loc, f"text: {clean_target}"
    except Exception:
        pass

    # 4. Safe direct locator / fallback
    try:
        loc = page.locator(clean_target).first
        if loc.count() > 0:
            return loc, f"locator: {clean_target}"
    except Exception:
        pass

    return None, "Target could not be resolved on the active page"
