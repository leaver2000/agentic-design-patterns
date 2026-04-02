---
name: visitor
abstract: true
pattern: Visitor
category: behavioral
extends: []
description: Represent an operation to be performed on agent outputs or pipeline nodes without changing the agents themselves.
---

## Intent
Represent an operation to be performed on the elements of an agent pipeline or output structure. Visitor lets you define new operations (evaluation, transformation, logging) without changing the classes of the agents or outputs on which it operates.

## Participants
- **Visitor** *(this)* — declares a `visit()` operation for each type of element in the agent structure
- **ConcreteVisitor** *(implementor)* — implements each `visit()` operation; accumulates state across visits
- **Element** — defines an `accept()` operation that takes a Visitor
- **ConcreteElement** *(implementor)* — a specific output type or pipeline node; implements `accept()` by calling the matching `visit_X()` on the visitor
- **ObjectStructure** — the pipeline or output tree being traversed

## Common Visitors
- **EvaluatorVisitor** — scores each element for quality, relevance, or correctness
- **TransformVisitor** — rewrites or enriches each element
- **LoggingVisitor** — records metadata for each element
- **CostVisitor** — tallies token usage across all elements

## Abstract Interface
Implementors MUST define on each Visitor:
- `visit_agent_result(result: AgentResult)` — handle an AgentResult node
- `visit_tool_call(call: ToolCall)` — handle a ToolCall node
- `visit_message(msg: Message)` — handle a Message node
- `summary() -> Any` — return the accumulated result of the traversal

Implementors MUST define on each Element:
- `accept(visitor: Visitor)` — call `visitor.visit_self(self)` with the correct type dispatch

## Constraints
- `accept()` MUST dispatch to the exact matching `visit_X()` method — generic fallback is a last resort
- Visitors MUST NOT modify the structure they traverse — they observe and accumulate
- Adding a new Element type requires adding a new `visit_X()` to all Visitors — plan the type set carefully

## Agentic AI Context
Use for post-hoc analysis of agent outputs without touching the agents themselves: run an `EvaluatorVisitor` over a completed pipeline to score quality, a `CostVisitor` to tally spend, and a `CitationVisitor` to extract all referenced sources — all in one pass. The agents emit a structured output tree; visitors operate on it separately.
