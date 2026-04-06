"""
Iterator — Agent Stream
abc: src/abc/iterator.md

Provides sequential access to agent outputs without exposing the
underlying generation mechanism.

Demonstrated variants:
  - StreamingIterator    — yields tokens as they arrive from the model
  - BatchResultIterator  — iterates over a pre-computed list of AgentResults
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import AsyncIterator, Iterator

import anthropic


# ---------------------------------------------------------------------------
# Aggregate and element types
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    content: str
    index: int
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Iterator interface
# ---------------------------------------------------------------------------

class AgentIterator(abc.ABC):
    """Iterator: defines the interface for sequential traversal."""

    @abc.abstractmethod
    def __iter__(self) -> Iterator[str]: ...

    @abc.abstractmethod
    def has_next(self) -> bool: ...

    def reset(self) -> None:
        raise NotImplementedError("This iterator does not support reset()")


# ---------------------------------------------------------------------------
# Concrete Iterator 1: Streaming token iterator
# ---------------------------------------------------------------------------

class StreamingIterator(AgentIterator):
    """
    ConcreteIterator: yields text chunks from a streaming Anthropic response.
    Cannot be reset (the stream is consumed).
    """

    def __init__(self, prompt: str, system: str = "", model: str = "claude-haiku-4-5-20251001") -> None:
        self._prompt = prompt
        self._system = system
        self._model = model
        self._client = anthropic.Anthropic()
        self._stream = None
        self._exhausted = False

    def __iter__(self) -> Iterator[str]:
        return self._generate()

    def _generate(self) -> Iterator[str]:
        kwargs: dict = {
            "model": self._model,
            "max_tokens": 400,
            "messages": [{"role": "user", "content": self._prompt}],
        }
        if self._system:
            kwargs["system"] = self._system

        with self._client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text
        self._exhausted = True

    def has_next(self) -> bool:
        return not self._exhausted

    def reset(self) -> None:
        raise NotImplementedError("StreamingIterator cannot be reset — the stream is consumed")


# ---------------------------------------------------------------------------
# Concrete Iterator 2: Batch result iterator
# ---------------------------------------------------------------------------

class BatchResultIterator(AgentIterator):
    """
    ConcreteIterator: iterates over a finite list of AgentResults.
    Supports reset() — the collection is in memory.
    """

    def __init__(self, results: list[AgentResult]) -> None:
        self._results = results
        self._pos = 0

    def __iter__(self) -> Iterator[str]:
        return self._generate()

    def _generate(self) -> Iterator[str]:
        while self._pos < len(self._results):
            yield self._results[self._pos].content
            self._pos += 1

    def has_next(self) -> bool:
        return self._pos < len(self._results)

    def reset(self) -> None:
        self._pos = 0

    def peek(self) -> AgentResult | None:
        if self._pos < len(self._results):
            return self._results[self._pos]
        return None

    def total(self) -> int:
        return len(self._results)


# ---------------------------------------------------------------------------
# Concrete Aggregate: BatchRunner produces a BatchResultIterator
# ---------------------------------------------------------------------------

class BatchAgentRunner:
    """
    ConcreteAggregate: runs a list of tasks and returns an iterator over results.
    """

    def __init__(self, system: str, model: str = "claude-haiku-4-5-20251001") -> None:
        self._system = system
        self._model = model
        self._client = anthropic.Anthropic()

    def run_batch(self, tasks: list[str]) -> BatchResultIterator:
        results: list[AgentResult] = []
        for i, task in enumerate(tasks):
            msg = self._client.messages.create(
                model=self._model,
                max_tokens=200,
                system=self._system,
                messages=[{"role": "user", "content": task}],
            )
            results.append(AgentResult(
                content=msg.content[0].text,
                index=i,
                metadata={"task": task[:60]},
            ))
        return BatchResultIterator(results)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo() -> None:
    print("=== Iterator Demo ===\n")

    # 1. Streaming iterator — collect tokens as they arrive
    print("--- Streaming Iterator ---")
    stream_iter = StreamingIterator(
        prompt="Explain attention in transformers in 3 sentences.",
        system="Be concise.",
    )
    print("Response (token by token): ", end="", flush=True)
    full = ""
    for token in stream_iter:
        print(token, end="", flush=True)
        full += token
    print(f"\n[{len(full)} chars total]\n")

    # 2. Batch iterator — iterate over pre-run results
    print("--- Batch Result Iterator ---")
    runner = BatchAgentRunner(
        system="You are a classification agent. Respond with one word: technical | creative | other."
    )
    tasks = [
        "Implement a binary search tree.",
        "Write a haiku about the ocean.",
        "What time is it in Tokyo?",
    ]
    batch_iter = runner.run_batch(tasks)
    print(f"Total results: {batch_iter.total()}")
    for i, content in enumerate(batch_iter):
        print(f"  Task {i}: {tasks[i][:40]!r} → {content.strip()}")

    # Reset and iterate again
    batch_iter.reset()
    print(f"\nAfter reset, has_next: {batch_iter.has_next()}")
    print(f"Peek: {batch_iter.peek()}")


if __name__ == "__main__":
    demo()
