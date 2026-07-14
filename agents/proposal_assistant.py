"""Proposal-building AI assistant — conversation state machine."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SALESFORCE_FIXTURE = ROOT / "fixtures" / "salesforce_customer.json"
TOOLS_FIXTURE = ROOT / "fixtures" / "proposal_tools_data.json"

VALID_LANGUAGES = {
    "english",
    "german",
    "italian",
    "french",
    "spanish",
    "japanese",
    "simplified chinese",
}
VALID_FORMATS = {"word", "ppt"}
VALID_LENGTHS = {"short", "long"}

MANDATORY_FIELDS = {
    "customer_account_name",
    "customer_pain_points",
    "cisco_technologies",
    "next_steps",
    "language",
    "proposal_output_format",
}

OPTIONAL_FIELDS = {
    "industry",
    "organization_size",
    "current_infrastructure",
    "deal_id",
}

INTAKE_ORDER = [
    "customer_account_name",
    "industry",
    "organization_size",
    "current_infrastructure",
]

POST_INFRA_STEPS = [
    "next_steps",
    "deal_id",
    "language",
    "proposal_output_format",
    "proposal_form_length",
]

SUMMARY_ORDER = [
    ("customer_account_name", "Customer Account Name"),
    ("industry", "Industry"),
    ("organization_size", "Organization Size"),
    ("current_infrastructure", "Current Infrastructure"),
    ("customer_pain_points", "Customer Pain Points"),
    ("cisco_technologies", "Cisco Technologies to be Proposed"),
    ("next_steps", "Next Steps"),
    ("deal_id", "Deal ID"),
    ("language", "Language"),
    ("proposal_output_format", "Proposal Output Format"),
    ("proposal_form_length", "Proposal Form Length"),
]

OUT_OF_CONTEXT_REDIRECT = (
    "I understand your interest in {topic}, but let's focus on the proposal building process."
)


class Phase(str, Enum):
    GREETING = "greeting"
    INTAKE = "intake"
    PAIN_POINTS_EXTRACT = "pain_points_extract"
    PAIN_POINTS_CONFIRM = "pain_points_confirm"
    TECHNOLOGIES_CONFIRM = "technologies_confirm"
    TECHNOLOGIES_SELECT = "technologies_select"
    DEAL_CONFIRM = "deal_confirm"
    DEAL_SELECT = "deal_select"
    REVIEW = "review"
    COMPLETE = "complete"


@dataclass
class AssistantResponse:
    message: str
    phase: Phase
    awaiting_input: bool = True
    tool_call: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None
    json_output: dict[str, Any] | None = None
    done: bool = False


@dataclass
class ProposalAssistant:
    """Guides a seller through proposal intake with strict ordering and validation."""

    customer_account: str | None = None
    phase: Phase = Phase.GREETING
    collected: dict[str, Any] = field(default_factory=dict)
    skipped: set[str] = field(default_factory=set)
    intake_index: int = 0
    post_infra_index: int = 0
    extracted_pain_points: list[str] = field(default_factory=list)
    pending_technologies: list[str] = field(default_factory=list)
    deal_batch_offset: int = 0
    deal_options: list[dict[str, Any]] = field(default_factory=list)
    _initial_data: dict[str, Any] = field(default_factory=dict, repr=False)
    _final_json: dict[str, Any] | None = field(default=None, repr=False)

    def start(self, customer_account: str) -> AssistantResponse:
        self.customer_account = customer_account
        self.collected["customer_account_name"] = customer_account
        self._load_initial_data(customer_account)
        self._prefill_from_data()
        self.phase = Phase.INTAKE
        self.intake_index = 0
        return self._advance_intake(greeting=True)

    def process_input(self, user_input: str) -> AssistantResponse:
        text = user_input.strip()
        if not text and self.phase not in (Phase.PAIN_POINTS_EXTRACT,):
            return AssistantResponse(
                message="Please provide a response.",
                phase=self.phase,
            )

        if self.phase == Phase.INTAKE:
            return self._handle_intake(text)
        if self.phase == Phase.PAIN_POINTS_EXTRACT:
            return self._run_pain_points_extraction()
        if self.phase == Phase.PAIN_POINTS_CONFIRM:
            return self._handle_pain_points_confirm(text)
        if self.phase == Phase.TECHNOLOGIES_CONFIRM:
            return self._handle_technologies_confirm(text)
        if self.phase == Phase.TECHNOLOGIES_SELECT:
            return self._handle_technologies_select(text)
        if self.phase == Phase.DEAL_CONFIRM:
            return self._handle_deal_confirm(text)
        if self.phase == Phase.DEAL_SELECT:
            return self._handle_deal_select(text)
        if self.phase in (Phase.GREETING,):
            return self._handle_post_intake_field(text)
        if self.phase == Phase.REVIEW:
            return self._handle_review(text)
        if self.phase == Phase.COMPLETE:
            return AssistantResponse(
                message="The proposal intake is complete. No further changes can be made.",
                phase=Phase.COMPLETE,
                awaiting_input=False,
                json_output=self._final_json,
                done=True,
            )
        return AssistantResponse(message="Let's continue with the proposal.", phase=self.phase)

    def _load_initial_data(self, customer_account: str) -> None:
        if not SALESFORCE_FIXTURE.exists():
            self._initial_data = {}
            return
        with open(SALESFORCE_FIXTURE) as f:
            raw = json.load(f)
        if raw.get("customer_account") != customer_account:
            self._initial_data = {}
            return
        self._initial_data = {k: v for k, v in raw.items() if k != "savm_id"}

    def _prefill_from_data(self) -> None:
        mapping = {
            "customer_account": "customer_account_name",
            "org_size": "organization_size",
            "deal_id": "deal_id",
            "cisco_technologies_proposed": "cisco_technologies",
            "current_infrastructure": "current_infrastructure",
            "industry": "industry",
        }
        for src, dest in mapping.items():
            val = self._initial_data.get(src)
            if val is not None and val != "" and val != []:
                self.collected[dest] = deepcopy(val)

        prev = self._initial_data.get("previous_proposal", {})
        for key in ("language", "proposal_output_format", "proposal_form_length"):
            val = prev.get(key)
            if val:
                self.collected[key] = val

    def _advance_intake(self, greeting: bool = False) -> AssistantResponse:
        greeting_parts: list[str] = []
        if greeting:
            greeting_parts.append(
                f"Welcome! I'll help you build a proposal for {self.customer_account}."
            )
            available = self._format_available_data()
            if available:
                greeting_parts.append(f"Here's what I already have:\n{available}")

        while self.intake_index < len(INTAKE_ORDER):
            field_name = INTAKE_ORDER[self.intake_index]
            if field_name in self.collected and self.collected[field_name]:
                self.intake_index += 1
                continue

            label = field_name.replace("_", " ").title()
            mandatory = field_name in MANDATORY_FIELDS
            optional = field_name in OPTIONAL_FIELDS

            parts = []
            if greeting_parts:
                parts.extend(greeting_parts)
                greeting_parts = []

            if optional:
                parts.append(
                    f"What is the {label}? (You can type 'skip' to skip this optional field.)"
                )
            else:
                parts.append(f"What is the {label}?")

            return AssistantResponse(
                message="\n\n".join(parts),
                phase=Phase.INTAKE,
            )

        self.phase = Phase.PAIN_POINTS_EXTRACT
        resp = self._run_pain_points_extraction()
        if greeting_parts:
            resp.message = "\n\n".join(greeting_parts + [resp.message])
        return resp

    def _handle_intake(self, text: str) -> AssistantResponse:
        field_name = INTAKE_ORDER[self.intake_index]
        optional = field_name in OPTIONAL_FIELDS

        if optional and text.lower() == "skip":
            self.skipped.add(field_name)
            self.intake_index += 1
            return self._advance_intake()

        if not text:
            label = field_name.replace("_", " ").title()
            return AssistantResponse(
                message=f"Please provide the {label}."
                + (" or type 'skip' to skip." if optional else ""),
                phase=Phase.INTAKE,
            )

        self.collected[field_name] = text
        self.intake_index += 1
        return self._advance_intake()

    def _run_pain_points_extraction(self) -> AssistantResponse:
        infra = self.collected.get("current_infrastructure")
        if not infra or "current_infrastructure" in self.skipped:
            self.phase = Phase.PAIN_POINTS_CONFIRM
            return AssistantResponse(
                message=(
                    "No current infrastructure was provided. "
                    "Please describe the customer's pain points."
                ),
                phase=Phase.PAIN_POINTS_CONFIRM,
            )

        result = _extract_pain_points(
            infra,
            self.collected.get("industry"),
            self.collected.get("organization_size"),
        )
        self.extracted_pain_points = result["pain_points"]
        self.phase = Phase.PAIN_POINTS_CONFIRM

        if self.extracted_pain_points:
            listed = "\n".join(f"  • {p}" for p in self.extracted_pain_points)
            return AssistantResponse(
                message=(
                    "Based on the infrastructure details, I identified these pain points:\n"
                    f"{listed}\n\n"
                    "Would you like to use these, add to them, or replace them entirely? "
                    "(Reply 'use', 'add', or 'replace')"
                ),
                phase=Phase.PAIN_POINTS_CONFIRM,
                tool_call={"tool": "extract_pain_points", "result": result},
            )

        return AssistantResponse(
            message=(
                "I could not extract pain points automatically. "
                "Please describe the customer's pain points."
            ),
            phase=Phase.PAIN_POINTS_CONFIRM,
        )

    def _handle_pain_points_confirm(self, text: str) -> AssistantResponse:
        lower = text.lower()

        if lower == "use" and self.extracted_pain_points:
            self.collected["customer_pain_points"] = list(self.extracted_pain_points)
            return self._enter_technologies_phase()

        if lower == "add" and self.extracted_pain_points:
            self.collected["customer_pain_points"] = list(self.extracted_pain_points)
            return AssistantResponse(
                message="Please provide the additional pain points to add.",
                phase=Phase.PAIN_POINTS_CONFIRM,
            )

        if lower == "replace":
            return AssistantResponse(
                message="Please provide the customer pain points to use.",
                phase=Phase.PAIN_POINTS_CONFIRM,
            )

        if "customer_pain_points" in self.collected and lower != "use":
            existing = self.collected["customer_pain_points"]
            new_points = _parse_list_input(text)
            self.collected["customer_pain_points"] = existing + new_points
            return self._enter_technologies_phase()

        new_points = _parse_list_input(text)
        if not new_points:
            return AssistantResponse(
                message="Please provide at least one pain point.",
                phase=Phase.PAIN_POINTS_CONFIRM,
            )
        self.collected["customer_pain_points"] = new_points
        return self._enter_technologies_phase()

    def _enter_technologies_phase(self) -> AssistantResponse:
        existing = self.collected.get("cisco_technologies")
        if existing:
            self.pending_technologies = list(existing)
            listed = "\n".join(f"  • {t}" for t in self.pending_technologies)
            self.phase = Phase.TECHNOLOGIES_CONFIRM
            return AssistantResponse(
                message=(
                    f"I have these Cisco technologies from existing data:\n{listed}\n\n"
                    "Would you like to use these, add to them, or replace them? "
                    "(Reply 'use', 'add', or 'replace')"
                ),
                phase=Phase.TECHNOLOGIES_CONFIRM,
            )

        return self._run_product_recommendations()

    def _run_product_recommendations(self) -> AssistantResponse:
        pain_points = self.collected.get("customer_pain_points", [])
        result = _recommend_products(pain_points)
        self.pending_technologies = result["recommendations"]
        self.phase = Phase.TECHNOLOGIES_SELECT

        listed = "\n".join(f"  • {t}" for t in self.pending_technologies)
        return AssistantResponse(
            message=(
                "Based on the pain points, I recommend these Cisco technologies:\n"
                f"{listed}\n\n"
                "Please confirm which technologies to include. "
                "List the ones you want, or type 'all' to accept all recommendations. "
                "You may also add custom technologies."
            ),
            phase=Phase.TECHNOLOGIES_SELECT,
            tool_call={"tool": "recommend_products", "result": result},
        )

    def _handle_technologies_confirm(self, text: str) -> AssistantResponse:
        lower = text.lower()

        if lower == "use":
            self.collected["cisco_technologies"] = list(self.pending_technologies)
            return self._enter_post_infra_flow()

        if lower == "add":
            return AssistantResponse(
                message="Please list the additional Cisco technologies to add.",
                phase=Phase.TECHNOLOGIES_CONFIRM,
            )

        if lower == "replace":
            self.phase = Phase.TECHNOLOGIES_SELECT
            return self._run_product_recommendations()

        additions = _parse_list_input(text)
        if additions:
            merged = list(self.pending_technologies)
            for tech in additions:
                if tech not in merged:
                    merged.append(tech)
            self.collected["cisco_technologies"] = merged
            return self._enter_post_infra_flow()

        return AssistantResponse(
            message="Reply 'use', 'add', or 'replace' for the technologies.",
            phase=Phase.TECHNOLOGIES_CONFIRM,
        )

    def _handle_technologies_select(self, text: str) -> AssistantResponse:
        lower = text.lower()

        if lower == "all":
            self.collected["cisco_technologies"] = list(self.pending_technologies)
            return self._enter_post_infra_flow()

        selected = _parse_list_input(text)
        if not selected:
            return AssistantResponse(
                message=(
                    "Please select technologies from the recommendations, type 'all', "
                    "or list custom technologies."
                ),
                phase=Phase.TECHNOLOGIES_SELECT,
            )

        validated = []
        for tech in selected:
            validated.append(tech)
        self.collected["cisco_technologies"] = validated
        return self._enter_post_infra_flow()

    def _enter_post_infra_flow(self) -> AssistantResponse:
        self.post_infra_index = 0
        self.phase = Phase.GREETING
        return self._advance_post_infra()

    def _advance_post_infra(self) -> AssistantResponse:
        while self.post_infra_index < len(POST_INFRA_STEPS):
            field_name = POST_INFRA_STEPS[self.post_infra_index]

            if field_name == "proposal_form_length":
                fmt = self.collected.get("proposal_output_format", "").lower()
                if fmt != "word":
                    self.post_infra_index += 1
                    continue

            if field_name == "deal_id":
                if field_name in self.collected and self.collected[field_name]:
                    return self._enter_deal_confirm()
                return self._enter_deal_suggest()

            if field_name in self.collected and self.collected[field_name]:
                self.post_infra_index += 1
                continue

            return self._ask_post_infra_field(field_name)

        self.phase = Phase.REVIEW
        return self._build_review()

    def _ask_post_infra_field(self, field_name: str) -> AssistantResponse:
        prompts = {
            "next_steps": "What are the next steps for this proposal?",
            "language": (
                "What language should the proposal be in? "
                "(English, German, Italian, French, Spanish, Japanese, or Simplified Chinese)"
            ),
            "proposal_output_format": "What output format would you like — word or ppt?",
            "proposal_form_length": "What form length would you like — short or long?",
        }
        optional = field_name in OPTIONAL_FIELDS
        msg = prompts[field_name]
        if optional:
            msg += " (Type 'skip' to skip.)"
        return AssistantResponse(message=msg, phase=Phase.GREETING)

    def _handle_post_intake_field(self, text: str) -> AssistantResponse:
        field_name = POST_INFRA_STEPS[self.post_infra_index]
        optional = field_name in OPTIONAL_FIELDS

        if optional and text.lower() == "skip":
            self.skipped.add(field_name)
            self.post_infra_index += 1
            return self._advance_post_infra()

        if field_name == "language":
            if text.lower() not in VALID_LANGUAGES:
                return AssistantResponse(
                    message=(
                        "Please choose a valid language: English, German, Italian, "
                        "French, Spanish, Japanese, or Simplified Chinese."
                    ),
                    phase=Phase.GREETING,
                )
            self.collected["language"] = _title_language(text)

        elif field_name == "proposal_output_format":
            if text.lower() not in VALID_FORMATS:
                return AssistantResponse(
                    message="Please choose 'word' or 'ppt'.",
                    phase=Phase.GREETING,
                )
            self.collected["proposal_output_format"] = text.lower()

        elif field_name == "proposal_form_length":
            if text.lower() not in VALID_LENGTHS:
                return AssistantResponse(
                    message="Please choose 'short' or 'long'.",
                    phase=Phase.GREETING,
                )
            self.collected["proposal_form_length"] = text.lower()

        else:
            if not text:
                return self._ask_post_infra_field(field_name)
            self.collected[field_name] = text

        self.post_infra_index += 1
        return self._advance_post_infra()

    def _enter_deal_confirm(self) -> AssistantResponse:
        deal_id = self.collected.get("deal_id")
        self.phase = Phase.DEAL_CONFIRM
        return AssistantResponse(
            message=(
                f"I have Deal ID: {deal_id}\n\n"
                "Is this correct? (Reply 'yes' to confirm, or provide a different Deal ID.)"
            ),
            phase=Phase.DEAL_CONFIRM,
        )

    def _handle_deal_confirm(self, text: str) -> AssistantResponse:
        if text.lower() in ("yes", "y", "confirm", "correct"):
            self.post_infra_index += 1
            self.phase = Phase.GREETING
            return self._advance_post_infra()

        if text.lower() == "skip":
            self.skipped.add("deal_id")
            del self.collected["deal_id"]
            self.post_infra_index += 1
            self.phase = Phase.GREETING
            return self._advance_post_infra()

        self.collected["deal_id"] = text
        self.post_infra_index += 1
        self.phase = Phase.GREETING
        return self._advance_post_infra()

    def _enter_deal_suggest(self) -> AssistantResponse:
        result = _suggest_opportunities(self.customer_account, self.deal_batch_offset)
        self.deal_options = result["opportunities"]
        self.phase = Phase.DEAL_SELECT

        if not self.deal_options:
            self.skipped.add("deal_id")
            self.post_infra_index += 1
            self.phase = Phase.GREETING
            return self._advance_post_infra()

        lines = []
        for i, opp in enumerate(self.deal_options, 1):
            lines.append(
                f"  {i}. {opp['deal_id']} — {opp['name']} "
                f"({opp['stage']}, ${opp['amount']:,})"
            )
        batch_info = ""
        if result["has_more"]:
            batch_info = "\n\nType 'more' to see additional opportunities."

        return AssistantResponse(
            message=(
                "Please select a Deal ID from these opportunities:\n"
                + "\n".join(lines)
                + "\n\nEnter the number or Deal ID, type 'skip' to skip, "
                "or 'more' for the next batch."
                + batch_info
            ),
            phase=Phase.DEAL_SELECT,
            tool_call={"tool": "suggest_opportunities", "result": result},
        )

    def _handle_deal_select(self, text: str) -> AssistantResponse:
        lower = text.lower()

        if lower == "skip":
            self.skipped.add("deal_id")
            self.post_infra_index += 1
            self.phase = Phase.GREETING
            return self._advance_post_infra()

        if lower == "more":
            self.deal_batch_offset += 10
            return self._enter_deal_suggest()

        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(self.deal_options):
                self.collected["deal_id"] = self.deal_options[idx]["deal_id"]
                self.post_infra_index += 1
                self.phase = Phase.GREETING
                return self._advance_post_infra()

        for opp in self.deal_options:
            if opp["deal_id"].lower() == lower or opp["deal_id"] == text:
                self.collected["deal_id"] = opp["deal_id"]
                self.post_infra_index += 1
                self.phase = Phase.GREETING
                return self._advance_post_infra()

        return AssistantResponse(
            message="Please enter a valid number, Deal ID, 'skip', or 'more'.",
            phase=Phase.DEAL_SELECT,
        )

    def _build_review(self) -> AssistantResponse:
        summary = self._build_summary_dict()
        lines = []
        for _, label in SUMMARY_ORDER:
            val = summary[label]
            lines.append(f"  {label}: {val}")

        return AssistantResponse(
            message=(
                "Here is a summary of the proposal details for your review:\n\n"
                + "\n".join(lines)
                + "\n\nIs this correct? Reply 'yes' to confirm, or tell me which field "
                "to update (e.g., 'update language to German')."
            ),
            phase=Phase.REVIEW,
            summary=summary,
        )

    def _handle_review(self, text: str) -> AssistantResponse:
        lower = text.lower()

        if lower in ("yes", "y", "confirm", "correct", "looks good"):
            self.phase = Phase.COMPLETE
            output = self._build_final_json()
            self._final_json = output
            return AssistantResponse(
                message=json.dumps(output, indent=2),
                phase=Phase.COMPLETE,
                json_output=output,
                awaiting_input=False,
                done=True,
            )

        updated = self._try_parse_field_update(text)
        if updated:
            return self._build_review()

        return AssistantResponse(
            message=(
                "Please reply 'yes' to confirm the summary, or specify a field to update "
                "(e.g., 'update next steps to schedule executive briefing')."
            ),
            phase=Phase.REVIEW,
        )

    def _try_parse_field_update(self, text: str) -> bool:
        lower = text.lower()
        if not lower.startswith("update "):
            return False

        remainder = text[7:].strip()
        remainder_lower = remainder.lower()
        field_map = {
            "customer account name": "customer_account_name",
            "industry": "industry",
            "organization size": "organization_size",
            "current infrastructure": "current_infrastructure",
            "customer pain points": "customer_pain_points",
            "cisco technologies": "cisco_technologies",
            "cisco technologies to be proposed": "cisco_technologies",
            "next steps": "next_steps",
            "deal id": "deal_id",
            "language": "language",
            "proposal output format": "proposal_output_format",
            "proposal form length": "proposal_form_length",
        }

        for label, key in field_map.items():
            prefix = label + " to "
            if remainder_lower.startswith(prefix):
                value = remainder[len(label) + 4 :].strip()
                if key == "customer_pain_points":
                    self.collected[key] = _parse_list_input(value)
                elif key == "cisco_technologies":
                    self.collected[key] = _parse_list_input(value)
                elif key == "language":
                    if value.lower() not in VALID_LANGUAGES:
                        return False
                    self.collected[key] = _title_language(value)
                elif key == "proposal_output_format":
                    if value.lower() not in VALID_FORMATS:
                        return False
                    self.collected[key] = value.lower()
                elif key == "proposal_form_length":
                    if value.lower() not in VALID_LENGTHS:
                        return False
                    self.collected[key] = value.lower()
                else:
                    self.collected[key] = value
                self.skipped.discard(key)
                return True
        return False

    def _build_summary_dict(self) -> dict[str, Any]:
        summary = {}
        for key, label in SUMMARY_ORDER:
            if key in self.skipped:
                summary[label] = "Skipped"
            elif key == "customer_pain_points":
                pts = self.collected.get(key, [])
                summary[label] = ", ".join(pts) if pts else "Skipped"
            elif key == "cisco_technologies":
                techs = self.collected.get(key, [])
                summary[label] = techs if techs else "Skipped"
            elif key == "proposal_form_length":
                fmt = self.collected.get("proposal_output_format", "").lower()
                if fmt != "word":
                    summary[label] = "N/A"
                elif key in self.skipped:
                    summary[label] = "Skipped"
                else:
                    summary[label] = self.collected.get(key, "Skipped")
            else:
                summary[label] = self.collected.get(key, "Skipped")
        return summary

    def _build_final_json(self) -> dict[str, Any]:
        pain_points = self.collected.get("customer_pain_points", [])
        techs = self.collected.get("cisco_technologies", [])
        fmt = self.collected.get("proposal_output_format", "")

        result = {
            "Customer Account Name": self.collected.get("customer_account_name", ""),
            "Industry": self._value_or_skipped("industry"),
            "Organization Size": self._value_or_skipped("organization_size"),
            "Current Infrastructure": self._value_or_skipped("current_infrastructure"),
            "Customer Pain Points": ", ".join(pain_points),
            "Cisco Technologies to be Proposed": techs,
            "Next Steps": self.collected.get("next_steps", ""),
            "DEAL ID": self._value_or_skipped("deal_id"),
            "Language": self.collected.get("language", ""),
            "Proposal Output Format": fmt,
        }

        if fmt == "word":
            result["Proposal Form Length"] = self.collected.get("proposal_form_length", "")
        return result

    def _value_or_skipped(self, key: str) -> str:
        if key in self.skipped:
            return "Skipped"
        return self.collected.get(key, "")

    def _format_available_data(self) -> str:
        lines = []
        display_map = {
            "customer_account_name": "Customer Account Name",
            "industry": "Industry",
            "organization_size": "Organization Size",
            "current_infrastructure": "Current Infrastructure",
            "cisco_technologies": "Cisco Technologies to be Proposed",
            "deal_id": "Deal ID",
            "language": "Language",
            "proposal_output_format": "Proposal Output Format",
            "proposal_form_length": "Proposal Form Length",
        }
        for key, label in display_map.items():
            val = self.collected.get(key)
            if val is not None and val != "" and val != []:
                if isinstance(val, list):
                    val = ", ".join(val)
                lines.append(f"  {label}: {val}")
        return "\n".join(lines)

    @staticmethod
    def redirect_off_topic(topic: str) -> str:
        return OUT_OF_CONTEXT_REDIRECT.format(topic=topic)


def _parse_list_input(text: str) -> list[str]:
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


def _title_language(text: str) -> str:
    mapping = {
        "english": "English",
        "german": "German",
        "italian": "Italian",
        "french": "French",
        "spanish": "Spanish",
        "japanese": "Japanese",
        "simplified chinese": "Simplified Chinese",
    }
    return mapping.get(text.lower(), text)


def _extract_pain_points(
    current_infrastructure: str,
    industry: str | None = None,
    organization_size: str | None = None,
) -> dict[str, Any]:
    with open(TOOLS_FIXTURE) as f:
        data = json.load(f)

    text = current_infrastructure.lower()
    if industry:
        text += " " + industry.lower()
    if organization_size:
        text += " " + organization_size.lower()

    found = []
    for pattern in data["pain_point_patterns"]:
        if any(kw in text for kw in pattern["keywords"]):
            found.extend(pattern["pain_points"])

    seen: set[str] = set()
    unique = []
    for pp in found:
        if pp not in seen:
            seen.add(pp)
            unique.append(pp)

    return {"pain_points": unique, "count": len(unique)}


def _recommend_products(
    pain_points: list[str],
    existing_technologies: list[str] | None = None,
) -> dict[str, Any]:
    with open(TOOLS_FIXTURE) as f:
        data = json.load(f)

    recs = set(existing_technologies or [])
    mapping = data["product_recommendations"]

    for pp in pain_points:
        for product in mapping.get(pp, []):
            recs.add(product)

    if not recs:
        recs = set(data["default_recommendations"])

    return {"recommendations": sorted(recs), "count": len(recs)}


def _suggest_opportunities(
    customer_account: str,
    batch_offset: int = 0,
    batch_size: int = 10,
) -> dict[str, Any]:
    with open(SALESFORCE_FIXTURE) as f:
        data = json.load(f)

    if data.get("customer_account") != customer_account:
        return {"opportunities": [], "total": 0, "has_more": False}

    all_opps = [
        {k: v for k, v in opp.items() if k != "savm_id"}
        for opp in data.get("opportunities", [])
    ]
    batch = all_opps[batch_offset : batch_offset + batch_size]
    return {
        "opportunities": batch,
        "total": len(all_opps),
        "has_more": batch_offset + batch_size < len(all_opps),
        "next_offset": batch_offset + batch_size if batch_offset + batch_size < len(all_opps) else None,
    }
