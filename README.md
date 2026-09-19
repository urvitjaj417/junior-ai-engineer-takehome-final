# Junior AI Engineer Take-Home

This repository implements all three assignments from the provided brief. The examples are intentionally small, deterministic, and runnable without an API key. Each assignment also exposes an optional OpenAI-compatible adapter through environment variables so the same orchestration can be exercised with a real model.

## Requirements

Use Python 3.11 or newer. Install dependencies with:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run each assignment from its folder. The committed transcripts are generated from the deterministic mode and show the required success, failure, review, resume, and self-check behavior.

| Folder | Focus | Run command |
|---|---|---|
| `assignment-1` | Tool-using research agent | `python assignment-1/research_agent.py --scenario clean` |
| `assignment-2` | Worker plus one-pass reviewer | `python assignment-2/review_chain.py --scenario approve` |
| `assignment-3` | Resumable sequential agent with self-check | `python assignment-3/resumable_agent.py --scenario stop-resume` |

The design uses LangGraph in all three assignments. Each assignment has a reproducible offline path and an optional model-backed path. Assignment 1 validates model-proposed tool actions locally; Assignment 2 validates model-generated code by executing tests; Assignment 3 validates model summaries before finalizing them. Assignment 3 uses LangGraph's `SqliteSaver` checkpointer for durable state rather than implementing a custom persistence layer.

To reproduce the complete evidence set, run the clean and edge-case commands shown in each assignment README. The programs have no hidden network dependency in their default mode, which makes the result straightforward for a reviewer to clone and verify.

The rubric-critical checks can also be run in one command:

```bash
python smoke_test.py
```

For a human-readable demonstration of every assignment scenario, run:

```bash
python demo_all.py
```

Use `python demo_all.py --live` to pass live mode to all three assignments. The runner saves complete outputs to the ignored local file `demo-results.local.json` and prints a concise status line for each of the six required scenarios.

## LLM adapter

Set `OPENAI_API_KEY`, `OPENAI_API_BASE`, and optionally `MODEL` to use `llm_adapter.py` for an OpenAI-compatible completion. The default execution path is deterministic so reviewers can reproduce the transcripts without credentials. The adapter is deliberately isolated from the state machines; it does not change the required control-flow behavior.

For the follow-up discussion, see [INTERVIEW_GUIDE.md](INTERVIEW_GUIDE.md). It explains the three graphs, failure and resume behavior, likely technical questions, and accurate answers.

## Assumptions

The prompt asks for at least two assignments, but this repository includes all three. A "reasoning trace" is implemented as an auditable decision log containing the decision, reason, action, and result. It does not expose hidden model chain-of-thought. A mocked failure is injected explicitly in Assignment 1, and the agent records the failure before choosing a fallback tool.
