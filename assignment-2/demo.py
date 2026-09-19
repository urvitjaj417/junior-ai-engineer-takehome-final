"""Run Assignment 2's approval and rejection demonstrations."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(scenario: str, live: bool) -> dict:
    command = [sys.executable, str(HERE / "review_chain.py"), "--scenario", scenario]
    if live:
        command.append("--live")
    completed = subprocess.run(command, cwd=HERE, capture_output=True, text=True, check=True)
    import json
    return json.loads(completed.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Demonstrate Assignment 2.")
    parser.add_argument("--live", action="store_true", help="Use the model for the approval candidate.")
    args = parser.parse_args()
    print(f"Assignment 2 demo | mode={'live with fallback' if args.live else 'deterministic'}")
    approved = run("approve", args.live)
    rejected = run("reject", args.live)
    assert approved["verdict"] == "approved"
    assert rejected["verdict"] == "rejected"
    assert len(rejected["trace"]) == 2
    print(f"PASS | approve | verdict={approved['verdict']} | LLM calls={approved['total_llm_calls']}")
    print(f"PASS | reject | verdict={rejected['verdict']} | reasons={len(rejected['reasons'])}")
    print("Assignment 2 demo passed")


if __name__ == "__main__":
    main()
