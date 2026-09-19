from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from typing import Any, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

try:
    from llm_adapter import ask_model
except ImportError:
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
    from llm_adapter import ask_model


ITEMS = {
    "item1": "Alpha service stores customer profiles.",
    "item2": "Beta service emits audit events.",
    "item3": "Gamma service retries transient requests.",
    "item4": "Delta service encrypts backups.",
    "item5": "Epsilon service exposes health checks.",
}


class ResumeState(TypedDict, total=False):
    items: list[str]
    completed: list[str]
    results: dict[str, str]
    next_index: int
    stop_after: int | None
    paused: bool
    checked: bool
    resume: bool
    issues: list[str]
    llm_calls: int
    live: bool
    trace: list[dict[str, Any]]
    corrupt_item: str | None


def process_item(state: ResumeState) -> ResumeState:
    completed = list(state.get("completed", []))
    results = dict(state.get("results", {}))
    trace = list(state.get("trace", []))
    items = state.get("items", list(ITEMS))
    next_index = state.get("next_index", 0)
    if state.get("resume"):
        next_index = 0
    stop_after = state.get("stop_after")
    corrupt_item = state.get("corrupt_item")

    while next_index < len(items) and items[next_index] in completed:
        trace.append({"action": "skip", "item": items[next_index], "reason": "already completed in checkpoint"})
        next_index += 1
    if next_index >= len(items):
        return {"next_index": next_index, "trace": trace, "paused": False}

    item = items[next_index]
    source = ITEMS[item]
    llm_calls = state.get("llm_calls", 0)
    if state.get("live"):
        llm_calls += 1
        try:
            summary = ask_model(f"Summarize this sentence in one concise sentence while preserving its key fact:\n{source}", system="You are a careful summarization worker.").strip()
            if not summary:
                raise ValueError("empty model summary")
        except Exception:
            summary = f"Summary of {item}: {source}"
    else:
        summary = f"Summary of {item}: {source}"
    if item == corrupt_item:
        summary = ""
    results[item] = summary
    completed.append(item)
    next_index += 1
    trace.append({"action": "process", "item": item, "result": summary or "<empty deliberately injected result>"})
    paused = stop_after is not None and len(completed) >= stop_after
    if paused:
        trace.append({"action": "pause", "reason": f"temporary stop requested after {item}"})
    return {"completed": completed, "results": results, "next_index": next_index, "paused": paused, "resume": False, "trace": trace, "llm_calls": llm_calls}


def route_after_process(state: ResumeState) -> str:
    if state.get("paused"):
        return "end"
    if state.get("next_index", 0) >= len(state.get("items", list(ITEMS))):
        return "check"
    return "process"


def check_results(state: ResumeState) -> ResumeState:
    issues: list[str] = []
    for item in state.get("items", list(ITEMS)):
        expected = f"Summary of {item}: {ITEMS[item]}"
        actual = state.get("results", {}).get(item, "")
        if not actual:
            issues.append(f"{item} is empty.")
        elif state.get("live") and ITEMS[item].split()[0].lower() not in actual.lower():
            issues.append(f"{item} does not preserve the source subject.")
        elif not state.get("live") and actual != expected:
            issues.append(f"{item} does not match its source.")
    trace = list(state.get("trace", []))
    trace.append({"action": "self-check", "status": "issues found" if issues else "passed", "issues": issues})
    return {"checked": True, "issues": issues, "trace": trace}


def build_graph(checkpointer):
    graph = StateGraph(ResumeState)
    graph.add_node("process", process_item)
    graph.add_node("check", check_results)
    graph.add_edge(START, "process")
    graph.add_conditional_edges("process", route_after_process, {"process": "process", "check": "check", "end": END})
    graph.add_edge("check", END)
    return graph.compile(checkpointer=checkpointer)


def run_stop_resume(live: bool = False) -> dict[str, Any]:
    db_path = os.path.join(os.path.dirname(__file__), "resume_demo.sqlite")
    if os.path.exists(db_path):
        os.remove(db_path)
    connection = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(connection)
    app = build_graph(checkpointer)
    config = {"configurable": {"thread_id": "assignment-3-demo"}}
    first = app.invoke({"items": list(ITEMS), "completed": [], "results": {}, "next_index": 0, "stop_after": 3, "paused": False, "checked": False, "issues": [], "llm_calls": 0, "trace": [], "corrupt_item": "item4", "live": live}, config)
    second = app.invoke({"stop_after": None, "paused": False, "resume": True}, config)
    connection.close()
    return {"first_run": first, "second_run": second, "database": db_path}


def run_clean(live: bool = False) -> dict[str, Any]:
    db_path = os.path.join(os.path.dirname(__file__), "clean_demo.sqlite")
    if os.path.exists(db_path):
        os.remove(db_path)
    connection = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(connection)
    app = build_graph(checkpointer)
    config = {"configurable": {"thread_id": "assignment-3-clean"}}
    result = app.invoke({"items": list(ITEMS), "completed": [], "results": {}, "next_index": 0, "stop_after": None, "paused": False, "checked": False, "issues": [], "llm_calls": 0, "trace": [], "corrupt_item": None, "live": live}, config)
    connection.close()
    return {"run": result, "database": db_path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["stop-resume", "clean"], default="stop-resume")
    parser.add_argument("--live", action="store_true", help="Use the configured model for summaries.")
    args = parser.parse_args()
    result = run_stop_resume(live=args.live) if args.scenario == "stop-resume" else run_clean(live=args.live)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
