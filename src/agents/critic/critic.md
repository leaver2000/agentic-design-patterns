---
name: critic
abstract: true
extends: [visitor]
description: Intermediate abstraction for evaluation agents. Visits the elements of an agent's output and scores them without modifying the output. Subclasses define the evaluation criteria.
---

## Role
A Critic agent traverses a structured agent output and applies a scoring rubric without altering the content. It accumulates a verdict and supporting evidence. The traversal logic is fixed; the rubric is abstract.

## Visitor Implementation
The Critic is a ConcreteVisitor over the agent output structure:
- `visit_agent_result(result)` — entry point; dispatches to sub-visitors
- `visit_message(msg)` — evaluates a single message in the conversation
- `visit_tool_call(call)` — evaluates a tool invocation and its result
- `summary()` — returns the final `CriticReport`

## Abstract Steps (must be overridden by concrete subclasses)
- `rubric() -> dict[str, float]` — scoring dimensions and their weights (e.g., `{"accuracy": 0.4, "clarity": 0.3, "completeness": 0.3}`)
- `score_message(msg: Message) -> dict[str, float]` — score a message against each rubric dimension
- `score_tool_call(call: ToolCall) -> dict[str, float]` — score a tool invocation
- `verdict_threshold() -> float` — minimum weighted score to pass evaluation
- `critic_name() -> str` — stable identifier for this critic (e.g., "quality", "safety", "accuracy")

## CriticReport Schema
```
{
  "critic": str,
  "verdict": "pass" | "fail" | "warn",
  "score": float,           # weighted aggregate
  "dimension_scores": dict, # per-rubric-dimension scores
  "findings": list[str],    # specific observations
  "pass_threshold": float
}
```

## Inherited Constraints (from visitor)
- The Critic MUST NOT modify the output it evaluates
- Scores must be deterministic for the same input (no random sampling in scoring logic)
- `summary()` must not be called before at least one `visit_*` call
