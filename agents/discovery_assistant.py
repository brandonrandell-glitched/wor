"""Discovery prep assistant — account context, pain points, and meeting questions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agents.base import AssistantResponse, parse_list_input
from lib.gtm_tools import (
    discovery_questions,
    extract_pain_points,
    get_customer_context,
    recommend_products,
)


@dataclass
class DiscoveryAssistant:
    customer_account: str | None = None
    phase: str = "intake"
    collected: dict[str, Any] = field(default_factory=dict)
    skipped: set[str] = field(default_factory=set)
    intake_index: int = 0
    extracted_pain_points: list[str] = field(default_factory=list)
    pending_technologies: list[str] = field(default_factory=list)
    _final_json: dict[str, Any] | None = field(default=None, repr=False)

    INTAKE = ["industry", "organization_size", "current_infrastructure"]

    def start(self, customer_account: str) -> AssistantResponse:
        self.customer_account = customer_account
        self.collected = {"customer_account_name": customer_account}
        ctx = get_customer_context(customer_account)
        if ctx:
            mapping = {
                "industry": "industry",
                "org_size": "organization_size",
                "current_infrastructure": "current_infrastructure",
            }
            for src, dest in mapping.items():
                if ctx.get(src):
                    self.collected[dest] = ctx[src]
        self.phase = "intake"
        self.intake_index = 0
        return self._advance_intake(greeting=True)

    def process_input(self, user_input: str) -> AssistantResponse:
        text = user_input.strip()
        if self.phase == "intake":
            return self._handle_intake(text)
        if self.phase == "pain_points_confirm":
            return self._handle_pain_points(text)
        if self.phase == "technologies_confirm":
            return self._handle_technologies(text)
        if self.phase == "review":
            return self._handle_review(text)
        if self.phase == "complete":
            return AssistantResponse(
                message="Discovery prep is complete.",
                phase="complete",
                awaiting_input=False,
                json_output=self._final_json,
                done=True,
                workflow="discovery",
            )
        return AssistantResponse(message="Let's continue.", phase=self.phase, workflow="discovery")

    def _advance_intake(self, greeting: bool = False) -> AssistantResponse:
        parts = []
        if greeting:
            parts.append(f"Welcome! I'll help you prepare for discovery with {self.customer_account}.")
            if self.collected.get("industry"):
                parts.append(f"I have industry: {self.collected['industry']}")

        while self.intake_index < len(self.INTAKE):
            field_name = self.INTAKE[self.intake_index]
            if self.collected.get(field_name):
                self.intake_index += 1
                continue
            label = field_name.replace("_", " ").title()
            parts.append(f"What is the {label}? (Type 'skip' to skip.)")
            return AssistantResponse(
                message="\n\n".join(parts),
                phase="intake",
                workflow="discovery",
            )

        return self._run_pain_points()

    def _handle_intake(self, text: str) -> AssistantResponse:
        field_name = self.INTAKE[self.intake_index]
        if text.lower() == "skip":
            self.skipped.add(field_name)
            self.intake_index += 1
            return self._advance_intake()
        self.collected[field_name] = text
        self.intake_index += 1
        return self._advance_intake()

    def _run_pain_points(self) -> AssistantResponse:
        infra = self.collected.get("current_infrastructure")
        if not infra or "current_infrastructure" in self.skipped:
            self.phase = "pain_points_confirm"
            return AssistantResponse(
                message="Please describe the customer's pain points.",
                phase="pain_points_confirm",
                workflow="discovery",
            )
        result = extract_pain_points(
            infra,
            self.collected.get("industry"),
            self.collected.get("organization_size"),
        )
        self.extracted_pain_points = result["pain_points"]
        self.phase = "pain_points_confirm"
        if self.extracted_pain_points:
            listed = "\n".join(f"  • {p}" for p in self.extracted_pain_points)
            return AssistantResponse(
                message=(
                    f"I identified these pain points:\n{listed}\n\n"
                    "Reply 'use', 'add', or 'replace'."
                ),
                phase="pain_points_confirm",
                tool_call={"tool": "extract_pain_points", "result": result},
                workflow="discovery",
            )
        return AssistantResponse(
            message="Please describe the customer's pain points.",
            phase="pain_points_confirm",
            workflow="discovery",
        )

    def _handle_pain_points(self, text: str) -> AssistantResponse:
        lower = text.lower()
        if lower == "use" and self.extracted_pain_points:
            self.collected["customer_pain_points"] = list(self.extracted_pain_points)
            return self._run_technologies()
        if lower == "replace":
            return AssistantResponse(
                message="Please provide the pain points.",
                phase="pain_points_confirm",
                workflow="discovery",
            )
        if lower == "add" and self.extracted_pain_points:
            self.collected["customer_pain_points"] = list(self.extracted_pain_points)
            return AssistantResponse(
                message="Please provide additional pain points.",
                phase="pain_points_confirm",
                workflow="discovery",
            )
        points = parse_list_input(text)
        if "customer_pain_points" in self.collected and lower != "use":
            self.collected["customer_pain_points"].extend(points)
        else:
            self.collected["customer_pain_points"] = points
        return self._run_technologies()

    def _run_technologies(self) -> AssistantResponse:
        pains = self.collected.get("customer_pain_points", [])
        result = recommend_products(pains)
        self.pending_technologies = result["recommendations"]
        self.collected["cisco_technologies"] = list(self.pending_technologies)
        self.phase = "technologies_confirm"
        listed = "\n".join(f"  • {t}" for t in self.pending_technologies)
        return AssistantResponse(
            message=(
                f"Recommended technologies:\n{listed}\n\n"
                "Reply 'all' to accept, or list the technologies to include."
            ),
            phase="technologies_confirm",
            tool_call={"tool": "recommend_products", "result": result},
            workflow="discovery",
        )

    def _handle_technologies(self, text: str) -> AssistantResponse:
        if text.lower() == "all":
            self.collected["cisco_technologies"] = list(self.pending_technologies)
        else:
            selected = parse_list_input(text)
            if selected:
                self.collected["cisco_technologies"] = selected
        self.phase = "review"
        return self._build_review()

    def _build_review(self) -> AssistantResponse:
        pains = self.collected.get("customer_pain_points", [])
        questions = discovery_questions(pains, self.collected.get("industry"))
        self.collected["discovery_questions"] = questions
        summary = {
            "Customer Account Name": self.customer_account,
            "Industry": self.collected.get("industry", "Skipped" if "industry" in self.skipped else ""),
            "Organization Size": self.collected.get("organization_size", "Skipped" if "organization_size" in self.skipped else ""),
            "Current Infrastructure": self.collected.get("current_infrastructure", "Skipped" if "current_infrastructure" in self.skipped else ""),
            "Customer Pain Points": ", ".join(pains),
            "Cisco Technologies": ", ".join(self.collected.get("cisco_technologies", [])),
            "Discovery Questions": "\n".join(f"- {q}" for q in questions),
        }
        lines = [f"  {k}: {v}" for k, v in summary.items()]
        return AssistantResponse(
            message="Discovery prep summary:\n\n" + "\n".join(lines) + "\n\nReply 'yes' to confirm.",
            phase="review",
            summary=summary,
            workflow="discovery",
        )

    def _handle_review(self, text: str) -> AssistantResponse:
        if text.lower() in ("yes", "y", "confirm"):
            self.phase = "complete"
            output = {
                "Customer Account Name": self.customer_account,
                "Industry": self.collected.get("industry", "Skipped"),
                "Organization Size": self.collected.get("organization_size", "Skipped"),
                "Current Infrastructure": self.collected.get("current_infrastructure", "Skipped"),
                "Customer Pain Points": ", ".join(self.collected.get("customer_pain_points", [])),
                "Cisco Technologies to be Proposed": self.collected.get("cisco_technologies", []),
                "Discovery Questions": self.collected.get("discovery_questions", []),
            }
            self._final_json = output
            import json
            return AssistantResponse(
                message=json.dumps(output, indent=2),
                phase="complete",
                json_output=output,
                awaiting_input=False,
                done=True,
                workflow="discovery",
            )
        return AssistantResponse(
            message="Reply 'yes' to confirm the discovery prep summary.",
            phase="review",
            workflow="discovery",
        )
