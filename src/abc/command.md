---
name: command
abstract: true
pattern: Command
category: behavioral
extends: []
description: Encapsulate an agent invocation as a serializable, queueable, undoable object.
---

## Intent
Encapsulate an agent invocation as a standalone object, thereby allowing you to queue, log, serialize, retry, and undo agent operations.

## Participants
- **Command** *(this)* — declares the interface for executing an operation
- **ConcreteCommand** *(implementor)* — binds an agent invocation with its arguments; implements `execute()` by calling the bound agent
- **Invoker** — asks the command to carry out a request; may queue or log commands
- **Receiver** *(the agent)* — the agent that performs the actual work when `execute()` is called
- **Client** — creates ConcreteCommands and sets their Receiver

## Abstract Interface
Implementors MUST define:
- `execute() -> AgentResult` — dispatch the encapsulated agent invocation
- `undo()` — reverse the effect of `execute()` if the operation is reversible
- `serialize() -> dict` — produce a JSON-serializable representation of this command
- `task_id() -> str` — return a stable identifier for deduplication and idempotency

## Constraints
- A Command object MUST be self-contained — it carries all information needed to execute the invocation
- `serialize()` output MUST be sufficient to reconstruct and re-execute the command
- `undo()` MUST be a no-op (not raise) if the command was never executed or is not reversible
- The Invoker MUST NOT know the Receiver's type — it only calls `execute()`

## Agentic AI Context
Use for building agent task queues, audit logs, and retry systems. A Command represents one unit of agent work: create it, enqueue it, execute it later, log it, retry it on failure, or replay it from a log. `undo()` enables rollback for agents that produce reversible side effects (file writes, API calls).
