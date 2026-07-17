#!/usr/bin/env python3
"""Run the Acme Financial Services demo through all three GTM workflows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.competitive_assistant import CompetitiveAssistant
from agents.discovery_assistant import DiscoveryAssistant
from agents.proposal_assistant import ProposalAssistant
from lib.handoff import merge_handoff_for
from story_library.competitive_brief import generate_competitive_brief
from story_library.discovery_brief import generate_discovery_brief
from story_library.generator import generate_proposal

CUSTOMER = "Acme Financial Services"
GENERATORS = {
    "discovery": generate_discovery_brief,
    "competitive": generate_competitive_brief,
    "proposal": generate_proposal,
}


def _run_discovery() -> dict:
    a = DiscoveryAssistant()
    resp = a.start(CUSTOMER)
    while resp.awaiting_input and not resp.done:
        if resp.phase == "pain_points_confirm":
            resp = a.process_input("use")
        elif resp.phase == "technologies_confirm":
            resp = a.process_input("all")
        elif resp.phase == "meddpicc_capture":
            resp = a.process_input(
                "Metrics: reduce MTTR from 48h to under 8h within 12 months\n"
                "Pain: OSFI audit findings on identity and segmentation gaps\n"
                "Champion: VP Infrastructure, Toronto HQ"
            )
        elif resp.phase == "review":
            resp = a.process_input("yes")
        elif resp.phase == "intake":
            resp = a.process_input("skip")
        else:
            resp = a.process_input("yes")
    return resp.json_output or {}


def _run_competitive(prior: list[dict]) -> dict:
    handoff = merge_handoff_for("competitive", prior)
    a = CompetitiveAssistant()
    resp = a.start(CUSTOMER, handoff=handoff)
    while resp.awaiting_input and not resp.done:
        if resp.phase == "competitors":
            resp = a.process_input("Palo Alto Networks, Fortinet")
        elif resp.phase == "review":
            resp = a.process_input("yes")
        elif resp.phase == "technologies":
            resp = a.process_input("use")
        else:
            resp = a.process_input("yes")
    return resp.json_output or {}


def _run_proposal(prior: list[dict]) -> dict:
    handoff = merge_handoff_for("proposal", prior)
    a = ProposalAssistant()
    resp = a.start(CUSTOMER, handoff=handoff)
    steps = [
        "Schedule executive briefing and Zero Trust workshop with CISO — "
        "target September close (CAD 450K OPP-2025-78432)",
        "yes",
        "Economic Buyer: CFO and CISO joint sign-off required for OSFI-aligned programme",
        "yes",
    ]
    step_idx = 0
    while resp.awaiting_input and not resp.done:
        if step_idx < len(steps):
            resp = a.process_input(steps[step_idx])
            step_idx += 1
        elif resp.phase.value == "meddpicc_optional" if hasattr(resp.phase, "value") else resp.phase == "meddpicc_optional":
            resp = a.process_input("skip")
        elif str(resp.phase).endswith("REVIEW") or resp.phase == "review":
            resp = a.process_input("yes")
        else:
            resp = a.process_input("yes")
    return resp.json_output or {}


def run_pipeline(generate: bool = False, output_dir: Path | None = None) -> dict:
    out = output_dir or (ROOT / "output" / "acme-pipeline")
    out.mkdir(parents=True, exist_ok=True)

    discovery_json = _run_discovery()
    prior = [{"workflow": "discovery", "json": discovery_json}]
    competitive_json = _run_competitive(prior)
    prior.append({"workflow": "competitive", "json": competitive_json})
    proposal_json = _run_proposal(prior)

    result = {
        "customer": CUSTOMER,
        "discovery": discovery_json,
        "competitive": competitive_json,
        "proposal": proposal_json,
        "documents": {},
    }

    if generate:
        result["documents"]["discovery"] = str(
            generate_discovery_brief(discovery_json, output_dir=out)
        )
        result["documents"]["competitive"] = str(
            generate_competitive_brief(competitive_json, output_dir=out)
        )
        result["documents"]["proposal"] = str(
            generate_proposal(proposal_json, output_dir=out)
        )

    manifest = out / "acme-pipeline-run.json"
    manifest.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["manifest"] = str(manifest)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Acme three-stage GTM pipeline")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate Word documents for all three stages",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: output/acme-pipeline)",
    )
    args = parser.parse_args()

    result = run_pipeline(generate=args.generate, output_dir=args.output_dir)
    print(json.dumps({k: v for k, v in result.items() if k != "discovery" and k != "competitive" and k != "proposal"}, indent=2))
    if args.generate:
        print("\nDocuments:")
        for stage, path in result["documents"].items():
            print(f"  {stage}: {path}")
    print(f"\nManifest: {result['manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
