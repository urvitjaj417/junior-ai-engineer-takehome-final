from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

try:
    from llm_adapter import ask_model
except ImportError:  # Running the file directly from its assignment folder.
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
    from llm_adapter import ask_model


QUESTION = "For a read-heavy API serving 10,000 requests per second, when should a team choose cache-aside over write-through caching, and what sizing trade-offs follow?"
ACTIVE_TOOLS: ResearchTools | None = None


class ResearchState(TypedDict, total=False):
    question: str
    scenario: str
    evidence: dict[str, str]
    call_count: int
    trace: list[dict[str, Any]]
    next_tool: str
    final_answer: str
    done: bool
    failed_tools: list[str]
    live: bool
    planner_calls: int


@dataclass
class ToolResult:
    ok: bool
    text: str


class ResearchTools:
    """Small deterministic tools; replace their bodies with real integrations in production."""

    def __init__(self, scenario: str):
        self.scenario = scenario
        self.failed_once = False

    def semantics(self) -> ToolResult:
        return ToolResult(True, "Cache-aside loads on a miss and writes the cache after the backing store; the application controls invalidation. Write-through writes the cache and backing store together, which simplifies freshness but adds write latency.")

    def operations(self) -> ToolResult:
        return ToolResult(True, "Cache-aside suits read-heavy workloads when occasional stale or cold reads are acceptable and invalidation can be owned by the application. Write-through is safer when reads must see recently written values, but every write pays cache-write latency and cache availability becomes part of the write path.")

    def calculator(self) -> ToolResult:
        requests_per_second = 10_000
        hit_rate = 0.90
        origin_rps = requests_per_second * (1 - hit_rate)
        return ToolResult(True, f"At {requests_per_second:,} requests/s and a {hit_rate:.0%} hit rate, expected backing-store reads are {origin_rps:,.0f}/s. If hit rate falls to 80%, origin load becomes {requests_per_second * 0.20:,.0f}/s.")

    def flaky_reference(self) -> ToolResult:
        if self.scenario == "failure" and not self.failed_once:
            self.failed_once = True
            raise TimeoutError("mocked reference service timeout")
        return ToolResult(True, "Fallback reference: cache-aside minimizes write-path coupling; write-through trades higher write latency for stronger cache freshness after writes.")

    def fallback_reference(self) -> ToolResult:
        return ToolResult(True, "Independent fallback reference: cache-aside keeps the write path independent from cache availability; write-through gives a fresher cache after writes but couples writes to cache health.")

    def call(self, name: str) -> ToolResult:
        return getattr(self, name)()


TOOL_COVERAGE = {
    "semantics": {"semantics"},
    "operations": {"operations"},
    "calculator": {"capacity"},
    "flaky_reference": {"freshness"},
    "fallback_reference": {"freshness"},
}
REQUIRED_EVIDENCE = {"semantics", "operations", "capacity"}


def choose_next(state: ResearchState) -> tuple[str, str]:
    """Choose the next action from evidence gaps, not from a fixed step counter."""
    evidence = state.get("evidence", {})
    failed = set(state.get("failed_tools", []))
    if state.get("scenario") == "failure" and "flaky_reference" not in evidence and "flaky_reference" not in failed:
        return "flaky_reference", "Exercise the failure path so the agent can demonstrate recovery."
    if failed and "fallback_reference" not in evidence:
        return "fallback_reference", "The previous tool failed; use an independent fallback rather than retrying the same tool."
    missing = REQUIRED_EVIDENCE - set(evidence)
    if not missing:
        return "done", "The required evidence categories are covered; answer now."
    candidates = [name for name, covers in TOOL_COVERAGE.items() if name not in evidence and name not in failed]
    candidates.sort(key=lambda name: len(TOOL_COVERAGE[name] & missing), reverse=True)
    if not candidates:
        return "done", "No unused tool can cover the remaining evidence within the safety budget."
    selected = candidates[0]
    return selected, f"The evidence gap is {sorted(missing)}; {selected} covers {sorted(TOOL_COVERAGE[selected] & missing)}."


def choose_next_with_model(state: ResearchState) -> tuple[str, str]:
    """Ask the configured model for a tool choice, then validate it locally."""
    available = [name for name in TOOL_COVERAGE if name not in state.get("evidence", {}) and name not in state.get("failed_tools", [])]
    prompt = {
        "question": state.get("question"),
        "evidence": state.get("evidence", {}),
        "failed_tools": state.get("failed_tools", []),
        "available_tools": available,
        "required_evidence": sorted(REQUIRED_EVIDENCE),
        "instruction": "Choose one available tool or done. Return JSON with action and reason. Do not choose a failed tool.",
    }
    try:
        raw = ask_model(json.dumps(prompt), system="You are a careful research-agent planner. Choose the next useful action; do not invent tool names.")
    except Exception as exc:
        fallback, reason = choose_next(state)
        return fallback, f"Model call failed ({type(exc).__name__}: {exc}); using validated local fallback. {reason}"
    try:
        decision = json.loads(raw)
        action = decision["action"]
        reason = decision["reason"]
        if action not in available and action != "done":
            raise ValueError(f"invalid action: {action}")
        missing = REQUIRED_EVIDENCE - set(state.get("evidence", {}))
        if action == "done" and missing:
            fallback, fallback_reason = choose_next(state)
            return fallback, f"Model requested early completion, but evidence is still missing ({sorted(missing)}); {fallback_reason}"
        return action, f"Model decision: {reason}"
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        fallback, reason = choose_next(state)
        return fallback, f"Model output was invalid ({exc}); using validated local fallback. {reason}"


