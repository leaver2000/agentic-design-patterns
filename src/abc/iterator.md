---
name: iterator
abstract: true
pattern: Iterator
category: behavioral
extends: []
description: Provide a way to access agent outputs or a collection of results sequentially without exposing the underlying generation mechanism.
---

## Intent
Provide a way to access the elements of an aggregate agent output sequentially — streaming tokens, a list of sub-results, or paginated results — without exposing the underlying representation.

## Participants
- **Iterator** *(this)* — defines the interface for accessing and traversing elements
- **ConcreteIterator** *(implementor)* — implements the Iterator; tracks current position in traversal
- **Aggregate** — defines an interface for creating an Iterator
- **ConcreteAggregate** *(implementor)* — implements the Aggregate; returns an instance of ConcreteIterator

## Variants
- **Streaming Iterator** — yields tokens or chunks as they arrive from the model
- **Result Iterator** — iterates over a finite list of AgentResults
- **Pagination Iterator** — fetches the next page of results on demand

## Abstract Interface
Implementors MUST define:
- `__anext__() -> T` — return the next element; raise StopAsyncIteration when exhausted
- `__aiter__() -> Self` — return self
- `peek() -> T | None` — return the next element without advancing *(optional)*
- `reset()` — restart the iteration from the beginning *(where semantically valid)*

## Constraints
- The Iterator MUST NOT require the full collection to exist in memory before iteration begins
- Concurrent use of the same Iterator instance by multiple callers is undefined behavior — document clearly
- `reset()` on a streaming iterator that cannot replay MUST raise NotImplementedError

## Agentic AI Context
Use for streaming agent responses token-by-token to a UI, iterating over a batch of agent results for aggregation, or paginating through a long tool-call sequence. The Iterator decouples the consumer (display, aggregator) from the producer (stream, batch runner) — the consumer does not need to know if results are streaming or buffered.
