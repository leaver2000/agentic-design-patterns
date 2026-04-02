---
name: chain-of-responsibility
abstract: true
pattern: Chain of Responsibility
category: behavioral
extends: []
description: Pass a task along a chain of agents until one handles it, decoupling the sender from the handler.
---

## Intent
Avoid coupling the sender of a request to its receiver by giving more than one agent a chance to handle the request. Chain the agents and pass the request along the chain until one handles it.

## Participants
- **Handler** *(this)* — defines the interface for handling requests; optionally holds a reference to the next handler
- **ConcreteHandler** *(implementor)* — handles requests it is responsible for; otherwise forwards to the next handler
- **Client** — initiates the request to the first handler in the chain

## Abstract Interface
Implementors MUST define:
- `handle(task: Task) -> AgentResult | None` — attempt to handle the task; return a result if handled, None to pass along
- `set_next(handler: Handler) -> Handler` — set the successor handler; return it to allow fluent chaining
- `can_handle(task: Task) -> bool` — determine if this handler is capable of handling the task

## Constraints
- A handler that cannot handle a task MUST forward it to the successor — returning an error is a handle
- The chain MUST have a terminal handler that catches unhandled tasks (or the caller must handle None)
- Handlers MUST NOT know the full chain structure — only their immediate successor
- The chain SHOULD be reconfigurable at runtime without modifying handler classes

## Agentic AI Context
Use for routing tasks to specialized agents based on capability: a task first reaches a `FastAgent` (cheap, handles simple queries), then a `DeepAgent` (expensive, handles complex ones), then a `FallbackAgent`. Also useful for content moderation pipelines where each agent in the chain applies a different filter and can either pass or stop the request.
