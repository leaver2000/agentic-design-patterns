---
name: state
abstract: true
pattern: State
category: behavioral
extends: []
description: Allow an agent to alter its behavior when its internal phase changes — planning, executing, reviewing, waiting — as if it changed its class.
---

## Intent
Allow an agent to alter its behavior when its internal state changes. The agent will appear to change its class as it transitions through phases (planning → executing → reviewing → done).

## Participants
- **Context** *(the agent)* — maintains an instance of a ConcreteState that defines current behavior; delegates phase-specific behavior to it
- **State** *(this)* — defines an interface for encapsulating behavior associated with a particular phase
- **ConcreteState** *(implementor)* — implements behavior for a specific phase; may trigger transitions to other states

## Common States
- **PlanningState** — decomposes task into subtasks; transitions to ExecutingState
- **ExecutingState** — invokes tools or sub-agents; transitions to ReviewingState or ErrorState
- **ReviewingState** — evaluates results; transitions to Done or back to PlanningState
- **WaitingState** — awaiting human input or an async event
- **ErrorState** — handles failures; may retry or escalate

## Abstract Interface
Implementors MUST define on each State:
- `on_enter(context: Agent)` — called when the agent transitions into this state
- `handle(context: Agent, input: Any) -> Any` — perform the state's primary action
- `on_exit(context: Agent)` — called when the agent transitions out of this state
- `state_name() -> str` — return a stable identifier

Implementors MUST define on the Context:
- `transition_to(state: State)` — change the current state

## Constraints
- State transitions MUST be explicit — no implicit transitions
- A State MUST NOT directly replace another ConcreteState class — it transitions via `context.transition_to()`
- The Context MUST NOT have conditional logic that checks state type — all branching lives in State subclasses

## Agentic AI Context
Use for agents with non-trivial lifecycles: a ReAct agent in PlanningState thinks and picks a tool; in ExecutingState it calls the tool; in ReviewingState it decides whether to loop or finish. The State pattern replaces a nest of `if/elif phase == ...` checks with a clean set of state objects, making new phases easy to add.
