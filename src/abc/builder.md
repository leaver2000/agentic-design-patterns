---
name: builder
abstract: true
pattern: Builder
category: creational
extends: []
description: Separate the construction of a complex agent pipeline from its representation so the same process can produce different pipeline configurations.
---

## Intent
Separate the construction of a complex agent pipeline from its representation so the same construction process can create different pipeline configurations.

## Participants
- **Director** *(this)* — constructs the pipeline by invoking builder steps in a defined sequence
- **AbstractBuilder** *(implementor)* — specifies the abstract interface for each construction step
- **ConcreteBuilder** *(implementor)* — implements the steps; tracks the pipeline being assembled
- **Pipeline** — the complex agent workflow being constructed step by step

## Abstract Interface
Implementors MUST define:
- `set_system_prompt(prompt: str)` — configure the agent's base instructions
- `add_tool(tool: Tool)` — attach a tool to the agent under construction
- `add_memory(memory: Memory)` — attach a memory backend
- `set_model(model: str)` — select the underlying LLM
- `build() -> Agent` — return the fully constructed agent

## Constraints
- `build()` MUST NOT be callable before the minimum required steps are complete
- Each build step MUST be independent — calling one step MUST NOT implicitly trigger another
- The Director MUST NOT know the concrete type of the Pipeline being produced

## Agentic AI Context
Use when agent pipelines require many optional components (tools, memories, guardrails, model choices) and the construction logic would otherwise scatter throughout the codebase. The Director holds the recipe; the Builder holds the materials. Swap builders to produce a "lightweight" vs. "full-featured" variant of the same pipeline shape.
