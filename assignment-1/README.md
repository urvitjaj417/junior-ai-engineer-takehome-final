# Assignment 1 — Tool-Using Research Agent

The research question is: **For a read-heavy API serving 10,000 requests per second, when should a team choose cache-aside over write-through caching, and what sizing trade-offs follow?** A useful answer needs more than one lookup because it combines semantics, operational behavior, and a capacity calculation.

## Design

The LangGraph state machine has an LLM-style planner, a tool executor, and a finalizer. In deterministic mode, the planner chooses its next tool from the current evidence gaps instead of following a fixed step counter. The available tools are a cache-semantics reference lookup, an operational-trade-off lookup, a calculator, and two freshness references. The failure scenario deliberately makes the first freshness reference time out; the planner marks it unavailable and selects the independent fallback rather than retrying the same failed tool. It stops when the evidence contains semantics, operational trade-offs, and a calculation, or when the six-call budget is exhausted.

Each step emits an auditable trace record with the decision, reason, action, and result. The failing scenario injects a timeout on the first tool call. The agent records it, adds a limitation, and chooses a fallback reference rather than crashing or pretending the call succeeded.

## Run

```bash
python research_agent.py --scenario clean
python research_agent.py --scenario failure
python research_agent.py --scenario clean --live  # requires OPENAI_API_KEY
```

To run both Assignment 1 demonstrations together:

```bash
python demo.py
python demo.py --live
```

The optional `--live` flag asks the configured OpenAI-compatible model to choose the next action as JSON. The program validates the returned action against the local tool registry and falls back to the deterministic planner if the model is unavailable or returns malformed output. The committed transcripts use deterministic mode so a reviewer can reproduce them without credentials.
