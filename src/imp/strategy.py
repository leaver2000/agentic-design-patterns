"""
Strategy — Model Strategy
abc: src/abc/strategy.md

Defines a family of model backends or reasoning approaches, encapsulates
each one, and makes them interchangeable at runtime.
A StrategySelector picks the right strategy based on task characteristics.
"""

from __future__ import annotations

import abc
import time
from dataclasses import dataclass
from typing import Any

import anthropic


# ---------------------------------------------------------------------------
# Strategy I/O types
# ---------------------------------------------------------------------------

@dataclass
class StrategyInput:
    task: str
    context: dict | None = None
    max_tokens: int = 400


@dataclass
class StrategyOutput:
    content: str
    strategy_id: str
    latency_s: float
    input_tokens: int
    output_tokens: int


# ---------------------------------------------------------------------------
# Strategy interface
# ---------------------------------------------------------------------------

class ModelStrategy(abc.ABC):
    """Strategy: declares the common interface for all model backends."""

    @abc.abstractmethod
    def execute(self, input: StrategyInput) -> StrategyOutput:
        """Run the strategy on the given input."""
        ...

    @abc.abstractmethod
    def strategy_id(self) -> str:
        """Stable identifier for this strategy."""
        ...

    @abc.abstractmethod
    def supports(self, input: StrategyInput) -> bool:
        """Return True if this strategy can handle the given input."""
        ...

    @abc.abstractmethod
    def cost_estimate(self, input: StrategyInput) -> float:
        """Estimated cost in USD for this input (rough approximation)."""
        ...


# ---------------------------------------------------------------------------
# Concrete Strategies — Claude model tiers
# ---------------------------------------------------------------------------

class _ClaudeStrategy(ModelStrategy):
    """Base for Claude-backed strategies."""

    def __init__(self, model: str, system: str = "") -> None:
        self._model = model
        self._system = system
        self._client = anthropic.Anthropic()

    def execute(self, input: StrategyInput) -> StrategyOutput:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": input.max_tokens,
            "messages": [{"role": "user", "content": input.task}],
        }
        if self._system:
            kwargs["system"] = self._system

        start = time.perf_counter()
        msg = self._client.messages.create(**kwargs)
        latency = time.perf_counter() - start

        return StrategyOutput(
            content=msg.content[0].text,
            strategy_id=self.strategy_id(),
            latency_s=round(latency, 3),
            input_tokens=msg.usage.input_tokens,
            output_tokens=msg.usage.output_tokens,
        )


class HaikuStrategy(_ClaudeStrategy):
    """Fast, cheap strategy for simple classification and lookup tasks."""

    INPUT_PRICE = 0.25 / 1_000_000
    OUTPUT_PRICE = 1.25 / 1_000_000
    MAX_TASK_CHARS = 2000

    def __init__(self) -> None:
        super().__init__(
            model="claude-haiku-4-5-20251001",
            system="You are a fast-response assistant. Be concise and direct.",
        )

    def strategy_id(self) -> str:
        return "haiku"

    def supports(self, input: StrategyInput) -> bool:
        return len(input.task) <= self.MAX_TASK_CHARS

    def cost_estimate(self, input: StrategyInput) -> float:
        estimated_input_tokens = len(input.task) // 4
        estimated_output_tokens = input.max_tokens // 2
        return (
            estimated_input_tokens * self.INPUT_PRICE
            + estimated_output_tokens * self.OUTPUT_PRICE
        )


