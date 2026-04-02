---
name: adapter
abstract: true
pattern: Adapter
category: structural
extends: []
description: Convert the interface of an external tool or API into the uniform tool interface that agents expect.
---

## Intent
Convert the interface of an external service, API, or legacy tool into the uniform tool interface that agents expect, enabling interoperability without modifying either side.

## Participants
- **Target** — the tool interface the agent expects (e.g., `call(name: str, args: dict) -> str`)
- **Adapter** *(this)* — implements Target by wrapping the Adaptee; translates calls
- **Adaptee** — the existing external service with an incompatible interface
- **Client** *(the agent)* — collaborates with the Adaptee through the Adapter's Target interface

## Abstract Interface
Implementors MUST define:
- `call(name: str, args: dict) -> ToolResult` — the standard agent-facing tool invocation
- `tool_schema() -> dict` — return the JSON schema describing this tool to the agent
- `_translate(args: dict) -> Any` — convert from agent-facing args to the Adaptee's native format
- `_parse_response(raw: Any) -> ToolResult` — convert the Adaptee's response to ToolResult

## Constraints
- The Adapter MUST NOT expose Adaptee internals to the agent
- `tool_schema()` MUST be self-consistent with `call()` — the schema is the agent's only contract
- Error handling from the Adaptee MUST be caught and translated into ToolResult error fields

## Agentic AI Context
Use when integrating third-party APIs, legacy REST services, or SDKs with non-standard calling conventions into an agent tool-use pipeline. The adapter decouples the agent from external interface churn — when the external API changes, only the adapter changes, not the agent or its prompts.
