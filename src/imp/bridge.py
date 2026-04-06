"""
Bridge — Model Bridge
abc: src/abc/bridge.md

Decouples agent task logic (abstraction) from the model backend (implementor)
so both can vary independently. Swap Claude for GPT or a local model without
touching the agent's orchestration code.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Iterator


# ---------------------------------------------------------------------------
# Implementor interface — the model backend
# ---------------------------------------------------------------------------

@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str


class ModelBackend(abc.ABC):
    """Implementor: defines the model-layer interface."""

    @abc.abstractmethod
    def complete(self, messages: list[Message], system: str = "", max_tokens: int = 512) -> str:
        """Synchronous completion."""
        ...

    @abc.abstractmethod
    def model_id(self) -> str:
        """Return the canonical model identifier."""
        ...


# ---------------------------------------------------------------------------
# Concrete Implementors
# ---------------------------------------------------------------------------

class ClaudeBackend(ModelBackend):
    """Concrete Implementor: Anthropic Claude via the `anthropic` SDK."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        import anthropic
        self._client = anthropic.Anthropic()
        self._model = model

    def model_id(self) -> str:
        return self._model

    def complete(self, messages: list[Message], system: str = "", max_tokens: int = 512) -> str:
        api_msgs = [{"role": m.role, "content": m.content} for m in messages]
        kwargs: dict = {"model": self._model, "max_tokens": max_tokens, "messages": api_msgs}
        if system:
            kwargs["system"] = system
        response = self._client.messages.create(**kwargs)
        return response.content[0].text


class EchoBackend(ModelBackend):
    """
    Concrete Implementor: deterministic echo backend for testing.
    No API key required; returns a fixed prefix + last user message.
    """

    def model_id(self) -> str:
        return "echo-v0"

    def complete(self, messages: list[Message], system: str = "", max_tokens: int = 512) -> str:
        last = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return f"[ECHO] Received: {last[:100]}"


# ---------------------------------------------------------------------------
# Abstraction — the agent, referencing the backend only via ModelBackend
# ---------------------------------------------------------------------------

class AgentAbstraction(abc.ABC):
    """
    Abstraction: defines the agent's high-level interface.
    Holds a ModelBackend reference; never inspects its concrete type.
    """

    def __init__(self, backend: ModelBackend) -> None:
        self._backend = backend

    @abc.abstractmethod
    def run(self, task: str) -> str:
        """Execute the agent's task using self._backend."""
        ...

    def swap_backend(self, backend: ModelBackend) -> None:
        """Replace the backend at runtime — no other changes needed."""
        self._backend = backend


# ---------------------------------------------------------------------------
# Refined Abstractions — agent behaviors that extend the base
# ---------------------------------------------------------------------------

class ReActAgent(AgentAbstraction):
    """
    Refined Abstraction: a simple ReAct loop (Reason + Act).
    Uses the backend for both reasoning and synthesis; backend is swappable.
    """

    MAX_STEPS = 3

    def run(self, task: str) -> str:
        history: list[Message] = [Message(role="user", content=task)]
        system = (
            "You are a ReAct agent. For each step, output:\n"
            "Thought: <your reasoning>\n"
            "Action: <what you would do next, or 'FINISH' to stop>\n"
            "When you write Action: FINISH, provide the final answer."
        )

        result = ""
        for step in range(self.MAX_STEPS):
            response = self._backend.complete(history, system=system, max_tokens=300)
            history.append(Message(role="assistant", content=response))

            if "FINISH" in response or "Action: FINISH" in response:
                result = response
                break

            # Feed the step back as a new user turn (simplified loop)
            history.append(Message(
                role="user",
                content="Continue to the next step, or write 'Action: FINISH' with your final answer.",
            ))

        return result or history[-2].content  # last assistant turn


class SummarizationAgent(AgentAbstraction):
    """Refined Abstraction: condenses content to key points."""

    def run(self, task: str) -> str:
        system = "You are a summarization agent. Be concise — 3 bullet points maximum."
        messages = [Message(role="user", content=task)]
        return self._backend.complete(messages, system=system, max_tokens=200)


class ClassificationAgent(AgentAbstraction):
    """Refined Abstraction: classifies input into a category."""

    def __init__(self, backend: ModelBackend, categories: list[str]) -> None:
        super().__init__(backend)
        self._categories = categories

    def run(self, task: str) -> str:
        cats = ", ".join(self._categories)
        system = (
            f"You are a classification agent. Classify the input into one of: {cats}. "
            "Respond with ONLY the category name."
        )
        messages = [Message(role="user", content=task)]
        return self._backend.complete(messages, system=system, max_tokens=20)


def demo() -> None:
    print("=== Bridge Demo ===\n")

    # Echo backend (no API key needed for this demo path)
    echo = EchoBackend()
    react = ReActAgent(echo)
    print(f"ReActAgent + EchoBackend:\n  {react.run('Explain gradient descent')}\n")

    # Swap to Claude without changing the agent
    claude_haiku = ClaudeBackend("claude-haiku-4-5-20251001")

    summarizer = SummarizationAgent(claude_haiku)
    summary = summarizer.run(
        "Multi-agent systems consist of multiple AI agents that collaborate to "
        "solve tasks. Each agent specializes in a role and communicates through "
        "a shared protocol. This enables parallelism, specialization, and fault isolation."
    )
    print(f"SummarizationAgent + Claude Haiku:\n{summary}\n")

    classifier = ClassificationAgent(claude_haiku, ["technical", "creative", "analytical"])
    category = classifier.run("Write a poem about neural networks.")
    print(f"ClassificationAgent: 'Write a poem about neural networks.' → {category}\n")

    # Swap classifier to echo backend — no code change to ClassificationAgent
    classifier.swap_backend(echo)
    category2 = classifier.run("Write a poem about neural networks.")
    print(f"ClassificationAgent (swapped to echo): → {category2}")


if __name__ == "__main__":
    demo()
