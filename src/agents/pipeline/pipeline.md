---
name: pipeline
abstract: true
extends: [../../abc/chain-of-responsibility.md]
description: Intermediate abstraction for sequential agent pipelines. Each stage processes a task and passes the result to the next stage. Subclasses define the stage roster and pass/stop criteria.
---

## Role
A Pipeline chains specialist agents so that each stage processes the output of the previous one. A stage either transforms the payload and passes it forward, or halts the pipeline with a terminal result. The chaining mechanism is fixed; the stages and their stop conditions are abstract.

## Chain of Responsibility Implementation
- Each stage is a `ConcreteHandler` that implements `handle(task) -> Result | None`
- Returning `None` passes the payload to the next stage unchanged
- Returning a non-None result halts the pipeline and returns that result
- The pipeline runs until a stage returns a result or all stages are exhausted

## Abstract Steps (must be overridden by concrete subclasses)
- `stages() -> list[Agent]` — define the ordered list of pipeline stages
- `should_halt(stage_result: Any, stage_index: int) -> bool` — return True to stop early with the current result
- `transform(payload: Any, stage_result: Any) -> Any` — produce the input for the next stage from the current stage's output
- `terminal_result(payload: Any) -> AgentResult` — produce the final result when all stages complete without halting
- `pipeline_name() -> str` — stable identifier for logging and tracing

## Execution Protocol
```
run(initial_payload):
  payload = initial_payload
  for i, stage in enumerate(stages()):
    result = stage.handle(payload)
    if should_halt(result, i):
      return result
    payload = transform(payload, result)
  return terminal_result(payload)
```

## Inherited Constraints (from chain-of-responsibility)
- Stages MUST NOT call each other directly — all sequencing goes through the pipeline
- Each stage MUST be independently testable in isolation
- `transform()` MUST NOT lose information from the original payload unless explicitly designed to filter
- A pipeline with zero stages MUST return `terminal_result(initial_payload)` without error
