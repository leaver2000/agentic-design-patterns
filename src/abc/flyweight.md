---
name: flyweight
abstract: true
pattern: Flyweight
category: structural
extends: []
description: Use shared immutable context — system prompts, tool schemas, embeddings — to support large numbers of agent instances efficiently.
---

## Intent
Use sharing to support large numbers of agent instances efficiently. Separate the intrinsic shared state (system prompts, tool schemas, model config, embeddings) from extrinsic per-invocation state (conversation history, task context).

## Participants
- **Flyweight** *(this)* — declares an interface through which flyweights can receive and act on extrinsic state
- **ConcreteFlyweight** *(implementor)* — implements the Flyweight interface; stores intrinsic state; must be shareable
- **FlyweightFactory** — creates and manages flyweight objects; ensures sharing
- **Client** — maintains extrinsic state; passes it to flyweights when invoking operations

## Abstract Interface
Implementors MUST define:
- `intrinsic_state() -> dict` — return the shared immutable configuration (system prompt, tools, model)
- `run(task: str, extrinsic: dict) -> AgentResult` — execute using intrinsic + extrinsic state combined; MUST NOT store extrinsic state
- `flyweight_key() -> str` — a cache key that uniquely identifies this intrinsic configuration

## Constraints
- Intrinsic state MUST be immutable after construction
- Extrinsic state MUST be passed in at call time, never stored on the flyweight
- The FlyweightFactory MUST return the same instance for identical `flyweight_key()` values
- Flyweights MUST be safe for concurrent use by multiple callers

## Agentic AI Context
Use when running thousands of similar agent invocations that share the same system prompt and tool set (e.g., a document-processing pipeline). Cache the shared configuration object and inject per-document context at call time. This pattern is also the basis for prompt caching — the intrinsic state maps directly to the cached prefix.
