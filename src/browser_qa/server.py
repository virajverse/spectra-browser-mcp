"""FastMCP Server exposing capability-oriented Browser QA & Network Intelligence tools."""

from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from browser_qa.service import BrowserQAService

mcp = FastMCP("browser-qa")
service = BrowserQAService()


# ==========================================
# 0. Extension & Browser Registration Tools
# ==========================================

@mcp.tool()
def extension_status() -> Dict[str, Any]:
    """Checks whether the SpectraBrowser Chrome Extension is connected to control live Chrome tabs without restarts."""
    return service.extension_status()

@mcp.tool()
def browser_register_start(
    display_name: str = "Personal Chrome",
    cdp_url: Optional[str] = None,
    port: int = 9222,
    profile_identifier: Optional[str] = None,
    chrome_path: Optional[str] = None,
    auto_launch: bool = True,
    auto_confirm: bool = True
) -> Dict[str, Any]:
    """Starts the browser registration process for a personal Chrome profile, auto-launches Chrome, and connects.

    Discovers Chrome installation dynamically and launches Chrome with CDP port visible on screen.
    Never extracts passwords or credentials. Set auto_confirm=False if manual step-by-step confirmation is preferred.
    """
    return service.browser_register_start(
        display_name=display_name,
        cdp_url=cdp_url,
        port=port,
        profile_identifier=profile_identifier,
        chrome_path=chrome_path,
        auto_launch=auto_launch,
        auto_confirm=auto_confirm
    )


