"""Shared types and helpers for GTM agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Workflow(str, Enum):
    PROPOSAL = "proposal"
    DISCOVERY = "discovery"
    COMPETITIVE = "competitive"


@dataclass
class AssistantResponse:
    message: str
    phase: str
    awaiting_input: bool = True
    tool_call: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None
    json_output: dict[str, Any] | None = None
    done: bool = False
    workflow: str = ""


@dataclass
class GTMContext:
    customer_account: str
    industry: str = ""
    organization_size: str = ""
    current_infrastructure: str = ""
    pain_points: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)
    deal_id: str = ""
    language: str = "English"
    offer_type: str = "security-suite"

    def to_dict(self) -> dict[str, Any]:
        return {
            "Customer Account Name": self.customer_account,
            "Industry": self.industry,
            "Organization Size": self.organization_size,
            "Current Infrastructure": self.current_infrastructure,
            "Customer Pain Points": ", ".join(self.pain_points),
            "Cisco Technologies to be Proposed": self.technologies,
            "Competitors": self.competitors,
            "DEAL ID": self.deal_id,
            "Language": self.language,
            "Offer Type": self.offer_type,
        }


def parse_list_input(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if ";" in text:
        parts = text.split(";")
    elif "\n" in text:
        parts = text.split("\n")
    else:
        parts = text.split(",")
    return [p.strip().lstrip("•").strip() for p in parts if p.strip()]
