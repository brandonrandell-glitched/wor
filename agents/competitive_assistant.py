"""Competitive brief assistant — positioning vs selected competitors."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from agents.base import AssistantResponse, parse_list_input
from lib.gtm_tools import get_customer_context
from lib.public_content import list_competitors


@dataclass
class CompetitiveAssistant:
    customer_account: str | None = None
    phase: str = "technologies"
    collected: dict[str, Any] = field(default_factory=dict)
    available_competitors: list[str] = field(default_factory=list)
    _final_json: dict[str, Any] | None = field(default=None, repr=False)

    def start(self, customer_account: str) -> AssistantResponse:
        self.customer_account = customer_account
        self.collected = {"customer_account_name": customer_account}
        self.available_competitors = list_competitors()
        ctx = get_customer_context(customer_account)
        if ctx and ctx.get("cisco_technologies_proposed"):
            self.collected["cisco_technologies"] = list(ctx["cisco_technologies_proposed"])
        self.phase = "technologies"
        if self.collected.get("cisco_technologies"):
            techs = ", ".join(self.collected["cisco_technologies"])
            return AssistantResponse(
                message=(
                    f"I have these Cisco technologies for {customer_account}: {techs}\n\n"
                    "Reply 'use' to keep them, or list technologies to replace."
                ),
                phase="technologies",
                workflow="competitive",
            )
        return AssistantResponse(
            message="Which Cisco technologies are in scope? (comma-separated)",
            phase="technologies",
            workflow="competitive",
        )

    def process_input(self, user_input: str) -> AssistantResponse:
        text = user_input.strip()
        if self.phase == "technologies":
            return self._handle_technologies(text)
        if self.phase == "competitors":
            return self._handle_competitors(text)
        if self.phase == "review":
            return self._handle_review(text)
        if self.phase == "complete":
            return AssistantResponse(
                message="Competitive brief is complete.",
                phase="complete",
                awaiting_input=False,
                json_output=self._final_json,
                done=True,
                workflow="competitive",
            )
        return AssistantResponse(message="Let's continue.", phase=self.phase, workflow="competitive")

    def _handle_technologies(self, text: str) -> AssistantResponse:
        if text.lower() != "use":
            selected = parse_list_input(text)
            if selected:
                self.collected["cisco_technologies"] = selected
            elif not self.collected.get("cisco_technologies"):
                return AssistantResponse(
                    message="Please list the Cisco technologies in scope.",
                    phase="technologies",
                    workflow="competitive",
                )
        self.phase = "competitors"
        options = "\n".join(f"  • {c}" for c in self.available_competitors)
        return AssistantResponse(
            message=(
                "Which competitors should we position against?\n"
                f"{options}\n\n"
                "List competitor names (comma-separated), or type 'all'."
            ),
            phase="competitors",
            workflow="competitive",
        )

    def _handle_competitors(self, text: str) -> AssistantResponse:
        if text.lower() == "all":
            self.collected["competitors"] = list(self.available_competitors)
        else:
            selected = parse_list_input(text)
            valid = [c for c in selected if c in self.available_competitors]
            if not valid:
                return AssistantResponse(
                    message="Please choose from the listed competitors.",
                    phase="competitors",
                    workflow="competitive",
                )
            self.collected["competitors"] = valid
        self.phase = "review"
        return self._build_review()

    def _build_review(self) -> AssistantResponse:
        summary = {
            "Customer Account Name": self.customer_account,
            "Cisco Technologies to be Proposed": self.collected.get("cisco_technologies", []),
            "Competitors": self.collected.get("competitors", []),
        }
        lines = [f"  {k}: {v}" for k, v in summary.items()]
        return AssistantResponse(
            message="Competitive brief summary:\n\n" + "\n".join(lines) + "\n\nReply 'yes' to confirm.",
            phase="review",
            summary=summary,
            workflow="competitive",
        )

    def _handle_review(self, text: str) -> AssistantResponse:
        if text.lower() in ("yes", "y", "confirm"):
            self.phase = "complete"
            output = {
                "Customer Account Name": self.customer_account,
                "Cisco Technologies to be Proposed": self.collected.get("cisco_technologies", []),
                "Competitors": self.collected.get("competitors", []),
            }
            self._final_json = output
            return AssistantResponse(
                message=json.dumps(output, indent=2),
                phase="complete",
                json_output=output,
                awaiting_input=False,
                done=True,
                workflow="competitive",
            )
        return AssistantResponse(
            message="Reply 'yes' to confirm.",
            phase="review",
            workflow="competitive",
        )
