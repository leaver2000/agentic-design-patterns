---
name: prototype
abstract: true
pattern: Prototype
category: creational
extends: []
description: Specify the agents to create by using a prototypical configured instance, and create new agents by cloning that prototype.
---

## Intent
Specify the agents to create using a prototypical configured instance, and create new agents by cloning that prototype.

## Participants
- **PrototypeRegistry** *(this)* — maintains a registry of prototypical agent instances keyed by role name
- **Prototype** — declares an interface for cloning itself
- **ConcretePrototype** *(implementor)* — implements the clone operation; copies its full configuration (system prompt, tools, memory, model)
- **Client** — creates new agents by asking the registry for a clone of a named prototype

## Abstract Interface
Implementors MUST define:
- `clone() -> Agent` — return a deep copy of the agent instance with all configuration intact
- `configure(**overrides)` — apply selective overrides to a cloned instance before use
- `prototype_id() -> str` — return a stable identifier for this prototype

## Constraints
- `clone()` MUST produce a fully independent instance — mutations to the clone MUST NOT affect the prototype
- The registry MUST store prototypes, not constructors; the prototype MUST be a live configured object
- `configure()` MUST be called after `clone()`, never on the prototype directly

## Agentic AI Context
Use when agent configuration is expensive (large system prompts, preloaded tool manifests, warm memory stores) and many similar agents are needed at runtime. Define one "gold master" agent per role, register it, then clone-and-customize for each task. Avoids repeating initialization cost and allows variant agents (e.g., a "verbose researcher" vs. "terse researcher") with minimal config delta.
