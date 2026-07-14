#!/usr/bin/env python3
"""Interactive CLI for GTM workflows."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.router import GTMRouter
from story_library.competitive_brief import generate_competitive_brief
from story_library.discovery_brief import generate_discovery_brief
from story_library.generator import generate_proposal

GENERATORS = {
    "proposal": generate_proposal,
    "discovery": generate_discovery_brief,
    "competitive": generate_competitive_brief,
}


def main():
    parser = argparse.ArgumentParser(description="GTM agent ecosystem CLI")
    parser.add_argument("customer_account", nargs="+", help="Customer account name")
    parser.add_argument(
        "--workflow",
        choices=["proposal", "discovery", "competitive"],
        default="proposal",
        help="Workflow to run (default: proposal)",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate document after intake completes",
    )
    args = parser.parse_args()

    customer = " ".join(args.customer_account)
    router = GTMRouter()
    session_id = "cli"
    resp = router.start(args.workflow, customer, session_id)
    print(resp.message)

    while resp.awaiting_input:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break
        resp = router.process(session_id, user_input)
        print(f"\n{resp.message}")
        if resp.done:
            if args.generate and resp.json_output:
                generator = GENERATORS[args.workflow]
                path = generator(resp.json_output)
                print(f"\nDocument saved to: {path}")
            break


if __name__ == "__main__":
    main()
