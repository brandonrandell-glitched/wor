"""Route seller requests to the correct GTM workflow."""

from __future__ import annotations

from typing import Any

from agents.base import AssistantResponse, Workflow
from agents.competitive_assistant import CompetitiveAssistant
from agents.discovery_assistant import DiscoveryAssistant
from agents.proposal_assistant import ProposalAssistant


class GTMRouter:
    WORKFLOWS = {
        Workflow.PROPOSAL.value: {
            "label": "Build Proposal",
            "description": "Full proposal intake with review and document export",
            "class": ProposalAssistant,
        },
        Workflow.DISCOVERY.value: {
            "label": "Discovery Prep",
            "description": "Account context, pain points, and discovery questions",
            "class": DiscoveryAssistant,
        },
        Workflow.COMPETITIVE.value: {
            "label": "Competitive Brief",
            "description": "Position Cisco technologies against selected competitors",
            "class": CompetitiveAssistant,
        },
    }

    def __init__(self) -> None:
        self._sessions: dict[str, Any] = {}

    def list_workflows(self) -> list[dict[str, str]]:
        return [
            {"id": key, "label": val["label"], "description": val["description"]}
            for key, val in self.WORKFLOWS.items()
        ]

    def start(self, workflow: str, customer_account: str, session_id: str) -> AssistantResponse:
        spec = self.WORKFLOWS.get(workflow)
        if not spec:
            raise ValueError(f"Unknown workflow: {workflow}")
        assistant = spec["class"]()
        resp = assistant.start(customer_account)
        self._sessions[session_id] = {"workflow": workflow, "assistant": assistant}
        return self._wrap(resp, workflow)

    def process(self, session_id: str, message: str) -> AssistantResponse:
        entry = self._sessions.get(session_id)
        if not entry:
            raise KeyError("Session not found")
        resp = entry["assistant"].process_input(message)
        return self._wrap(resp, entry["workflow"])

    def get_assistant(self, session_id: str) -> Any:
        entry = self._sessions.get(session_id)
        return entry["assistant"] if entry else None

    def get_workflow(self, session_id: str) -> str | None:
        entry = self._sessions.get(session_id)
        return entry["workflow"] if entry else None

    @staticmethod
    def _wrap(resp: Any, workflow: str) -> AssistantResponse:
        if isinstance(resp, AssistantResponse) and resp.workflow:
            return resp
        return AssistantResponse(
            message=resp.message,
            phase=resp.phase.value if hasattr(resp.phase, "value") else str(resp.phase),
            awaiting_input=resp.awaiting_input,
            tool_call=resp.tool_call,
            summary=resp.summary,
            json_output=resp.json_output,
            done=resp.done,
            workflow=workflow,
        )
