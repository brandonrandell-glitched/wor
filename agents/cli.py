#!/usr/bin/env python3
"""Interactive CLI for the proposal-building assistant."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.proposal_assistant import ProposalAssistant
from story_library.generator import generate_proposal


def main():
    parser = argparse.ArgumentParser(description="Proposal-building assistant CLI")
    parser.add_argument("customer_account", nargs="+", help="Customer account name")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate proposal document after intake completes",
    )
    args = parser.parse_args()

    customer = " ".join(args.customer_account)
    assistant = ProposalAssistant()
    resp = assistant.start(customer)
    print(resp.message)

    while resp.awaiting_input:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break
        resp = assistant.process_input(user_input)
        print(f"\n{resp.message}")
        if resp.done:
            if args.generate and resp.json_output:
                path = generate_proposal(resp.json_output)
                print(f"\nProposal document saved to: {path}")
            break


if __name__ == "__main__":
    main()
