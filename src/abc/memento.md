---
name: memento
abstract: true
pattern: Memento
category: behavioral
extends: []
description: Capture and externalize an agent's internal state so it can be restored later without violating encapsulation.
---

## Intent
Without violating encapsulation, capture and externalize an agent's internal state — conversation history, working memory, tool state — so the agent can be restored to that state later.

## Participants
- **Originator** *(the agent)* — creates a Memento containing a snapshot of its current state; uses the Memento to restore its state
- **Memento** *(this)* — stores the internal state of the Originator; protects against access by objects other than the Originator
- **Caretaker** — is responsible for the Memento's safekeeping; never operates on or examines the Memento's contents

## Abstract Interface
Implementors MUST define on the Memento:
- `serialize() -> bytes | str` — produce a durable, portable representation of the captured state
- `restore(agent: Agent)` — apply the captured state back to the agent
- `snapshot_id() -> str` — a stable identifier for this snapshot
- `created_at() -> datetime` — timestamp of when the snapshot was taken

Implementors MUST define on the Originator (agent):
- `save() -> Memento` — capture the current state and return it as a Memento
- `load(memento: Memento)` — restore state from the given Memento

## Constraints
- The Memento MUST capture a complete, self-consistent state — partial snapshots are forbidden
- Only the Originator MUST be able to write to or read the Memento's internal data
- The Caretaker MUST treat the Memento as opaque — no inspection or modification
- `restore()` MUST be idempotent for the same Memento

## Agentic AI Context
Use for agent checkpointing, conversation resume, and rollback. Save a Memento before a risky multi-step operation; restore it if the operation fails. Also enables multi-session agents — serialize the Memento to a database, load it next session. The Caretaker is typically a persistence layer (Redis, Postgres, S3).
