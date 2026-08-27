"""Semantic DOM observation engine with snapshot observation IDs and ref mapping."""

import uuid
from typing import Any, Dict, List, Optional, Tuple
from playwright.sync_api import Page
from browser_qa.models.page import SemanticElement, FormInputModel, FormModel, PageObservation


class PageObserver:
    """Inspects page semantics, extracts interactive elements without 2MB DOM bloat,

    assigns @ref IDs, and guards against stale references.
    """

    def __init__(self):
        # Maps session_id -> current PageObservation
        self._current_observations: Dict[str, PageObservation] = {}
        # Maps session_id -> {ref_id: element_metadata}
        self._ref_maps: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def get_current_observation(self, session_id: str) -> Optional[PageObservation]:
        return self._current_observations.get(session_id)

    def validate_observation_id(self, session_id: str, observation_id: Optional[str]) -> Tuple[bool, str]:
        """Validates that action's observation_id matches current page snapshot."""
        if not observation_id:
            return True, ""
        current = self._current_observations.get(session_id)
        if not current:
            return False, "No active page observation exists for this session. Please call page_inspect() first."
        if current.observation_id != observation_id:
            return False, (
                f"Stale Reference Error: Observation '{observation_id}' is outdated. "
                f"Current page observation is '{current.observation_id}'. "
                "The DOM has mutated since your last inspection. Call page_inspect() to get fresh references."
            )
        return True, ""

    def resolve_ref(self, session_id: str, ref_id: str) -> Optional[Dict[str, Any]]:
        """Lookup element metadata by ref_id (e.g. '@1')."""
        clean_ref = ref_id.strip()
        if not clean_ref.startswith("@"):
            clean_ref = f"@{clean_ref}"
        session_map = self._ref_maps.get(session_id, {})
        return session_map.get(clean_ref)

    def inspect(self, session_id: str, page: Page) -> PageObservation:
        """Inspects page and returns a compact semantic observation."""
        obs_id = f"obs_{uuid.uuid4().hex[:8]}"
        url = page.url
        title = page.title()

        # In-page JS evaluation to extract interactive elements
        js_code = """
        () => {
            const elements = [];
            const forms = [];
            const headings = [];

            // Headings
            document.querySelectorAll('h1, h2, h3').forEach(h => {
                const text = (h.innerText || '').trim();
                if (text && headings.length < 15) {
                    headings.push(`${h.tagName.toLowerCase()}: ${text}`);
                }
            });

            // Interactive elements selector
            const interactiveSelector = 'button, a[href], input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="tab"], [role="menuitem"]';
            const nodes = document.querySelectorAll(interactiveSelector);

            let count = 0;
            nodes.forEach(node => {
                if (count >= 100) return; // Limit to top 100 interactive elements
                const rect = node.getBoundingClientRect();
                const style = window.getComputedStyle(node);
                const isVisible = rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
                if (!isVisible) return;

                count++;
                const tag = node.tagName.toLowerCase();
                const role = node.getAttribute('role') || (tag === 'a' ? 'link' : tag === 'button' ? 'button' : (tag === 'input' ? (node.getAttribute('type') || 'textbox') : tag));
                const name = (node.innerText || node.getAttribute('aria-label') || node.getAttribute('title') || node.getAttribute('placeholder') || node.getAttribute('value') || '').trim();
                
                // Form attributes
                const inputType = node.getAttribute('type') || '';
                const placeholder = node.getAttribute('placeholder') || '';
                const disabled = node.disabled || node.getAttribute('aria-disabled') === 'true';

                // Candidate robust selector
                let selector = '';
                if (node.id) {
                    selector = `#${CSS.escape(node.id)}`;
                } else if (node.getAttribute('name')) {
                    selector = `${tag}[name="${node.getAttribute('name')}"]`;
                } else if (node.getAttribute('data-testid')) {
                    selector = `[data-testid="${node.getAttribute('data-testid')}"]`;
                }

                elements.push({
                    index: count,
                    tag_name: tag,
                    role: role,
                    name: name.slice(0, 100),
                    is_disabled: disabled,
                    selector: selector,
                    attributes: {
                        type: inputType,
                        placeholder: placeholder,
                        href: tag === 'a' ? node.getAttribute('href') : undefined,
                        value: (tag === 'input' && inputType !== 'password') ? (node.value || '').slice(0, 50) : undefined
                    }
                });
            });

            // Forms
            document.querySelectorAll('form').forEach((f, fIdx) => {
                const formInputs = [];
                f.querySelectorAll('input, select, textarea').forEach(inp => {
                    formInputs.push({
                        name: inp.getAttribute('name') || inp.id || '',
                        input_type: inp.getAttribute('type') || inp.tagName.toLowerCase(),
                        value: inp.getAttribute('type') === 'password' ? '[MASKED]' : (inp.value || ''),
                        placeholder: inp.getAttribute('placeholder') || '',
                        required: inp.required || false
                    });
                });
                forms.push({
                    form_ref_id: `@form_${fIdx + 1}`,
                    action: f.getAttribute('action') || '',
                    method: (f.getAttribute('method') || 'GET').toUpperCase(),
                    inputs: formInputs
                });
            });

            // Visible body text summary (truncated)
            const bodyText = (document.body ? document.body.innerText : '').replace(/\\s+/g, ' ').trim().slice(0, 2000);

            return { elements, forms, headings, bodyText };
        }
        """
        raw_data = page.evaluate(js_code)

        semantic_elements: List[SemanticElement] = []
        ref_map: Dict[str, Dict[str, Any]] = {}

        for item in raw_data.get("elements", []):
            ref_id = f"@{item['index']}"
            elem = SemanticElement(
                ref_id=ref_id,
                role=item["role"],
                name=item["name"],
                tag_name=item["tag_name"],
                selector=item["selector"],
                is_disabled=item["is_disabled"],
                attributes=item["attributes"]
            )
            semantic_elements.append(elem)
            ref_map[ref_id] = {
                "ref_id": ref_id,
                "role": item["role"],
                "name": item["name"],
                "tag_name": item["tag_name"],
                "selector": item["selector"],
                "attributes": item["attributes"]
            }

        forms_list: List[FormModel] = []
        for f in raw_data.get("forms", []):
            inputs_list = [FormInputModel(**inp) for inp in f.get("inputs", [])]
            forms_list.append(FormModel(
                form_ref_id=f.get("form_ref_id"),
                action=f.get("action", ""),
                method=f.get("method", "GET"),
                inputs=inputs_list
            ))

        body_text = raw_data.get("bodyText", "")
        headings = raw_data.get("headings", [])

        # Smart Screen Diagnosis (Cloudflare, Login, Loading, Interactive)
        lower_title = title.lower()
        lower_body = body_text.lower()
        cf_signals = ["just a moment", "cloudflare", "turnstile", "verify you are human", "checking your browser", "cf-turnstile"]
        login_signals = ["sign in", "log in", "enter your password", "continue with google", "create your account"]

        if any(s in lower_title or s in lower_body for s in cf_signals):
            diagnosis = {
                "screen_type": "cloudflare",
                "is_blocked": True,
                "confidence": 0.95,
                "summary": "Cloudflare challenge or Turnstile verification is active.",
                "suggested_action": "Wait 4-5s for auto-solve if headed, or call session_ask_human('Cloudflare challenge detected. Please tick the verification box on screen.')."
            }
        elif any(s in lower_title for s in ["login", "sign in", "auth"]) or any(s in lower_body for s in login_signals):
            diagnosis = {
                "screen_type": "login",
                "is_blocked": False,
                "confidence": 0.85,
                "summary": "Authentication or Login screen detected.",
                "suggested_action": "Call session_ask_human to ask user if they want to log in, or proceed with credentials if authorized."
            }
        elif len(semantic_elements) == 0 and ("loading" in lower_body or len(body_text.strip()) < 50):
            diagnosis = {
                "screen_type": "loading",
                "is_blocked": False,
                "confidence": 0.80,
                "summary": "Page is still loading or rendering dynamic SPA elements.",
                "suggested_action": "Call browser_wait_idle() or browser_wait(2000) to allow complete DOM hydration."
            }
        else:
            diagnosis = {
                "screen_type": "interactive",
                "is_blocked": False,
                "confidence": 1.0,
                "summary": f"Ready for interaction with {len(semantic_elements)} elements discovered.",
                "suggested_action": "Select target element from interactive_elements and execute action."
            }

        observation = PageObservation(
            observation_id=obs_id,
            session_id=session_id,
            url=url,
            title=title,
            interactive_elements=semantic_elements,
            forms=forms_list,
            headings=headings,
            visible_text_summary=body_text,
            screen_diagnosis=diagnosis
        )

        self._current_observations[session_id] = observation
        self._ref_maps[session_id] = ref_map
        return observation