def planner(state: ResearchState) -> ResearchState:
    if state.get("live"):
        tool, reason = choose_next_with_model(state)
        planner_calls = state.get("planner_calls", 0) + 1
    else:
        tool, reason = choose_next(state)
        planner_calls = state.get("planner_calls", 0)
    trace = list(state.get("trace", []))
    event = {"step": len(trace) + 1, "decision": "answer" if tool == "done" else "use_tool", "reason": reason, "action": tool}
    if tool == "done":
        event["result"] = "Evidence accepted; handing off to finalization."
    trace.append(event)
    return {"next_tool": tool, "trace": trace, "done": tool == "done", "planner_calls": planner_calls}


def execute_tool(state: ResearchState) -> ResearchState:
    tool_name = state["next_tool"]
    if tool_name == "done":
        return state
    trace = list(state.get("trace", []))
    calls = state.get("call_count", 0)
    if calls >= 6:
        trace.append({"step": len(trace) + 1, "decision": "stop", "reason": "Six-tool-call safety budget reached.", "action": "stop"})
        return {"trace": trace, "done": True, "next_tool": "done"}
    if ACTIVE_TOOLS is None:
        raise RuntimeError("tool registry was not initialized")
    tools = ACTIVE_TOOLS
    try:
        result = tools.call(tool_name)  # type: ignore[union-attr]
        evidence = dict(state.get("evidence", {}))
        evidence[tool_name] = result.text
        trace[-1]["result"] = result.text
        trace[-1]["status"] = "ok"
        return {"evidence": evidence, "call_count": calls + 1, "trace": trace}
    except Exception as exc:
        trace[-1]["result"] = f"FAILED: {exc}"
        trace[-1]["status"] = "recovered"
        trace[-1]["recovery"] = "Recorded the failure and marked this tool unavailable so planning can select an independent fallback."
        failed_tools = list(state.get("failed_tools", []))
        failed_tools.append(tool_name)
        return {"call_count": calls + 1, "trace": trace, "failed_tools": failed_tools}


def finalize(state: ResearchState) -> ResearchState:
    evidence = state.get("evidence", {})
    answer = (
        "Recommendation: choose cache-aside for this read-heavy API when the team can tolerate cold misses or brief staleness and can implement reliable invalidation. "
        "Choose write-through when freshness after writes is more important than write latency and the team accepts cache availability as part of the write path. "
        f"The capacity estimate is {evidence.get('calculator', 'not available')}. "
        "The agent recovered from any tool failure by recording it and relying on the remaining independent evidence."
    )
    trace = list(state.get("trace", []))
    trace.append({"step": len(trace) + 1, "decision": "finalize", "reason": "The planner determined that the available evidence was sufficient or the safety budget required stopping.", "action": "done", "result": answer})
    return {"final_answer": answer, "trace": trace}


def build_graph():
    graph = StateGraph(ResearchState)
    graph.add_node("planner", planner)
    graph.add_node("execute_tool", execute_tool)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "planner")
    graph.add_conditional_edges("planner", lambda s: "finalize" if s.get("done") else "execute_tool", {"finalize": "finalize", "execute_tool": "execute_tool"})
    graph.add_edge("execute_tool", "planner")
    graph.add_edge("finalize", END)
    return graph.compile()


def run(scenario: str, live: bool = False) -> ResearchState:
    # The tool object is kept outside the serialized public state to remain simple and auditable.
    global ACTIVE_TOOLS
    ACTIVE_TOOLS = ResearchTools(scenario)
    app = build_graph()
    initial: ResearchState = {"question": QUESTION, "scenario": scenario, "evidence": {}, "call_count": 0, "trace": [], "done": False, "failed_tools": [], "live": live, "planner_calls": 0}
    return app.invoke(initial)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["clean", "failure"], default="clean")
    parser.add_argument("--live", action="store_true", help="Use the configured OpenAI-compatible model for planning.")
    args = parser.parse_args()
    result = run(args.scenario, live=args.live)
    print(json.dumps({"question": QUESTION, "scenario": args.scenario, "live": args.live, "tool_calls": result.get("call_count"), "planner_calls": result.get("planner_calls"), "trace": result.get("trace"), "final_answer": result.get("final_answer")}, indent=2))


if __name__ == "__main__":
    main()
