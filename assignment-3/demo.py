"""Run Assignment 3's clean and stop-resume demonstrations."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(scenario: str, live: bool) -> dict:
    command = [sys.executable, str(HERE / "resumable_agent.py"), "--scenario", scenario]
    if live:
        command.append("--live")
    completed = subprocess.run(command, cwd=HERE, capture_output=True, text=True, check=True)
    return json.loads(completed.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Demonstrate Assignment 3.")
    parser.add_argument("--live", action="store_true", help="Use the model for summaries when credentials are configured.")
    args = parser.parse_args()
    print(f"Assignment 3 demo | mode={'live with fallback' if args.live else 'deterministic'}")
    resumed = run("stop-resume", args.live)
    clean = run("clean", args.live)
    second = resumed["second_run"]
    assert len(second["completed"]) == 5
    assert "item4 is empty." in second["issues"]
    assert "already completed in checkpoint" in json.dumps(second["trace"])
    assert clean["run"]["checked"] is True and not clean["run"]["issues"]
    print(f"PASS | stop-resume | completed={len(second['completed'])} | issues={second['issues']}")
    print(f"PASS | clean | completed={len(clean['run']['completed'])} | checked={clean['run']['checked']}")
    print("Assignment 3 demo passed")


if __name__ == "__main__":
    main()
