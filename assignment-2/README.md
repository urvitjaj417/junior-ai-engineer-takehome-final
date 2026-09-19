# Assignment 2 — Multi-Agent Task with Review

The worker writes a Python function that computes the average of a non-empty list of numbers. The reviewer checks one attempt against four concrete criteria: the function is named `average`, it accepts exactly one argument, it rejects an empty list with `ValueError`, and it returns the arithmetic mean for valid numeric input. The reviewer parses and executes the candidate against representative inputs, so the verdict is based on observable behavior rather than keyword matching. It runs exactly once and returns either `approved` with the final output or `rejected` with specific reasons.

LangGraph models the clean handoff from worker to reviewer. Deterministic mode makes the two required transcripts reproducible. The `--scenario reject` run intentionally violates the empty-input criterion. The report includes total LLM calls; deterministic mode reports zero external LLM calls, while the optional adapter can be used to replace worker and reviewer text generation.

```bash
python review_chain.py --scenario approve
python review_chain.py --scenario reject
python review_chain.py --scenario approve --live  # requires OPENAI_API_KEY
```

To run both Assignment 2 demonstrations together:

```bash
python demo.py
python demo.py --live
```

With `--live`, the worker asks the configured model for the approval candidate and reports one LLM call. The rejection scenario intentionally keeps its deterministic invalid candidate so the required negative transcript remains stable. If the model is unavailable or returns invalid Python, the worker falls back to the reproducible candidate. The reviewer remains locally executable and behavior-based, so model output cannot bypass the approval criteria.
