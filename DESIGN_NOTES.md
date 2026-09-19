# Design Notes for the Follow-up Conversation

## Assignment 1

The key design choice is to separate **planning** from **execution**. The planner sees the evidence collected so far, the failed tools, and the required evidence categories. It chooses an action from the registered tools. The executor owns the six-call budget and records success or failure. A failed tool is added to `failed_tools`, which prevents an accidental retry and makes an independent fallback possible. In live mode, the model proposes the next action as JSON, but the local registry validates the action. This prevents a model from inventing a tool name or bypassing the safety limit. The default transcript is deterministic because reproducibility is more useful in a take-home submission than an unrepeatable network call.

The trace records observable agent decisions. It deliberately does not claim to expose hidden model reasoning. Each event says what action was selected, why it was useful, and what result came back.

## Assignment 2

The worker and reviewer are separate LangGraph nodes with a one-way handoff. The reviewer runs the submitted function against representative inputs instead of approving based on formatting. There is no revision edge in the graph, so rejection is final for that run, as required by the prompt.

## Assignment 3

The checkpoint is owned by LangGraph's SQLite saver. The application state contains only the fields needed to resume: completed item IDs, results, the next index, and the check outcome. On resume, the graph scans from the beginning, logs already completed items as skipped, and continues from the first unfinished item. The final check is deliberately independent of processing so that a blank result cannot pass silently.

The optional live path uses one model call per item and records that count in state. A model failure falls back to a local summary, while live-mode validation checks that the source subject is preserved.

## Trade-off

The deterministic mode is the committed evidence path. It avoids requiring a reviewer to configure a provider key and makes failure and resume behavior stable. The optional OpenAI-compatible adapter is available to all three assignments: it can propose research actions, generate the review candidate, or summarize items. In each case, local validation remains authoritative and model output cannot bypass safety-critical orchestration.
