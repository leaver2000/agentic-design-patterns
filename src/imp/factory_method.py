"""
Factory Method — Agent Spawner
abc: src/abc/factory-method.md

Defines an interface for spawning an agent; subclasses decide which
concrete agent to instantiate based on runtime context.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass

import anthropic


# ---------------------------------------------------------------------------
# Agent interface
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    content: str
    agent_type: str


class Agent(abc.ABC):
    @abc.abstractmethod
    def run(self, task: str) -> AgentResult: ...

    @property
    @abc.abstractmethod
    def agent_type(self) -> str: ...


class ClaudeAgent(Agent):
    def __init__(self, agent_type: str, system: str, model: str) -> None:
        self._type = agent_type
        self._system = system
        self._model = model
        self._client = anthropic.Anthropic()

    @property
    def agent_type(self) -> str:
        return self._type

    def run(self, task: str) -> AgentResult:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=400,
            system=self._system,
            messages=[{"role": "user", "content": task}],
        )
        return AgentResult(content=msg.content[0].text, agent_type=self._type)


# ---------------------------------------------------------------------------
# Abstract Creator
# ---------------------------------------------------------------------------

class AgentCreator(abc.ABC):
    """
    Declares the factory method `spawn()`.
    May define default behavior that calls spawn().
    """

    @abc.abstractmethod
    def spawn(self, context: dict) -> Agent:
        """Create and return the appropriate agent for the given context."""
        ...

    @abc.abstractmethod
    def agent_type(self) -> str:
        """Return a stable identifier for the agent class this creator produces."""
        ...

    def run_task(self, task: str, context: dict | None = None) -> AgentResult:
        """Template: spawn an agent and run a task on it."""
        agent = self.spawn(context or {})
        return agent.run(task)


# ---------------------------------------------------------------------------
# Concrete Creators
# ---------------------------------------------------------------------------

class ResearchCreator(AgentCreator):
    def agent_type(self) -> str:
        return "researcher"

    def spawn(self, context: dict) -> Agent:
        depth = context.get("depth", "standard")
        model = "claude-sonnet-4-6" if depth == "deep" else "claude-haiku-4-5-20251001"
        return ClaudeAgent(
            agent_type="researcher",
            system="You are a research agent. Answer questions with factual, cited responses.",
            model=model,
        )


class CodingCreator(AgentCreator):
    def agent_type(self) -> str:
        return "coder"

    def spawn(self, context: dict) -> Agent:
        lang = context.get("language", "python")
        return ClaudeAgent(
            agent_type="coder",
            system=(
                f"You are a {lang} coding agent. "
                "Write correct, idiomatic code with type annotations."
            ),
            model="claude-sonnet-4-6",
        )


class ModerationCreator(AgentCreator):
    def agent_type(self) -> str:
        return "moderator"

    def spawn(self, context: dict) -> Agent:
        return ClaudeAgent(
            agent_type="moderator",
            system=(
                "You are a content moderation agent. "
                "Respond with JSON: {\"verdict\": \"pass\"|\"fail\", \"reason\": str}"
            ),
            model="claude-haiku-4-5-20251001",
        )


# ---------------------------------------------------------------------------
# Registry — selects the correct Creator by task type
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, AgentCreator] = {
    "research": ResearchCreator(),
    "coding": CodingCreator(),
    "moderation": ModerationCreator(),
}


def get_creator(task_type: str) -> AgentCreator:
    creator = _REGISTRY.get(task_type)
    if creator is None:
        raise KeyError(f"No creator registered for task type: {task_type!r}")
    return creator


def demo() -> None:
    print("=== Factory Method Demo ===\n")

    cases = [
        ("research", "What is retrieval-augmented generation?", {}),
        ("research", "Explain transformer attention in detail.", {"depth": "deep"}),
        ("coding", "Write a function to chunk a list into batches of size n.", {"language": "python"}),
        ("moderation", "I love sunny days and long walks.", {}),
    ]

    for task_type, task, ctx in cases:
        creator = get_creator(task_type)
        result = creator.run_task(task, ctx)
        print(f"[{result.agent_type}] {task[:50]}")
        print(f"  → {result.content[:120]}...\n")


if __name__ == "__main__":
    demo()
