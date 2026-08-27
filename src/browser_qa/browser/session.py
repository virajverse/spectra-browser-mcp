"""Session lifecycle manager, profile isolation, and navigation scope guards."""

import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from browser_qa.models.session import (
    BrowserMode, SessionConfig, SessionState, SessionStatus
)
from browser_qa.storage.filesystem import FileSystemStore


class SessionManager:
    """Manages active sessions, profile isolation, pause/resume auth handoffs, and origin scope guards."""

    def __init__(self):
        self._sessions: Dict[str, SessionConfig] = {}
        self._states: Dict[str, SessionState] = {}
        self._pause_reasons: Dict[str, Optional[str]] = {}
        self._created_at: Dict[str, float] = {}

    def create_session(
        self,
        session_id: str = "default",
        browser_mode: BrowserMode = BrowserMode.HEADED,
        target_origin: Optional[str] = None,
        allowed_origins: Optional[List[str]] = None,
        profile_id: Optional[str] = None,
        viewport_width: int = 1280,
        viewport_height: int = 800
    ) -> SessionConfig:
        """Creates or reconfigures a session."""
        normalized_allowed = []
        if target_origin:
            normalized_allowed.append(self.get_origin(target_origin))
        if allowed_origins:
            for origin in allowed_origins:
                normalized_allowed.append(self.get_origin(origin))

        config = SessionConfig(
            session_id=session_id,
            browser_mode=browser_mode,
            target_origin=self.get_origin(target_origin) if target_origin else None,
            allowed_origins=list(set(normalized_allowed)),
            profile_id=profile_id,
            viewport_width=viewport_width,
            viewport_height=viewport_height
        )

        self._sessions[session_id] = config
        self._states[session_id] = SessionState.AUTHENTICATING if browser_mode == BrowserMode.HEADED else SessionState.ACTIVE
        self._pause_reasons[session_id] = None
        self._created_at[session_id] = time.time()
        return config

    def get_session(self, session_id: str) -> Optional[SessionConfig]:
        return self._sessions.get(session_id)

    def get_state(self, session_id: str) -> SessionState:
        return self._states.get(session_id, SessionState.CLOSED)

    def pause_session(self, session_id: str, reason: str = "User authentication required") -> bool:
        if session_id in self._sessions:
            self._states[session_id] = SessionState.PAUSED
            self._pause_reasons[session_id] = reason
            return True
        return False

    def resume_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            self._states[session_id] = SessionState.ACTIVE
            self._pause_reasons[session_id] = None
            return True
        return False

    def close_session(self, session_id: str) -> None:
        self._states[session_id] = SessionState.CLOSED
        self._sessions.pop(session_id, None)
        self._pause_reasons.pop(session_id, None)

    @staticmethod
    def get_origin(url_or_origin: str) -> str:
        """Extracts scheme://netloc from URL."""
        if not url_or_origin:
            return ""
        parsed = urlparse(url_or_origin)
        if not parsed.scheme or not parsed.netloc:
            # Maybe passed as example.com or http://example.com
            if "://" not in url_or_origin:
                parsed = urlparse(f"https://{url_or_origin}")
        return f"{parsed.scheme}://{parsed.netloc}".lower().rstrip("/")

    def validate_navigation(self, session_id: str, url: str) -> Tuple[bool, str]:
        """Checks if URL is within allowed origins for this session."""
        config = self._sessions.get(session_id)
        if not config or not config.allowed_origins:
            return True, ""  # No restriction configured

        dest_origin = self.get_origin(url)
        if not dest_origin:
            return True, ""

        if dest_origin in config.allowed_origins:
            return True, ""

        return False, (
            f"Scope Guard: Navigation to '{url}' (origin '{dest_origin}') is blocked. "
            f"Allowed origins for this session are: {config.allowed_origins}"
        )
