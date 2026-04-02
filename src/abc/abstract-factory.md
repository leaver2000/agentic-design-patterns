---
name: abstract-factory
abstract: true
pattern: Abstract Factory
category: creational
extends: []
description: Define an interface for creating families of related agents without specifying their concrete implementations.
---

## Intent
Define an interface for creating families of related or dependent agents without specifying their concrete classes.

## Participants
- **AbstractAgentFactory** *(this)* — declares the creation interface for each agent type in the family
- **ConcreteAgentFactory** *(implementor)* — implements the creation operations to produce concrete agents
- **AbstractAgent** — declares the interface that all product agents in a family share
- **ConcreteAgent** — a specific agent produced by the factory; fulfills one role in the family
- **Client** — uses only the AbstractAgentFactory and AbstractAgent interfaces

## Abstract Interface
Implementors MUST define:
- `create_agent(role: str) -> Agent` — instantiate a concrete agent for the given role
- `supported_roles() -> list[str]` — enumerate the roles this factory can produce
- `validate_family_compatibility(agents: list[Agent]) -> bool` — assert agents from the same factory can collaborate

## Constraints
- All agents produced by one factory instance MUST share a compatible communication contract
- The client MUST NOT reference concrete agent classes directly
- Switching the entire agent family MUST be achievable by substituting only the factory

## Agentic AI Context
Use when a system must work with multiple families of agents (e.g., a "research family" of searcher + summarizer + critic vs. a "code family" of planner + implementer + reviewer) and must enforce that agents within a family are always used together. The factory ensures cross-family mixing does not occur at runtime.
