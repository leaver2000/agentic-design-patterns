---
name: singleton
abstract: true
pattern: Singleton
category: creational
extends: []
description: Ensure a shared agent service has only one instance and provide a global access point to it.
---

## Intent
Ensure a shared agent service — such as a memory store, tool registry, or model router — has only one instance, and provide a global access point to it.

## Participants
- **Singleton** *(this)* — defines the `instance()` class method; responsible for creating and caching its own sole instance
- **Client** — accesses the singleton only through `instance()`; never constructs it directly

## Abstract Interface
Implementors MUST define:
- `instance() -> Self` *(class method)* — return the single shared instance, creating it on first call
- `reset()` *(class method, optional)* — clear the instance for testing purposes only

## Constraints
- Construction MUST be private or guarded — direct instantiation by clients is forbidden
- `instance()` MUST be safe under concurrent access (thread-safe / async-safe)
- The singleton MUST NOT carry mutable task-specific state — only shared infrastructure state

## Agentic AI Context
Use for infrastructure shared across all agents in a session: a tool registry, a rate-limit tracker, a shared embedding cache, or a session-scoped memory store. Do not use for agents themselves — agent instances are task-scoped and should not be singletons. The key constraint is that the singleton holds *configuration and infrastructure*, not conversation state.
