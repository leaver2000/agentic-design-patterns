---
name: observer
abstract: true
pattern: Observer
category: behavioral
extends: []
description: Define a one-to-many dependency between agents so that when one agent emits an event, all subscribed agents are notified automatically.
---

## Intent
Define a one-to-many dependency between agents so that when one agent changes state or emits an event, all its dependents are notified and can respond automatically.

## Participants
- **Subject** — maintains a list of Observers; notifies them of state changes or events
- **Observer** *(this)* — defines an update interface for objects that should be notified
- **ConcreteSubject** *(implementor)* — an agent that emits events (tool call made, token generated, task complete, error raised)
- **ConcreteObserver** *(implementor)* — a subscriber that reacts to Subject events (logger, monitor, downstream agent)

## Abstract Interface
Implementors MUST define on the Observer:
- `on_event(event: AgentEvent) -> None` — respond to a published event
- `subscribes_to() -> list[str]` — declare which event types this observer handles

Implementors MUST define on the Subject:
- `subscribe(observer: Observer)` — register an observer
- `unsubscribe(observer: Observer)` — deregister an observer
- `emit(event: AgentEvent)` — notify all subscribed observers of an event

## Constraints
- The Subject MUST NOT know the concrete type of its Observers
- Observers MUST NOT emit events that cause cycles — the event graph must be acyclic
- `on_event()` MUST NOT raise — exceptions must be caught and handled internally
- Observers MUST be notified in subscription order or in a documented order

## Agentic AI Context
Use for agent observability, event-driven pipelines, and reactive multi-agent coordination. A `ToolCallEvent` can be observed by a Logger, a CostTracker, and a GuardrailAgent simultaneously. An `AgentCompletionEvent` can trigger downstream agents. This is the foundation of event-driven agent architectures and streaming progress updates.
