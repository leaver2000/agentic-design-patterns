---
name: mediator
abstract: true
pattern: Mediator
category: behavioral
extends: []
description: Define an orchestrator object that centralizes how a set of agents interact, keeping agents decoupled from each other.
---

## Intent
Define an object that encapsulates how a set of agents interact. The Mediator promotes loose coupling by keeping agents from referring to each other explicitly, and it lets you vary their interaction independently.

## Participants
- **Mediator** *(this)* — defines an interface for communicating with Agent colleagues
- **ConcreteMediator** *(implementor)* — implements cooperative behavior by coordinating colleagues; knows and maintains all colleagues
- **Colleague** — each agent; knows its Mediator; communicates with other colleagues only through the Mediator
- **ConcreteColleague** *(implementor)* — a specific agent role; notifies the Mediator when relevant events occur

## Abstract Interface
Implementors MUST define on the Mediator:
- `notify(sender: Agent, event: str, payload: dict)` — called by colleagues when something happens; triggers coordination logic
- `route(task: Task) -> Agent` — decide which colleague handles the next step
- `broadcast(event: str, payload: dict)` — send an event to all relevant colleagues

Implementors MUST define on each Colleague:
- `set_mediator(mediator: Mediator)` — inject the mediator reference
- `send(event: str, payload: dict)` — notify the mediator of an event

## Constraints
- Colleagues MUST communicate exclusively through the Mediator — no direct agent-to-agent calls
- The Mediator MUST NOT perform agent-level work itself — it coordinates, not executes
- Adding a new interaction pattern MUST require changing only the Mediator, not the colleagues

## Agentic AI Context
Use in multi-agent systems where agents would otherwise form a tightly coupled web of direct references. A `WorkflowOrchestrator` mediates between a PlannerAgent, ResearchAgent, WriterAgent, and ReviewerAgent — when Research finishes, the Orchestrator decides whether to call Writer or loop back to Planner. Agents don't know about each other.
