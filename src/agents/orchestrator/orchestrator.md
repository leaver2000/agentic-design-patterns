---
name: orchestrator
abstract: true
extends: [mediator]
description: Intermediate abstraction for multi-agent coordination. Routes tasks to specialist agents, aggregates results, and manages the interaction protocol. Subclasses define the agent roster and routing logic.
---

## Role
An Orchestrator coordinates a fixed roster of specialist agents. It receives a task, determines which agents handle which parts, sequences their execution, and merges their outputs into a coherent result. Agents know only the Orchestrator — never each other.

## Mediator Implementation
- Colleagues register with the Orchestrator via `register(agent)`
- Agents call `notify(self, event, payload)` when they complete work or surface an issue
- The Orchestrator calls `route(task)` to determine the next step and `dispatch(agent, subtask)` to delegate

## Abstract Steps (must be overridden by concrete subclasses)
- `roster() -> dict[str, Agent]` — define the named agents this orchestrator coordinates
- `decompose(task: Task) -> list[Subtask]` — break the top-level task into agent-sized subtasks
- `assign(subtask: Subtask) -> str` — map a subtask to a roster member by name
- `merge(results: list[AgentResult]) -> AgentResult` — combine agent outputs into the final response
- `on_agent_failure(agent_name: str, error: Exception) -> FailurePolicy` — define retry/skip/escalate behavior

## Execution Protocol
```
run(task):
  subtasks = decompose(task)
  for subtask in subtasks:
    agent_name = assign(subtask)
    result = dispatch(roster()[agent_name], subtask)
    notify(self, "subtask_complete", {agent: agent_name, result: result})
  return merge(collected_results)
```

## Inherited Constraints (from mediator)
- Agents in the roster MUST NOT call each other directly
- `decompose()` and `assign()` are the only places routing logic may live
- The Orchestrator MUST NOT perform agent-level work itself — it coordinates only
- `on_agent_failure()` MUST return an explicit policy; silent swallowing of errors is forbidden
