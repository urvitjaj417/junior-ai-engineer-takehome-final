"""Run the rubric-critical checks without requiring pytest."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def run(*args: str) -> dict:
    output = subprocess.check_output([sys.executable, *args], cwd=ROOT, text=True)
    return json.loads(output)


def main() -> None:
    clean = run("assignment-1/research_agent.py", "--scenario", "clean")
    failure = run("assignment-1/research_agent.py", "--scenario", "failure")
    assert clean["tool_calls"] <= 6
    assert failure["tool_calls"] <= 6
    assert "FAILED: mocked reference service timeout" in json.dumps(failure)
    assert any(event.get("action") == "fallback_reference" for event in failure["trace"])

    approved = run("assignment-2/review_chain.py", "--scenario", "approve")
    rejected = run("assignment-2/review_chain.py", "--scenario", "reject")
    assert approved["verdict"] == "approved"
    assert rejected["verdict"] == "rejected"
    assert any("ZeroDivisionError" in reason for reason in rejected["reasons"])
    assert len(rejected["trace"]) == 2

    resumed = run("assignment-3/resumable_agent.py", "--scenario", "stop-resume")
    second_trace = json.dumps(resumed["second_run"]["trace"])
    assert "already completed in checkpoint" in second_trace
    assert resumed["second_run"]["issues"] == ["item4 is empty."]

    print("smoke tests passed")


if __name__ == "__main__":
    main()