class SonnetStrategy(_ClaudeStrategy):
    """Balanced strategy for reasoning and analysis tasks."""

    INPUT_PRICE = 3.0 / 1_000_000
    OUTPUT_PRICE = 15.0 / 1_000_000

    def __init__(self) -> None:
        super().__init__(
            model="claude-sonnet-4-6",
            system="You are a thoughtful assistant. Reason carefully before answering.",
        )

    def strategy_id(self) -> str:
        return "sonnet"

    def supports(self, input: StrategyInput) -> bool:
        return True  # Sonnet handles anything

    def cost_estimate(self, input: StrategyInput) -> float:
        estimated_input_tokens = len(input.task) // 4
        estimated_output_tokens = input.max_tokens // 2
        return (
            estimated_input_tokens * self.INPUT_PRICE
            + estimated_output_tokens * self.OUTPUT_PRICE
        )


class EchoStrategy(ModelStrategy):
    """
    Deterministic strategy for testing — no API call, no cost.
    Echoes the task with a fixed prefix.
    """

    def strategy_id(self) -> str:
        return "echo"

    def supports(self, input: StrategyInput) -> bool:
        return True

    def cost_estimate(self, input: StrategyInput) -> float:
        return 0.0

    def execute(self, input: StrategyInput) -> StrategyOutput:
        return StrategyOutput(
            content=f"[ECHO] {input.task[:200]}",
            strategy_id="echo",
            latency_s=0.0,
            input_tokens=0,
            output_tokens=0,
        )


# ---------------------------------------------------------------------------
# Context — the agent; delegates entirely to the strategy
# ---------------------------------------------------------------------------

class StrategyAgent:
    """
    Context: configured with a ConcreteStrategy.
    Never contains logic that branches on strategy type.
    """

    def __init__(self, strategy: ModelStrategy) -> None:
        self._strategy = strategy

    def set_strategy(self, strategy: ModelStrategy) -> None:
        self._strategy = strategy

    def run(self, task: str, max_tokens: int = 400) -> StrategyOutput:
        input = StrategyInput(task=task, max_tokens=max_tokens)
        return self._strategy.execute(input)


# ---------------------------------------------------------------------------
# Strategy Selector — picks the right strategy based on task characteristics
# ---------------------------------------------------------------------------

class StrategySelector:
    """
    Selects a strategy based on cost budget and task complexity.
    Strategy selection logic lives here, NOT in the Context.
    """

    def __init__(self, strategies: list[ModelStrategy], budget_usd: float = 0.01) -> None:
        self._strategies = strategies
        self._budget = budget_usd

    def select(self, input: StrategyInput) -> ModelStrategy:
        """Pick the cheapest capable strategy within budget."""
        candidates = [s for s in self._strategies if s.supports(input)]
        affordable = [s for s in candidates if s.cost_estimate(input) <= self._budget]

        if not affordable:
            # Pick the cheapest even if over budget
            return min(candidates, key=lambda s: s.cost_estimate(input))

        # Among affordable candidates, pick cheapest
        return min(affordable, key=lambda s: s.cost_estimate(input))


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo() -> None:
    print("=== Strategy Demo ===\n")

    haiku = HaikuStrategy()
    sonnet = SonnetStrategy()

    selector = StrategySelector([haiku, sonnet], budget_usd=0.001)
    agent = StrategyAgent(haiku)  # Default

    tasks = [
        "Classify this text: 'neural networks learn representations'.",
        "Explain the attention mechanism in transformers in detail, including the math.",
    ]

    for task in tasks:
        inp = StrategyInput(task=task)
        selected = selector.select(inp)
        agent.set_strategy(selected)

        print(f"Task: {task[:60]}")
        print(f"  Selected strategy: {selected.strategy_id()}")
        print(f"  Estimated cost: ${selected.cost_estimate(inp):.6f}")

        output = agent.run(task)
        print(f"  Result: {output.content[:100]}...")
        print(f"  Actual latency: {output.latency_s}s")
        print(f"  Tokens: {output.input_tokens} in / {output.output_tokens} out\n")

    # Swap to echo strategy — same agent, no code change
    agent.set_strategy(EchoStrategy())
    output = agent.run("Test the echo strategy.")
    print(f"Echo strategy: {output.content}")


if __name__ == "__main__":
    demo()
