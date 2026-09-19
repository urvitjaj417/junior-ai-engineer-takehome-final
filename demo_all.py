"""Run every assignment scenario in one command.

Default mode is deterministic and requires no API key. Add --live to pass the
live flag to each assignment; the assignments safely fall back if credentials
are not configured.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SCENARIOS = [
    ("Assignment 1 - clean", "assignment-1/research_agent.py", "--scenario", "clean"),
    ("Assignment 1 - failure recovery", "assignment-1/research_agent.py", "--scenario", "failure"),
    ("Assignment 2 - approved review", "assignment-2/review_chain.py", "--scenario", "approve"),
    ("Assignment 2 - rejected review", "assignment-2/review_chain.py", "--scenario", "reject"),
    ("Assignment 3 - stop and resume", "assignment-3/resumable_agent.py", "--scenario", "stop-resume"),
    ("Assignment 3 - clean run", "assignment-3/resumable_agent.py", "--scenario", "clean"),
]


def run_one(label: str, script: str, *args: str, live: bool) -> dict:
    command = [sys.executable, script, *args]
    if live:
        command.append("--live")
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"{label} failed:\n{completed.stderr or completed.stdout}")
    return json.loads(completed.stdout)


def summarize(label: str, result: dict) -> str:
    if label.startswith("Assignment 1"):
        return f"final answer ready; tool calls={result.get('tool_calls')}"
    if label == "Assignment 2 - approved review":
        return f"verdict={result.get('verdict')}; LLM calls={result.get('total_llm_calls')}"
    if label == "Assignment 2 - rejected review":
        return f"verdict={result.get('verdict')}; reasons={len(result.get('reasons', []))}"
    if label == "Assignment 3 - stop and resume":
        second = result["second_run"]
        return f"resumed; completed={len(second.get('completed', []))}; issues={second.get('issues')}"
    run = result["run"]
    return f"completed={len(run.get('completed', []))}; checked={run.get('checked')}; issues={run.get('issues')}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all take-home assignment demos.")
    parser.add_argument("--live", action="store_true", help="Pass --live to each assignment. Requires an API key for actual model calls.")
    args = parser.parse_args()

    results: dict[str, dict] = {}
    print("Junior AI Engineer Take-Home Demo")
    print(f"Mode: {'live (with safe fallback)' if args.live else 'deterministic offline'}\n")
    for label, script, *scenario_args in SCENARIOS:
        result = run_one(label, script, *scenario_args, live=args.live)
        results[label] = result
        print(f"PASS | {label} | {summarize(label, result)}")

    output_path = ROOT / "demo-results.local.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nAll six scenarios passed. Full results saved to {output_path.name}.")


if __name__ == "__main__":
    main()
