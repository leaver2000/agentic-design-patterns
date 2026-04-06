"""
Chain of Responsibility — Agent Pipeline
abc: src/abc/chain-of-responsibility.md

Passes a task along a chain of handler agents until one handles it.
Demonstrated with a tiered routing chain: fast → standard → deep.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field

import anthropic


# ---------------------------------------------------------------------------
# Handler interface
# ---------------------------------------------------------------------------

@dataclass
class Task:
    content: str
    complexity: str = "unknown"  # "simple" | "standard" | "complex"
    metadata: dict = field(default_factory=dict)


@dataclass
class HandlerResult:
    content: str
    handled_by: str
    passed: bool = False  # True if this handler forwarded rather than handled


class Handler(abc.ABC):
    """Handler: defines the interface; optionally holds the next handler."""

    def __init__(self) -> None:
        self._next: Handler | None = None

    def set_next(self, handler: Handler) -> Handler:
        """Set the successor; return it for fluent chaining."""
        self._next = handler
        return handler

    @abc.abstractmethod
    def can_handle(self, task: Task) -> bool:
        """Return True if this handler is capable of handling the task."""
        ...

    @abc.abstractmethod
    def handle(self, task: Task) -> HandlerResult | None:
        """
        Attempt to handle the task.
        Return a HandlerResult if handled.
        Return None to pass to the next handler.
        """
        ...

    def _forward(self, task: Task) -> HandlerResult | None:
        """Forward to successor if one exists."""
        if self._next:
            return self._next.handle(task)
        return HandlerResult(
            content="No handler in the chain could handle this task.",
            handled_by="chain-terminal",
        )


# ---------------------------------------------------------------------------
# Concrete Handlers — tiered routing by complexity
# ---------------------------------------------------------------------------

class FastHandler(Handler):
    """
    ConcreteHandler: handles simple tasks cheaply.
    Passes complex tasks to the next handler.
    """

    HANDLES = {"simple"}

    def __init__(self) -> None:
        super().__init__()
        self._client = anthropic.Anthropic()

    def can_handle(self, task: Task) -> bool:
        return task.complexity in self.HANDLES

    def handle(self, task: Task) -> HandlerResult | None:
        if not self.can_handle(task):
            return self._forward(task)

        msg = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system="You are a fast-response agent. Give brief, direct answers.",
            messages=[{"role": "user", "content": task.content}],
        )
        return HandlerResult(content=msg.content[0].text, handled_by="fast-handler")


class StandardHandler(Handler):
    """Handles standard-complexity tasks; passes deep/complex tasks forward."""

    HANDLES = {"simple", "standard", "unknown"}

    def __init__(self) -> None:
        super().__init__()
        self._client = anthropic.Anthropic()

    def can_handle(self, task: Task) -> bool:
        return task.complexity in self.HANDLES

    def handle(self, task: Task) -> HandlerResult | None:
        if task.complexity == "complex":
            return self._forward(task)

        msg = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system="You are a standard-response agent. Give thorough but focused answers.",
            messages=[{"role": "user", "content": task.content}],
        )
        return HandlerResult(content=msg.content[0].text, handled_by="standard-handler")


class DeepHandler(Handler):
    """Terminal handler: handles everything that reaches it."""

    def can_handle(self, task: Task) -> bool:
        return True  # Always handles — terminal handler

    def __init__(self) -> None:
        super().__init__()
        self._client = anthropic.Anthropic()

    def handle(self, task: Task) -> HandlerResult | None:
        msg = self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=(
                "You are a deep-analysis agent. Provide thorough, well-structured "
                "responses with examples and nuance."
            ),
            messages=[{"role": "user", "content": task.content}],
        )
        return HandlerResult(content=msg.content[0].text, handled_by="deep-handler")


# ---------------------------------------------------------------------------
# Routing Handler — classifies complexity then forwards
# ---------------------------------------------------------------------------

class ComplexityRouter(Handler):
    """
    Pre-processing handler: infers task complexity, annotates the task,
    then forwards to the appropriate handler.
    """

    def can_handle(self, task: Task) -> bool:
        return True  # Routing handler always participates

    def __init__(self) -> None:
        super().__init__()
        self._client = anthropic.Anthropic()

    def handle(self, task: Task) -> HandlerResult | None:
        if task.complexity != "unknown":
            return self._forward(task)

        # Classify complexity
        msg = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            system=(
                "Classify the complexity of this task. "
                "Respond with exactly one word: simple, standard, or complex."
            ),
            messages=[{"role": "user", "content": task.content}],
        )
        label = msg.content[0].text.strip().lower()
        if label not in {"simple", "standard", "complex"}:
            label = "standard"
        task.complexity = label
        task.metadata["classified_by"] = "complexity-router"

        return self._forward(task)


# ---------------------------------------------------------------------------
# Chain builder
# ---------------------------------------------------------------------------

def build_tiered_chain() -> Handler:
    """
    Build the chain: router → fast → standard → deep
    """
    router = ComplexityRouter()
    fast = FastHandler()
    standard = StandardHandler()
    deep = DeepHandler()

    router.set_next(fast).set_next(standard).set_next(deep)
    return router


def demo() -> None:
    print("=== Chain of Responsibility Demo ===\n")

    chain = build_tiered_chain()

    tasks = [
        Task(content="What is 2 + 2?"),
        Task(content="Summarize the key points of the transformer architecture.", complexity="standard"),
        Task(content="Analyze the philosophical implications of large language models on the nature of understanding and consciousness.", complexity="complex"),
    ]

    for task in tasks:
        print(f"Task [{task.complexity}]: {task.content[:70]}")
        result = chain.handle(task)
        if result:
            print(f"  Handled by: {result.handled_by}")
            print(f"  Complexity after routing: {task.complexity}")
            print(f"  Answer: {result.content[:120]}...")
        print()


if __name__ == "__main__":
    demo()