@mcp.tool()
def browser_register_status(registration_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves safe registration state, connection health, and profile metadata without sensitive credentials."""
    return service.browser_register_status(registration_id)


@mcp.tool()
def browser_register_confirm(registration_id: str) -> Dict[str, Any]:
    """Finalizes browser registration after verifying that Chrome CDP connection is live and user-authorized."""
    return service.browser_register_confirm(registration_id)


@mcp.tool()
def browser_register_revoke(registration_id: str) -> Dict[str, Any]:
    """Explicitly revokes registered browser, detaches automation, and releases all telemetry collection."""
    return service.browser_register_revoke(registration_id)


@mcp.tool()
def browser_register_list() -> List[Dict[str, Any]]:
    """Lists all registered browser configurations and their connection statuses."""
    return service.browser_register_list()


@mcp.tool()
def browser_tabs(session_id: str = "default") -> List[Dict[str, Any]]:
    """Returns safe metadata (tab_id, title, origin, active) for open tabs in the registered browser context."""
    return service.browser_tabs(session_id)


@mcp.tool()
def browser_select_tab(tab_id: str, session_id: str = "default") -> Dict[str, Any]:
    """Selects an open tab in the registered Chrome context to be the active QA target and brings it to front."""
    return service.browser_select_tab(tab_id, session_id)


# ==========================================
# 1. Session & Authentication Tools
# ==========================================

@mcp.tool()
def session_create(
    session_id: str = "default",
    browser_mode: str = "headed",
    browser_target: str = "managed",
    registration_id: Optional[str] = None,
    tab_id: Optional[str] = None,
    target_origin: Optional[str] = None,
    allowed_origins: Optional[List[str]] = None,
    profile_id: Optional[str] = None
) -> Dict[str, Any]:
    """Initializes or attaches a browser session.

    Set browser_target='registered' to control an explicitly registered personal Chrome profile.
    Set browser_target='managed' (default) to run an isolated Playwright-managed browser.
    Set browser_mode='headed' if manual user authentication, Google SSO, or CAPTCHA is required.
    Set target_origin and allowed_origins to restrict navigation scope (e.g. ['https://app.example.com']).
    """
    return service.session_create(
        session_id=session_id,
        browser_mode=browser_mode,
        browser_target=browser_target,
        registration_id=registration_id,
        tab_id=tab_id,
        target_origin=target_origin,
        allowed_origins=allowed_origins,
        profile_id=profile_id
    )


@mcp.tool()
def session_status(session_id: str = "default") -> Dict[str, Any]:
    """Retrieves session state, active URL, pause reason, origin compliance, and telemetry counts."""
    return service.session_status(session_id)


@mcp.tool()
def session_pause(session_id: str = "default", reason: str = "User authentication required") -> Dict[str, Any]:
    """Pauses agent automation to allow human user to complete manual login, 2FA, or CAPTCHA in headed browser."""
    return service.session_pause(session_id, reason)


@mcp.tool()
def session_ask_human(
    question: str,
    options: Optional[List[str]] = None,
    context_summary: Optional[str] = None,
    session_id: str = "default"
) -> Dict[str, Any]:
    """Pauses automation to ask user for decisions, choices, or instructions before taking action."""
    return service.session_ask_human(
        question=question,
        options=options,
        context_summary=context_summary,
        session_id=session_id
    )


@mcp.tool()
def session_resume(session_id: str = "default", user_decision: Optional[str] = None) -> Dict[str, Any]:
    """Resumes agent automation after human user confirms decision or login completion."""
    return service.session_resume(session_id, user_decision)


@mcp.tool()
def session_save(session_id: str = "default", profile_id: Optional[str] = None) -> Dict[str, Any]:
    """Persists browser authentication storage state (cookies & localStorage) for profile reuse."""
    return service.session_save(session_id, profile_id)


@mcp.tool()
def session_close(session_id: str = "default") -> Dict[str, Any]:
    """Closes browser context and releases resources."""
    return service.session_close(session_id)


# ==========================================
# 2. Browser Navigation & Safe Interaction
# ==========================================

@mcp.tool()
def browser_navigate(url: str, session_id: str = "default") -> Dict[str, Any]:
    """Navigates to URL within session allowed origins."""
    return service.browser_navigate(url, session_id)


@mcp.tool()
def browser_reload(ignore_cache: bool = True, session_id: str = "default") -> Dict[str, Any]:
    """Reloads the active tab with DevTools Network & Console monitoring enabled to capture complete traffic from start."""
    return service.browser_reload(ignore_cache=ignore_cache, session_id=session_id)


@mcp.tool()
def browser_click(
    target: str,
    observation_id: Optional[str] = None,
    session_id: str = "default",
    confirm_destructive: bool = False
) -> Dict[str, Any]:
    """Clicks an element with priority resolution: @ref (e.g. '@1') -> accessible role/name -> text -> locator.

    Correlates resulting network requests and console errors into a FlowEvent.
    Guards against stale observation_ids and destructive actions (delete, pay, cancel).
    """
    return service.browser_click(
        target=target,
        observation_id=observation_id,
        session_id=session_id,
        confirm_destructive=confirm_destructive
    )


@mcp.tool()
def browser_type(
    target: str,
    text: str,
    observation_id: Optional[str] = None,
    clear: bool = False,
    session_id: str = "default"
) -> Dict[str, Any]:
    """Fills/types text into an input element. Secret values (passwords, tokens) are automatically redacted."""
    return service.browser_type(
        target=target,
        text=text,
        observation_id=observation_id,
        clear=clear,
        session_id=session_id
    )


@mcp.tool()
def browser_select(
    target: str,
    option: str,
    observation_id: Optional[str] = None,
    session_id: str = "default"
) -> Dict[str, Any]:
    """Selects an option in a dropdown element."""
    return service.browser_select(
        target=target,
        option=option,
        observation_id=observation_id,
        session_id=session_id
    )


@mcp.tool()
def browser_scroll(direction: str = "down", amount: int = 500, target: Optional[str] = None, session_id: str = "default") -> Dict[str, Any]:
    """Scrolls page viewport up or down, or scrolls a specific element (@ref or CSS selector) into view."""
    return service.browser_scroll(direction, amount, target, session_id)


@mcp.tool()
def browser_press(key: str = "Enter", session_id: str = "default") -> Dict[str, Any]:
    """Simulates keyboard key press (e.g. 'Enter', 'Tab', 'Escape')."""
    return service.browser_press(key, session_id)


@mcp.tool()
def browser_extract_images(
    save_dir: Optional[str] = None,
    return_base64: bool = False,
    session_id: str = "default"
) -> Dict[str, Any]:
    """Extracts all full-resolution images from the active webpage and downloads them in original quality without screenshots."""
    return service.browser_extract_images(save_dir=save_dir, return_base64=return_base64, session_id=session_id)


@mcp.tool()
def browser_wait(ms: int = 1000, session_id: str = "default") -> Dict[str, Any]:
    """Waits for specified milliseconds."""
    return service.browser_wait(ms, session_id)


@mcp.tool()
def browser_wait_for(
    target: str,
    state: str = "visible",
    timeout_ms: int = 15000,
    session_id: str = "default"
) -> Dict[str, Any]:
    """Waits dynamically for target element (@ref, text, or selector) to become visible, hidden, or attached."""
    return service.browser_wait_for(target, state, timeout_ms, session_id)


@mcp.tool()
def browser_wait_idle(timeout_ms: int = 10000, session_id: str = "default") -> Dict[str, Any]:
    """Waits for network requests to settle and page DOM mutations to finish."""
    return service.browser_wait_idle(timeout_ms, session_id)


@mcp.tool()
def browser_screenshot(
    session_id: str = "default",
    full_page: bool = False,
    save_to_disk: bool = False,
    return_base64: bool = True
) -> Dict[str, Any]:
    """Captures screenshot with Pure In-Memory Ephemeral Stream (0 disk bytes used by default). Set save_to_disk=True only if local file artifact is needed."""
    return service.browser_screenshot(session_id=session_id, full_page=full_page, save_to_disk=save_to_disk, return_base64=return_base64)


# ==========================================
# 3. Page Observation Tools
# ==========================================

@mcp.tool()
def page_inspect(session_id: str = "default") -> Dict[str, Any]:
    """Generates structured semantic snapshot with new observation_id and assigned @ref IDs (@1, @2).

    Does NOT dump 2MB raw HTML. Returns headings, visible text summary, and clickable widgets.
    """
    return service.page_inspect(session_id)


@mcp.tool()
def page_forms(session_id: str = "default") -> List[Dict[str, Any]]:
    """Returns detected forms, fields, types, placeholders, and current values."""
    return service.page_forms(session_id)


@mcp.tool()
def page_text(session_id: str = "default", max_chars: int = 3000) -> Dict[str, Any]:
    """Extracts visible, readable text summary of active page."""
    return service.page_text(session_id, max_chars)


# ==========================================
# 4. Network & Stream Telemetry Tools
# ==========================================

@mcp.tool()
def network_stream(
    session_id: str = "default",
    filter_type: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Consumes real-time event stream from the per-session ring buffer advancing the cursor."""
    return service.network_stream(session_id, filter_type, limit)


@mcp.tool()
def network_list(
    session_id: str = "default",
    filter_type: Optional[str] = None,
    status_code: Optional[int] = None,
    errors_only: bool = False,
    search_query: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Lists captured HTTP transactions mirroring Chrome DevTools Network table (Name, Status, Type, Initiator, Size, Time).

    Args:
        filter_type: Filter by category ('Fetch/XHR', 'Doc', 'CSS', 'JS', 'Font', 'Img', 'Media', 'Socket', 'Wasm', 'Other').
        status_code: Filter by specific HTTP status (e.g. 200, 404, 500, 302, 304).
        errors_only: When True, lists only failed/error requests (4xx, 5xx, or network failures).
        search_query: Text or URL query to filter like the DevTools search bar.
        limit: Max transactions to return (default 100).
    """
    return service.network_list(
        session_id=session_id,
        filter_type=filter_type,
        status_code=status_code,
        errors_only=errors_only,
        search_query=search_query,
        limit=limit
    )


@mcp.tool()
def network_get(
    request_id: str,
    session_id: str = "default",
    include_request_body: bool = True,
    include_response_body: bool = True,
    max_body_bytes: int = 100000
) -> Optional[Dict[str, Any]]:
    """Retrieves full redacted transaction details (headers, payload, response, timing breakdown)."""
    return service.network_get(
        request_id=request_id,
        session_id=session_id,
        include_request_body=include_request_body,
        include_response_body=include_response_body,
        max_body_bytes=max_body_bytes
    )


@mcp.tool()
def network_summary(session_id: str = "default") -> Dict[str, Any]:
    """Returns endpoint latency percentiles (P50, P95), error distributions, and duplicate call candidates."""
    return service.network_summary(session_id)


@mcp.tool()
def network_clear(session_id: str = "default") -> Dict[str, Any]:
    """Clears captured network transactions and resets ring buffer cursor."""
    return service.network_clear(session_id)


# ==========================================
# 5. Console & Streaming Telemetry Tools
# ==========================================

@mcp.tool()
def console_list(
    session_id: str = "default",
    min_level: str = "info",
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Lists captured console logs, warnings, errors, and uncaught page exceptions."""
    return service.console_list(session_id, min_level, limit)


@mcp.tool()
def websocket_list(session_id: str = "default") -> List[Dict[str, Any]]:
    """Lists active WebSocket connections, handshake status, and frame metrics."""
    return service.websocket_list(session_id)


@mcp.tool()
def sse_list(session_id: str = "default") -> List[Dict[str, Any]]:
    """Lists active SSE streams and captured event payloads."""
    return service.sse_list(session_id)


# ==========================================
# 6. QA Intelligence & Evidence Engine Tools
# ==========================================

@mcp.tool()
def qa_anomalies(session_id: str = "default") -> List[Dict[str, Any]]:
    """Scans for deterministic anomalies: 5xx errors, CORS failures, high tail latency (>3s), and JS errors."""
    return service.qa_anomalies(session_id)


@mcp.tool()
def qa_correlate(action_id: Optional[str] = None, session_id: str = "default") -> List[Dict[str, Any]]:
    """Returns FlowEvents correlating user/agent actions with triggered network requests and console errors."""
    return service.qa_correlate(action_id, session_id)


@mcp.tool()
def qa_report(session_id: str = "default", format_type: str = "markdown") -> str:
    """Generates an evidence-backed QA Audit Report with reproduction steps and performance statistics."""
    return service.qa_report(session_id, format_type)


# ==========================================
# 7. System Storage & Cache Maintenance Tools
# ==========================================

@mcp.tool()
def check_mcp_storage() -> Dict[str, Any]:
    """Scans and itemizes what files, screenshots, extracted images, and compiler caches are consuming disk space across all MCPs."""
    return service.storage_inspect()


@mcp.tool()
def clean_mcp_storage(dry_run: bool = False) -> Dict[str, Any]:
    """Safely wipes temporary screenshots, extracted images, and compiler caches to recover disk space on user's laptop. Only run on explicit user request."""
    return service.storage_clean(dry_run=dry_run)


if __name__ == "__main__":
    mcp.run()
