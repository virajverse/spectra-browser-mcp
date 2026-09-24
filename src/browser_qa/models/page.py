"""Page observation, semantic element, and form models."""

import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SemanticElement(BaseModel):
    ref_id: str  # e.g. "@1", "@2"
    role: str  # button, link, textbox, checkbox, select, heading, etc.
    name: str = ""  # Accessible name or inner text
    tag_name: str = ""
    selector: str = ""  # Internal safe locator
    is_visible: bool = True
    is_disabled: bool = False
    attributes: Dict[str, Any] = Field(default_factory=dict)


class FormInputModel(BaseModel):
    ref_id: Optional[str] = None
    name: str = ""
    input_type: str = "text"
    value: str = ""
    placeholder: str = ""
    required: bool = False
    options: List[str] = Field(default_factory=list)  # For select elements


class FormModel(BaseModel):
    form_ref_id: Optional[str] = None
    action: str = ""
    method: str = "POST"
    inputs: List[FormInputModel] = Field(default_factory=list)
    submit_ref_id: Optional[str] = None


class PageObservation(BaseModel):
    observation_id: str = Field(default_factory=lambda: f"obs_{uuid.uuid4().hex[:8]}")
    session_id: str = "default"
    timestamp: float = Field(default_factory=time.time)
    url: str
    title: str = ""
    interactive_elements: List[SemanticElement] = Field(default_factory=list)
    forms: List[FormModel] = Field(default_factory=list)
    headings: List[str] = Field(default_factory=list)
    visible_text_summary: str = ""
    screen_diagnosis: Dict[str, Any] = Field(default_factory=dict)
