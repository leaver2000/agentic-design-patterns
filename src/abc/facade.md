---
name: facade
abstract: true
pattern: Facade
category: structural
extends: []
description: Provide a unified interface to a complex multi-agent subsystem, hiding its internal coordination from callers.
---

## Intent
Provide a simplified, unified interface to a complex multi-agent subsystem. The Facade defines a higher-level interface that makes the subsystem easier to use without exposing its internal agent topology.

## Participants
- **Facade** *(this)* — knows which agents to call, in what order, and how to aggregate their results; presents one simple method to the client
- **Subsystem Agents** — the individual agents doing the work; have no knowledge of the Facade
- **Client** — communicates only with the Facade

## Abstract Interface
Implementors MUST define:
- `execute(request: Request) -> Response` — the single entry point; coordinates all internal agents
- `subsystem_agents() -> list[Agent]` — return the agents this facade orchestrates
- `health_check() -> dict` — report the readiness of each internal agent

## Constraints
- The Facade MUST expose no more than the minimum interface clients need
- Subsystem agents MUST remain independently operable — the Facade MUST NOT make them Facade-dependent
- The Facade MUST handle all internal sequencing, retries, and result aggregation — the client does none of this

## Agentic AI Context
Use when exposing a complex pipeline (e.g., search → retrieve → synthesize → cite → format) as a single `answer(question)` call. The Facade is the public API of a multi-agent feature; callers see one function, not ten. This is the standard pattern for wrapping an entire agent system behind a product interface.
