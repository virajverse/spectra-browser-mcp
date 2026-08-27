"""File-system persistent storage for client profiles and screenshots."""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from browser_qa.config import PROFILES_DIR, EVIDENCE_DIR, SCREENSHOTS_DIR


class FileSystemStore:
    """Manages persistent browser profiles and disk evidence storage."""

    @staticmethod
    def get_profile_state_path(profile_id: str) -> Path:
        profile_path = PROFILES_DIR / profile_id / "state"
        profile_path.mkdir(parents=True, exist_ok=True)
        return profile_path / "storage_state.json"

    @classmethod
    def save_profile_state(cls, profile_id: str, state: Dict[str, Any]) -> str:
        file_path = cls.get_profile_state_path(profile_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        return str(file_path)

    @classmethod
    def load_profile_state(cls, profile_id: str) -> Optional[Dict[str, Any]]:
        file_path = cls.get_profile_state_path(profile_id)
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    @classmethod
    def profile_exists(cls, profile_id: str) -> bool:
        return cls.get_profile_state_path(profile_id).exists()

    @staticmethod
    def get_screenshot_path(session_id: str, filename: str) -> Path:
        sess_dir = SCREENSHOTS_DIR / session_id
        sess_dir.mkdir(parents=True, exist_ok=True)
        return sess_dir / filename
