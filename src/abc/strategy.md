---
name: strategy
abstract: true
pattern: Strategy
category: behavioral
extends: []
description: Define a family of model backends or reasoning approaches, encapsulate each one, and make them interchangeable at runtime.
---

## Intent
Define a family of algorithms or model backends, encapsulate each one, and make them interchangeable. Strategy lets the model or reasoning approach vary independently from the agents that use it.

## Participants
- **Context** *(the agent)* — is configured with a ConcreteStrategy; may define an interface for data the strategy needs
- **Strategy** *(this)* — declares the interface common to all supported backends or approaches
- **ConcreteStrategy** *(implementor)* — implements the algorithm or model backend using the Strategy interface

## Variants
- **Model Strategy** — swappable LLM backends (Claude Haiku, Sonnet, Opus; GPT-4; local Ollama)
- **Reasoning Strategy** — swappable reasoning approaches (ReAct, Chain-of-Thought, Tree-of-Thought, direct)
- **Retrieval Strategy** — swappable retrieval backends (vector search, BM25, hybrid)
- **Sampling Strategy** — swappable generation parameters (greedy, temperature-based, beam search)

## Abstract Interface
Implementors MUST define:
- `execute(input: StrategyInput) -> StrategyOutput` — run the strategy on the given input
- `strategy_id() -> str` — a stable identifier for this strategy
- `cost_estimate(input: StrategyInput) -> float` — estimated cost in tokens or dollars *(optional but recommended)*
- `supports(input: StrategyInput) -> bool` — return True if this strategy can handle the given input

## Constraints
- All ConcreteStrategies MUST be substitutable for one another at the Context interface
- The Context MUST NOT contain logic that branches on strategy type
- Strategies MUST NOT share mutable state between invocations
- Strategy selection logic belongs in a factory or selector, not in the Context

## Agentic AI Context
Use to swap models at runtime based on task complexity, cost budget, or latency requirements. A `StrategySelector` picks `HaikuStrategy` for simple classification, `SonnetStrategy` for reasoning, `OpusStrategy` for complex synthesis. The agent (Context) is unchanged — it calls `strategy.execute()` regardless of which backend is active.
