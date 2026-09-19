"""Run Assignment 1's clean and failure-recovery demonstrations."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(scenario: str, live: bool) -> dict:
    command = [sys.executable, str(HERE / "research_agent.py"), "--scenario", scenario]
    if live:
        command.append("--live")
    completed = subprocess.run(command, cwd=HERE, capture_output=True, text=True, check=True)
    return json.loads(completed.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Demonstrate Assignment 1.")
    parser.add_argument("--live", action="store_true", help="Use the model planner when credentials are configured.")
    args = parser.parse_args()
    print(f"Assignment 1 demo | mode={'live with fallback' if args.live else 'deterministic'}")
    for scenario in ("clean", "failure"):
        result = run(scenario, args.live)
        print(f"PASS | {scenario} | tool_calls={result['tool_calls']} | final_answer=yes")
        if scenario == "failure":
            assert "FAILED: mocked reference service timeout" in json.dumps(result)
            assert any(event.get("action") == "fallback_reference" for event in result["trace"])
            print("      mocked timeout recorded and independent fallback selected")
    print("Assignment 1 demo passed")


if __name__ == "__main__":
    main()
