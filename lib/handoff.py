"""Merge confirmed workflow JSON across discovery, competitive, and proposal."""

from __future__ import annotations

from typing import Any

CONTINUE_OPTIONS: dict[str, list[dict[str, str]]] = {
    "discovery": [
        {"id": "competitive", "label": "Continue to Competitive Brief"},
        {"id": "proposal", "label": "Continue to Build Proposal"},
    ],
    "competitive": [
        {"id": "proposal", "label": "Continue to Build Proposal"},
    ],
    "proposal": [],
}


def _parse_pain_points(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(p).strip() for p in value if str(p).strip()]
    if isinstance(value, str) and value.strip() and value != "Skipped":
        return [p.strip() for p in value.split(",") if p.strip()]
    return []


def _skipped(value: Any) -> bool:
    return value in (None, "", "Skipped", [])


def discovery_to_handoff(data: dict[str, Any]) -> dict[str, Any]:
    """Map confirmed discovery JSON into assistant prefill keys."""
    result: dict[str, Any] = {"_handoff_sources": ["discovery"]}
    mapping = {
        "Industry": "industry",
        "Organization Size": "organization_size",
        "Current Infrastructure": "current_infrastructure",
    }
    for src, dest in mapping.items():
        val = data.get(src)
        if not _skipped(val):
            result[dest] = val

    pains = _parse_pain_points(data.get("Customer Pain Points"))
    if pains:
        result["customer_pain_points"] = pains

    techs = data.get("Cisco Technologies to be Proposed")
    if techs:
        result["cisco_technologies"] = list(techs)

    meddpicc = data.get("MEDDPICC")
    if isinstance(meddpicc, dict) and meddpicc:
        result["meddpicc"] = meddpicc

    stage = data.get("CX Lifecycle Stage")
    if stage:
        result["cx_lifecycle_stage"] = stage

    return result


def competitive_to_handoff(data: dict[str, Any]) -> dict[str, Any]:
    """Map confirmed competitive JSON into assistant prefill keys."""
    result: dict[str, Any] = {"_handoff_sources": ["competitive"]}
    techs = data.get("Cisco Technologies to be Proposed")
    if techs:
        result["cisco_technologies"] = list(techs)
    competitors = data.get("Competitors")
    if competitors:
        result["competitors"] = list(competitors)
    return result


def merge_handoff_for(target_workflow: str, prior_outputs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Build one handoff dict for starting *target_workflow* from prior confirmed JSON.

    prior_outputs: [{"workflow": "discovery"|"competitive"|"proposal", "json": {...}}, ...]
    """
    merged: dict[str, Any] = {"_handoff_sources": []}
    for item in prior_outputs:
        workflow = item.get("workflow", "")
        data = item.get("json") or {}
        if workflow == "discovery":
            chunk = discovery_to_handoff(data)
        elif workflow == "competitive":
            chunk = competitive_to_handoff(data)
        else:
            continue
        for src in chunk.get("_handoff_sources", []):
            if src not in merged["_handoff_sources"]:
                merged["_handoff_sources"].append(src)
        for key, val in chunk.items():
            if key == "_handoff_sources":
                continue
            merged[key] = val
    return merged


def continue_options(completed_workflow: str) -> list[dict[str, str]]:
    return list(CONTINUE_OPTIONS.get(completed_workflow, []))
