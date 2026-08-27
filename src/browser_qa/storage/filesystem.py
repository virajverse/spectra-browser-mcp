"""File-system and memory storage for screenshots and session states."""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from browser_qa.config import SCREENSHOTS_DIR


class FileSystemStore:
    """Manages screenshots on disk and session storage states cleanly in memory."""

    _in_memory_states: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def save_profile_state(cls, profile_id: str, state: Dict[str, Any]) -> str:
        """Saves browser session storage state in memory without creating profile folders."""
        cls._in_memory_states[profile_id] = state
        return f"memory://profiles/{profile_id}/state"

    @classmethod
    def load_profile_state(cls, profile_id: str) -> Optional[Dict[str, Any]]:
        """Loads browser session storage state from memory."""
        return cls._in_memory_states.get(profile_id)

    @classmethod
    def profile_exists(cls, profile_id: str) -> bool:
        return profile_id in cls._in_memory_states

    @staticmethod
    def get_screenshot_path(session_id: str, filename: str) -> Path:
        sess_dir = SCREENSHOTS_DIR / session_id
        sess_dir.mkdir(parents=True, exist_ok=True)
        return sess_dir / filename
