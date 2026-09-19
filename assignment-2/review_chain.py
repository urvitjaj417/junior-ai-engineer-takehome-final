from __future__ import annotations

import argparse
import ast
import json
import sys
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

try:
    from llm_adapter import ask_model
except ImportError:
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
    from llm_adapter import ask_model


class ReviewState(TypedDict, total=False):
    scenario: str
    worker_output: str
    verdict: str
    reasons: list[str]
    total_llm_calls: int
    live: bool
    trace: list[dict[str, Any]]


CRITERIA = [
    "function is named average",
    "function accepts one argument",
    "empty input raises ValueError",
    "valid numeric input returns the arithmetic mean",
]


def worker(state: ReviewState) -> ReviewState:
    live = state.get("live", False)
    llm_calls = 0
    generation_note = "deterministic candidate"
    if live and state.get("scenario") != "reject":
        llm_calls = 1
        prompt = "Write only a Python function named average(values). It must return the arithmetic mean for non-empty numeric lists and raise ValueError for an empty list. No markdown fences."
        try:
            output = ask_model(prompt, system="You are the worker agent. Produce one small, testable Python function.").strip()
            if "```" in output:
                output = output.replace("```python", "").replace("```", "").strip()
            ast.parse(output)
            generation_note = "live model candidate"
        except Exception as exc:
            generation_note = f"live model unavailable; deterministic fallback ({type(exc).__name__})"
            output = "def average(values):\n    if not values:\n        raise ValueError('values must not be empty')\n    return sum(values) / len(values)"
    elif state.get("scenario") == "reject":
        output = "def average(values):\n    return sum(values) / len(values)"
    else:
        output = "def average(values):\n    if not values:\n        raise ValueError('values must not be empty')\n    return sum(values) / len(values)"
    trace = list(state.get("trace", []))
    trace.append({"agent": "worker", "decision": "produce one candidate", "mode": generation_note, "result": output})
    return {"worker_output": output, "trace": trace, "total_llm_calls": llm_calls}


def reviewer(state: ReviewState) -> ReviewState:
    code = state["worker_output"]
    reasons: list[str] = []
    try:
        tree = ast.parse(code)
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "average"]
        if not functions:
            reasons.append("The function is not named average.")
        else:
            function = functions[0]
            if len(function.args.args) != 1:
                reasons.append("average must accept exactly one argument.")
            namespace: dict[str, Any] = {}
            exec(compile(tree, "candidate.py", "exec"), {}, namespace)
            candidate = namespace["average"]
            try:
                if candidate([1, 2, 3]) != 2:
                    reasons.append("average([1, 2, 3]) did not return 2.")
            except Exception as exc:
                reasons.append(f"The valid-input test raised {type(exc).__name__}: {exc}.")
            try:
                candidate([])
                reasons.append("average([]) returned instead of raising ValueError.")
            except ValueError:
                pass
            except Exception as exc:
                reasons.append(f"average([]) raised {type(exc).__name__}, not ValueError.")
    except (SyntaxError, KeyError, TypeError) as exc:
        reasons.append(f"The candidate could not be parsed or loaded: {type(exc).__name__}: {exc}.")
    verdict = "approved" if not reasons else "rejected"
    trace = list(state.get("trace", []))
    trace.append({"agent": "reviewer", "decision": "check once against concrete criteria", "criteria": CRITERIA, "verdict": verdict, "reasons": reasons})
    return {"verdict": verdict, "reasons": reasons, "trace": trace, "total_llm_calls": state.get("total_llm_calls", 0)}


def build_graph():
    graph = StateGraph(ReviewState)
    graph.add_node("worker", worker)
    graph.add_node("reviewer", reviewer)
    graph.add_edge(START, "worker")
    graph.add_edge("worker", "reviewer")
    graph.add_edge("reviewer", END)
    return graph.compile()


def run(scenario: str, live: bool = False) -> ReviewState:
    return build_graph().invoke({"scenario": scenario, "live": live, "trace": []})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["approve", "reject"], default="approve")
    parser.add_argument("--live", action="store_true", help="Use the configured model to generate the worker candidate.")
    args = parser.parse_args()
    result = run(args.scenario, live=args.live)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
