---
name: bridge
abstract: true
pattern: Bridge
category: structural
extends: []
description: Decouple an agent's task logic from the model implementation so that both can vary independently.
---

## Intent
Decouple an agent's task logic (the abstraction) from the model implementation (the implementor) so that both can vary independently.

## Participants
- **Abstraction** *(this)* — defines the agent's high-level interface; holds a reference to an Implementor
- **RefinedAbstraction** *(implementor)* — extends the Abstraction with task-specific behavior
- **Implementor** — defines the model-layer interface (`complete`, `stream`, `embed`)
- **ConcreteImplementor** *(implementor)* — a specific model backend (Claude, GPT-4, Gemini, local Ollama)

## Abstract Interface
Implementors MUST define on the Implementor side:
- `complete(messages: list[Message], **kwargs) -> str` — synchronous completion
- `stream(messages: list[Message], **kwargs) -> AsyncIterator[str]` — streaming completion
- `model_id() -> str` — return the canonical model identifier

Implementors MUST define on the Abstraction side:
- `run(task: str, context: dict) -> AgentResult` — execute the agent's task using `self.implementor`

## Constraints
- The Abstraction MUST reference the Implementor only through the Implementor interface — no isinstance checks
- Swapping the Implementor MUST NOT require changes to the Abstraction or any RefinedAbstraction
- Prompt construction belongs in the Abstraction; token limits and retry logic belong in the Implementor

## Agentic AI Context
Use when you want the same agent logic (e.g., a ReAct loop, a planner) to run on different models without forking agent code. The Bridge lets you test an agent against a cheap fast model in CI and deploy it against a more capable model in production, or A/B test models without touching agent behavior.
