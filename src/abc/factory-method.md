---
name: factory-method
abstract: true
pattern: Factory Method
category: creational
extends: []
description: Define an interface for spawning an agent, but let subclasses decide which agent class to instantiate.
---

## Intent
Define an interface for spawning an agent, but let the subclass or configuration decide which concrete agent class to instantiate. Defers agent instantiation to subclasses.

## Participants
- **Creator** *(this)* — declares the `spawn()` factory method; may provide default behavior that calls `spawn()`
- **ConcreteCreator** *(implementor)* — overrides `spawn()` to return an instance of a specific agent class
- **Agent** — defines the interface for agents the factory method creates
- **ConcreteAgent** *(implementor)* — implements the Agent interface; created by the matching ConcreteCreator

## Abstract Interface
Implementors MUST define:
- `spawn(context: dict) -> Agent` — create and return the appropriate agent for the given context
- `agent_type() -> str` — return a stable identifier for the agent class this creator produces

## Constraints
- `spawn()` MUST return an object satisfying the Agent interface — callers rely only on that interface
- ConcreteCreators MUST be substitutable for one another at the call site (Liskov)
- The Creator MUST NOT hard-code the agent class name; all decisions belong in `spawn()`

## Agentic AI Context
Use when a framework needs to produce different agent types based on runtime context (task type, user tier, environment) but the orchestration logic should remain model-agnostic. A `ResearchCreator` spawns a `ResearchAgent`; a `CodingCreator` spawns a `CodingAgent` — the pipeline that calls `spawn()` never changes.
