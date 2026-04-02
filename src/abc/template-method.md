---
name: template-method
abstract: true
pattern: Template Method
category: behavioral
extends: []
description: Define the skeleton of an agent workflow in a base agent, deferring specific steps to subagents.
---

## Intent
Define the skeleton of an agent workflow in a base operation, deferring some steps to sub-agents or subclasses. Template Method lets subclasses redefine certain steps without changing the workflow's overall structure.

## Participants
- **AbstractAgent** *(this)* — defines the `run()` template method and all abstract step methods; implements common steps
- **ConcreteAgent** *(implementor)* — implements the abstract step methods; MUST NOT override `run()` itself

## Abstract Interface
Implementors MUST define in the AbstractAgent:
- `run(task: str, context: dict) -> AgentResult` — the template method; calls steps in fixed order; MUST be `final` (not overridable)
- `abstract plan(task: str) -> Plan` — step 1: decompose the task *(must be overridden)*
- `abstract execute(plan: Plan) -> list[StepResult]` — step 2: carry out the plan *(must be overridden)*
- `abstract review(results: list[StepResult]) -> AgentResult` — step 3: synthesize results *(must be overridden)*
- `hook_before_execute(plan: Plan)` — optional hook; default is no-op *(may be overridden)*
- `hook_after_review(result: AgentResult)` — optional hook; default is no-op *(may be overridden)*

## Constraints
- `run()` MUST be declared final (not overridable by ConcreteAgents)
- Abstract steps MUST be overridden by ConcreteAgents; optional hooks MUST NOT be required
- The step sequence defined in `run()` is invariant — ConcreteAgents cannot reorder steps
- ConcreteAgents MUST call `super()` for any hook they override

## Agentic AI Context
Use when all agents in a family follow the same high-level workflow (plan → execute → review) but differ in how each step is carried out. A `ResearchAgent` and `CodeAgent` both inherit from `WorkflowAgent` and share the orchestration skeleton; each provides its own `plan()`, `execute()`, and `review()` implementations. The workflow is guaranteed consistent; the behavior is customizable.
