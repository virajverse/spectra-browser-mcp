"""Browser automation package export."""

from browser_qa.browser.controller import BrowserController
from browser_qa.browser.page_observer import PageObserver
from browser_qa.browser.session import SessionManager
from browser_qa.browser.actions import classify_action_safety, resolve_locator

__all__ = ["BrowserController", "PageObserver", "SessionManager", "classify_action_safety", "resolve_locator"]
