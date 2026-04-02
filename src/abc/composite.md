---
name: composite
abstract: true
pattern: Composite
category: structural
extends: []
description: Compose agents into tree structures so that orchestrators and leaf agents are treated uniformly.
---

## Intent
Compose agents into tree structures to represent orchestrator-subagent hierarchies. Composite lets clients treat individual leaf agents and multi-agent orchestrators uniformly.

## Participants
- **Component** *(this)* — declares the uniform interface for both leaf agents and orchestrators
- **Leaf** *(implementor)* — a single agent with no children; performs actual work
- **Composite** *(implementor)* — an orchestrator that holds child Components and delegates work to them
- **Client** — manipulates agents through the Component interface only

## Abstract Interface
Implementors MUST define:
- `run(task: str, context: dict) -> AgentResult` — execute this component's portion of work
- `add_child(agent: Component)` — add a sub-agent *(Composite only; raises on Leaf)*
- `remove_child(agent: Component)` — remove a sub-agent *(Composite only; raises on Leaf)*
- `children() -> list[Component]` — return immediate children *(empty list for Leaf)*
- `describe() -> dict` — return a serializable description of this node and its subtree

## Constraints
- The Component interface MUST be identical for Leaf and Composite — callers MUST NOT need to distinguish them
- A Composite MUST aggregate results from children into a single AgentResult
- Circular parent-child relationships are forbidden; the tree MUST be a DAG

## Agentic AI Context
Use when building hierarchical agent systems: a top-level PlannerAgent decomposes a task and delegates to ResearchAgent, WriterAgent, CriticAgent — each of which may itself be a Composite that further decomposes. The Composite pattern lets you add or rearrange agents in the hierarchy without changing how the root is invoked.
