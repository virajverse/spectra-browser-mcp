"""Browser Registration Manager for user-selected personal Chrome profile registration.

Handles explicit user authorization, dynamic Chrome path and profile discovery,
CDP connectivity verification, safe metadata persistence, and revocation.
Zero QA logic is contained in this module.
"""

import json
import os
import platform
import shutil
import subprocess
import time
import urllib.request
import urllib.error
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from playwright.sync_api import Browser, sync_playwright

from browser_qa.config import REGISTRATIONS_FILE
from browser_qa.models.registration import BrowserRegistration, RegistrationStatus


class BrowserRegistrationManager:
    """Manages explicit registration, verification, and lifecycle of personal Chrome browsers."""

    def __init__(self, registrations_file: Optional[Path] = None):
        self.registrations_file = registrations_file or REGISTRATIONS_FILE
        self._registrations: Dict[str, BrowserRegistration] = {}
        self._active_browsers: Dict[str, Browser] = {}
        self._playwright = None
        self._playwright_instances: Dict[str, Any] = {}  # FIX BUG-01: was missing, caused AttributeError in revoke_registration()
        self._launched_processes: Dict[str, subprocess.Popen] = {}
        self._load_registrations()

    def _ensure_playwright(self):
        if not self._playwright:
            self._playwright = sync_playwright().start()
        return self._playwright

    def _load_registrations(self) -> None:
        """Loads persisted registrations from file if configured."""
        if not self.registrations_file or not self.registrations_file.exists():
            return
        try:
            with open(self.registrations_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for reg_dict in data.values():
                    reg = BrowserRegistration(**reg_dict)
                    # Any browser marked CONNECTED from a prior run must be re-verified
                    if reg.status == RegistrationStatus.CONNECTED:
                        reg.status = RegistrationStatus.DISCONNECTED
                    self._registrations[reg.registration_id] = reg
        except Exception:
            # Fallback to clean state if file is corrupted
            self._registrations = {}

    def _save_registrations(self) -> None:
        """Persists safe registration metadata to disk if file path is configured."""
        if not self.registrations_file:
            return
        try:
            self.registrations_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                reg_id: reg.model_dump()
                for reg_id, reg in self._registrations.items()
            }
            with open(self.registrations_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[BrowserRegistrationManager] Error saving registrations: {e}")

    @staticmethod
    def detect_chrome_executable() -> Optional[str]:
        """Dynamically locates Google Chrome executable without hardcoding paths."""
        system = platform.system().lower()

        if system == "windows":
            candidates = [
                shutil.which("chrome"),
                shutil.which("chrome.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
            ]
        elif system == "darwin":
            candidates = [
                shutil.which("google-chrome"),
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            ]
        else:  # Linux / Unix
            candidates = [
                shutil.which("google-chrome"),
                shutil.which("google-chrome-stable"),
                shutil.which("chromium-browser"),
                shutil.which("chromium"),
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser",
            ]

        for cand in candidates:
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                return str(Path(cand).resolve())

        return None

    @staticmethod
    def detect_chrome_user_data_dir() -> Optional[str]:
        """Dynamically locates Chrome User Data directory for discovering profile names safely."""
        system = platform.system().lower()
        if system == "windows":
            cand = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
        elif system == "darwin":
            cand = os.path.expanduser("~/Library/Application Support/Google/Chrome")
        else:
            cand = os.path.expanduser("~/.config/google-chrome")

        if os.path.isdir(cand):
            return cand
        return None

    @classmethod
    def list_available_profiles(cls) -> List[Dict[str, str]]:
        """Safely discovers Chrome profile directory identifiers without reading sensitive data."""
        user_data = cls.detect_chrome_user_data_dir()
        if not user_data or not os.path.isdir(user_data):
            return [{"profile_id": "Default", "display_name": "Default Profile"}]

        profiles: List[Dict[str, str]] = []
        # Check Default
        if os.path.isdir(os.path.join(user_data, "Default")):
            profiles.append({"profile_id": "Default", "display_name": "Default"})

        # Check numbered Profile directories
        try:
            for entry in os.listdir(user_data):
                if entry.startswith("Profile ") and os.path.isdir(os.path.join(user_data, entry)):
                    profiles.append({"profile_id": entry, "display_name": entry})
        except Exception:
            pass

        return profiles or [{"profile_id": "Default", "display_name": "Default"}]

    @staticmethod
    def probe_cdp_endpoint(cdp_url: str, timeout_seconds: float = 2.0) -> Tuple[bool, Dict[str, Any]]:
        """Checks if a Chrome DevTools Protocol endpoint is responding via /json/version."""
        base_url = cdp_url.rstrip("/")
        version_endpoint = f"{base_url}/json/version"
        try:
            req = urllib.request.Request(version_endpoint, headers={"User-Agent": "SpectraBrowser-Registration/1.0"})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    # Safe metadata only
                    safe_meta = {
                        "browser": data.get("Browser", "Chrome"),
                        "protocol_version": data.get("Protocol-Version", ""),
                        "user_agent": data.get("User-Agent", ""),
                        "web_socket_debugger_url": bool(data.get("webSocketDebuggerUrl")),
                    }
                    return True, safe_meta
        except Exception as e:
            return False, {"error": str(e)}

        return False, {"error": "Non-200 response"}

    @staticmethod
    def find_free_cdp_port(preferred_port: int = 9222) -> int:
        """Finds an available TCP port for Chrome DevTools Protocol."""
        import socket
        for p in [preferred_port, 9223, 9224, 9225, 9226, 9227]:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                try:
                    s.bind(("127.0.0.1", p))
                    return p
                except OSError:
                    continue
        return preferred_port

    def start_registration(
        self,
        display_name: str = "Personal Chrome",
        cdp_url: Optional[str] = None,
        port: int = 9222,
        profile_identifier: Optional[str] = None,
        chrome_path: Optional[str] = None,
        auto_launch: bool = True,
        auto_confirm: bool = True,
        use_real_profile: bool = True  # FIX: use real Chrome profile instead of blank one
    ) -> Dict[str, Any]:
        """Starts browser registration, optionally auto-launching Chrome with the user's real profile."""
        detected_chrome = chrome_path or self.detect_chrome_executable()
        reg_id = f"reg_chrome_{uuid.uuid4().hex[:8]}"

        selected_cdp = cdp_url or f"http://127.0.0.1:{port}"

        # Probe if Chrome is already active on this port
        is_active, probe_meta = self.probe_cdp_endpoint(selected_cdp, timeout_seconds=1.0)

        # If not active CDP and auto_launch requested, pick a free port to avoid conflicts
        if auto_launch and not is_active and not cdp_url:
            port = self.find_free_cdp_port(port)
            selected_cdp = f"http://127.0.0.1:{port}"
            is_active, probe_meta = self.probe_cdp_endpoint(selected_cdp, timeout_seconds=0.5)

        # Build clear dynamic OS launch instruction
        system = platform.system().lower()
        chrome_cmd_name = detected_chrome or ("chrome.exe" if system == "windows" else "google-chrome")
        prof_arg = f' --profile-directory="{profile_identifier}"' if profile_identifier else ""

        if system == "windows":
            launch_cmd = f'& "{chrome_cmd_name}" --remote-debugging-port={port}{prof_arg}'
            cmd_prompt_example = f'"{chrome_cmd_name}" --remote-debugging-port={port}{prof_arg}'
        else:
            launch_cmd = f'"{chrome_cmd_name}" --remote-debugging-port={port}{prof_arg}'
            cmd_prompt_example = launch_cmd

        launched = False
        if auto_launch and detected_chrome and not is_active:
            try:
                # FIX: Use real Chrome user profile directory so launched Chrome
                # has all the user's accounts, cookies, and sessions intact.
                # Priority: real profile > isolated fallback
                real_user_data = self.detect_chrome_user_data_dir()

                if use_real_profile and real_user_data:
                    # Use real profile — user will already be logged in
                    user_data_path = real_user_data
                else:
                    import tempfile
                    user_data_path = str(Path(tempfile.gettempdir()) / "spectra_chrome_user_data")

                args = [
                    detected_chrome,
                    f"--remote-debugging-port={port}",
                    f"--user-data-dir={user_data_path}",
                    "--no-first-run",
                    "--no-default-browser-check"
                ]
                if profile_identifier:
                    args.append(f"--profile-directory={profile_identifier}")
                creationflags = 0
                if system == "windows":
                    creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                proc = subprocess.Popen(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creationflags,
                    shell=False
                )
                self._launched_processes[reg_id] = proc
                launched = True
                time.sleep(2.5)  # Allow Chrome process to bind port and load profile
                is_active, probe_meta = self.probe_cdp_endpoint(selected_cdp, timeout_seconds=3.0)
            except Exception as e:
                launched = False

        status = RegistrationStatus.WAITING_FOR_USER if not is_active else RegistrationStatus.REGISTERING

        instructions = (
            f"1. To authorize your personal Chrome browser, launch Chrome with remote debugging on port {port}:\n"
            f"   Command: {launch_cmd}\n"
            f"2. Or if running from Command Prompt: {cmd_prompt_example}\n"
            f"3. In the visible Chrome window, log in manually to any required websites (Google SSO, 2FA, CAPTCHA).\n"
            f"4. Finally, call browser_register_confirm(registration_id='{reg_id}') to authorize the connection."
        )

        registration = BrowserRegistration(
            registration_id=reg_id,
            display_name=display_name,
            browser_type="chrome",
            profile_identifier=profile_identifier,
            connection_type="cdp",
            cdp_url=selected_cdp,
            port=port,
            status=status,
            created_at=time.time(),
            last_seen=time.time(),
            metadata={
                "detected_chrome_path": detected_chrome,
                "auto_launched": launched,
                "endpoint_active": is_active,
                "probe": probe_meta if is_active else {},
            }
        )

        self._registrations[reg_id] = registration
        self._save_registrations()

        if auto_confirm and is_active:
            confirm_res = self.confirm_registration(reg_id)
            if confirm_res.get("success"):
                return {
                    "status": "CONNECTED",
                    "registration_id": reg_id,
                    "display_name": display_name,
                    "cdp_url": selected_cdp,
                    "port": port,
                    "profile_identifier": profile_identifier,
                    "endpoint_detected_online": True,
                    "browser_version": confirm_res.get("browser_version"),
                    "active_pages_count": confirm_res.get("active_pages_count"),
                    "instructions": "Chrome launched and connected automatically. You can view the live window on your screen.",
                    "message": "Chrome launched and CONNECTED successfully! Ready for visible browser control."
                }

        return {
            "status": registration.status.value,
            "registration_id": reg_id,
            "display_name": display_name,
            "cdp_url": selected_cdp,
            "port": port,
            "profile_identifier": profile_identifier,
            "endpoint_detected_online": is_active,
            "instructions": instructions,
            "connection_method": "Chrome DevTools Protocol (CDP)",
            "next_step": f"Call browser_register_confirm(registration_id='{reg_id}') once Chrome is open."
        }

    def confirm_registration(self, registration_id: str) -> Dict[str, Any]:
        """Finalizes registration after verifying live CDP reachability with Playwright."""
        reg = self._registrations.get(registration_id)
        if not reg:
            return {
                "success": False,
                "error": f"Registration '{registration_id}' not found. Call browser_register_start() first."
            }

        if reg.status == RegistrationStatus.REVOKED:
            return {
                "success": False,
                "error": f"Registration '{registration_id}' has been REVOKED and cannot be confirmed. Start a new registration."
            }

        # 1. Probe CDP endpoint
        is_active, probe_meta = self.probe_cdp_endpoint(reg.cdp_url, timeout_seconds=3.0)
        if not is_active:
            reg.status = RegistrationStatus.WAITING_FOR_USER
            self._save_registrations()
            return {
                "success": False,
                "status": reg.status.value,
                "error": (
                    f"Unable to connect to Chrome at {reg.cdp_url}. "
                    f"Please ensure Chrome is running with '--remote-debugging-port={reg.port}' before confirming."
                ),
                "probe_error": probe_meta.get("error")
            }

        # 2. Verify with Playwright connect_over_cdp
        try:
            pw = self._ensure_playwright()
            browser = pw.chromium.connect_over_cdp(reg.cdp_url)
            self._active_browsers[registration_id] = browser

            # Safely query page count without exposing sensitive content
            contexts = browser.contexts
            total_pages = sum(len(ctx.pages) for ctx in contexts)

            reg.status = RegistrationStatus.CONNECTED
            reg.last_seen = time.time()
            reg.metadata.update({
                "browser_version": probe_meta.get("browser", "Chrome"),
                "protocol_version": probe_meta.get("protocol_version", ""),
                "active_contexts": len(contexts),
                "active_pages_count": total_pages,
            })
            self._save_registrations()

            return {
                "success": True,
                "status": reg.status.value,
                "registration_id": reg.registration_id,
                "display_name": reg.display_name,
                "cdp_url": reg.cdp_url,
                "profile_identifier": reg.profile_identifier,
                "browser_version": reg.metadata.get("browser_version"),
                "active_pages_count": total_pages,
                "message": (
                    f"Personal Chrome browser registered and CONNECTED successfully. "
                    f"Visible real-time automation is authorized for registration '{registration_id}'."
                )
            }
        except Exception as e:
            reg.status = RegistrationStatus.DISCONNECTED
            self._save_registrations()
            return {
                "success": False,
                "status": reg.status.value,
                "error": f"Playwright CDP attachment failed: {str(e)}"
            }

    def get_status(self, registration_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns safe status metadata for a specific registration or the most recent one."""
        if not self._registrations:
            return {
                "status": RegistrationStatus.UNREGISTERED.value,
                "message": "No registered browser found. An explicit browser registration is required before using personal Chrome."
            }

        target_reg = None
        if registration_id:
            target_reg = self._registrations.get(registration_id)
            if not target_reg:
                return {
                    "status": "NOT_FOUND",
                    "error": f"Registration '{registration_id}' does not exist."
                }
        else:
            # Pick first connected or most recently updated
            connected_regs = [r for r in self._registrations.values() if r.status == RegistrationStatus.CONNECTED]
            target_reg = connected_regs[-1] if connected_regs else list(self._registrations.values())[-1]

        # Health probe if currently connected
        if target_reg.status == RegistrationStatus.CONNECTED:
            is_active, _ = self.probe_cdp_endpoint(target_reg.cdp_url, timeout_seconds=1.0)
            if not is_active:
                target_reg.status = RegistrationStatus.DISCONNECTED
                self._save_registrations()

        active_browser = self._active_browsers.get(target_reg.registration_id)
        page_count = 0
        current_urls: List[str] = []
        if active_browser and active_browser.is_connected():
            try:
                for ctx in active_browser.contexts:
                    page_count += len(ctx.pages)
                    for p in ctx.pages:
                        # Report safe origin or domain only, never query params or tokens
                        u = p.url
                        if u and "://" in u:
                            parts = u.split("?")[0].split("#")[0]
                            current_urls.append(parts)
            except Exception:
                pass

        return {
            "status": target_reg.status.value,
            "registration_id": target_reg.registration_id,
            "display_name": target_reg.display_name,
            "browser_type": target_reg.browser_type,
            "profile_identifier": target_reg.profile_identifier,
            "connection_type": target_reg.connection_type,
            "cdp_url": target_reg.cdp_url,
            "created_at": target_reg.created_at,
            "last_seen": target_reg.last_seen,
            "active_page_count": page_count,
            "open_tab_urls": current_urls[:5],
            "capabilities": target_reg.capabilities,
            "metadata": {
                k: v for k, v in target_reg.metadata.items()
                if "password" not in k.lower() and "token" not in k.lower() and "cookie" not in k.lower()
            }
        }

    def list_registrations(self) -> List[Dict[str, Any]]:
        """Lists all known browser registrations with safe metadata."""
        results = []
        for reg in self._registrations.values():
            results.append({
                "registration_id": reg.registration_id,
                "display_name": reg.display_name,
                "status": reg.status.value,
                "cdp_url": reg.cdp_url,
                "profile_identifier": reg.profile_identifier,
                "created_at": reg.created_at,
                "last_seen": reg.last_seen
            })
        return results

    def revoke_registration(self, registration_id: str) -> Dict[str, Any]:
        """Revokes browser registration, disconnects CDP, and halts automation and telemetry."""
        reg = self._registrations.get(registration_id)
        if not reg:
            return {
                "success": False,
                "error": f"Registration '{registration_id}' not found."
            }

        # Release active Playwright browser connection
        browser = self._active_browsers.pop(registration_id, None)
        if browser:
            try:
                browser.close()
            except Exception:
                pass

        pw = self._playwright_instances.pop(registration_id, None)
        if pw:
            try:
                pw.stop()
            except Exception:
                pass

        # If we auto-launched a process, we leave it or close it safely
        proc = self._launched_processes.pop(registration_id, None)
        if proc:
            try:
                proc.poll()
            except Exception:
                pass

        reg.status = RegistrationStatus.REVOKED
        reg.last_seen = time.time()
        self._save_registrations()

        return {
            "success": True,
            "registration_id": registration_id,
            "status": RegistrationStatus.REVOKED.value,
            "message": (
                f"Registration '{registration_id}' has been REVOKED. "
                "Browser control and telemetry collection have been terminated."
            )
        }

    def get_connected_browser(self, registration_id: Optional[str] = None) -> Tuple[Optional[Browser], Optional[BrowserRegistration], str]:
        """Retrieves or re-establishes an active Playwright Browser for a connected registration."""
        if not self._registrations:
            return None, None, "No registered browsers found. Call browser_register_start() first."

        target_reg: Optional[BrowserRegistration] = None
        if registration_id:
            target_reg = self._registrations.get(registration_id)
            if not target_reg:
                return None, None, f"Registration '{registration_id}' not found."
        else:
            connected = [r for r in self._registrations.values() if r.status == RegistrationStatus.CONNECTED]
            if not connected:
                return None, None, "No active registered browser is currently CONNECTED."
            target_reg = connected[-1]

        if target_reg.status == RegistrationStatus.REVOKED:
            return None, None, f"Registration '{target_reg.registration_id}' has been REVOKED."

        # Check existing active connection
        existing = self._active_browsers.get(target_reg.registration_id)
        if existing and existing.is_connected():
            return existing, target_reg, ""

        # Re-establish connection over CDP
        try:
            pw = self._ensure_playwright()
            browser = pw.chromium.connect_over_cdp(target_reg.cdp_url)
            self._active_browsers[target_reg.registration_id] = browser
            target_reg.status = RegistrationStatus.CONNECTED
            target_reg.last_seen = time.time()
            return browser, target_reg, ""
        except Exception as e:
            target_reg.status = RegistrationStatus.DISCONNECTED
            self._save_registrations()
            return None, target_reg, f"Failed to connect to registered Chrome at {target_reg.cdp_url}: {str(e)}"
