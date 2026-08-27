"""Abstract storage interface for Browser QA MCP."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from browser_qa.models.event import BaseEvent, EventType
from browser_qa.models.network import NetworkTransaction
from browser_qa.models.flow import ConsoleEvent, FlowEvent
from browser_qa.models.finding import Anomaly, Finding


class StorageInterface(ABC):
    """Interface ensuring storage implementations are interchangeable."""

    @abstractmethod
    def add_event(self, session_id: str, event: BaseEvent) -> None:
        pass

    @abstractmethod
    def get_events(self, session_id: str, limit: int = 50, event_type: Optional[EventType] = None) -> List[BaseEvent]:
        pass

    @abstractmethod
    def add_transaction(self, session_id: str, tx: NetworkTransaction) -> None:
        pass

    @abstractmethod
    def get_transaction(self, session_id: str, request_id: str) -> Optional[NetworkTransaction]:
        pass

    @abstractmethod
    def list_transactions(
        self,
        session_id: str,
        limit: int = 50,
        status_code: Optional[int] = None,
        filter_type: Optional[str] = None
    ) -> List[NetworkTransaction]:
        pass

    @abstractmethod
    def clear_transactions(self, session_id: str) -> None:
        pass

    @abstractmethod
    def add_console_event(self, session_id: str, event: ConsoleEvent) -> None:
        pass

    @abstractmethod
    def list_console_events(self, session_id: str, limit: int = 50, min_level: Optional[str] = None) -> List[ConsoleEvent]:
        pass

    @abstractmethod
    def add_flow(self, session_id: str, flow: FlowEvent) -> None:
        pass

    @abstractmethod
    def get_flow(self, session_id: str, flow_id: str) -> Optional[FlowEvent]:
        pass

    @abstractmethod
    def list_flows(self, session_id: str, limit: int = 20) -> List[FlowEvent]:
        pass

    @abstractmethod
    def add_anomaly(self, session_id: str, anomaly: Anomaly) -> None:
        pass

    @abstractmethod
    def list_anomalies(self, session_id: str) -> List[Anomaly]:
        pass

    @abstractmethod
    def add_finding(self, session_id: str, finding: Finding) -> None:
        pass

    @abstractmethod
    def list_findings(self, session_id: str) -> List[Finding]:
        pass

    @abstractmethod
    def save_profile(self, profile_id: str, state_dict: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def load_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        pass
