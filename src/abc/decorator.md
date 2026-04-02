---
name: decorator
abstract: true
pattern: Decorator
category: structural
extends: []
description: Attach additional capabilities to an agent dynamically — memory, logging, rate-limiting, guardrails — without subclassing.
---

## Intent
Attach additional capabilities to an agent dynamically. Decorators provide a flexible alternative to subclassing for extending agent functionality.

## Participants
- **Component** — defines the agent interface that can have capabilities added
- **ConcreteComponent** — the base agent being decorated
- **Decorator** *(this)* — maintains a reference to a Component and conforms to the Component interface
- **ConcreteDecorator** *(implementor)* — adds a specific capability (e.g., MemoryDecorator, LoggingDecorator, RateLimitDecorator, GuardrailDecorator)

## Abstract Interface
Implementors MUST define:
- `run(task: str, context: dict) -> AgentResult` — delegate to the wrapped component, adding behavior before and/or after
- `wrapped() -> Component` — return the inner component
- `capability_name() -> str` — return a stable identifier for what this decorator adds

## Constraints
- The Decorator MUST implement the Component interface exactly — it is a drop-in replacement
- Decoration MUST be stackable — a Decorator wrapping another Decorator MUST work correctly
- The Decorator MUST NOT modify the wrapped component's state directly
- Side effects (logging, metrics) MUST NOT alter the AgentResult unless the decorator's explicit purpose is transformation

## Agentic AI Context
Use to layer cross-cutting concerns onto agents without polluting their core logic: wrap any agent with `MemoryDecorator` to add persistent context, `LoggingDecorator` for observability, `RetryDecorator` for resilience, or `GuardrailDecorator` for output safety. Decorators compose cleanly: `GuardrailDecorator(RetryDecorator(MemoryDecorator(base_agent)))`.
