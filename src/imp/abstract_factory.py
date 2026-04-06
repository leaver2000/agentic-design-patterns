"""
Abstract Factory — Agent Factory
abc: src/abc/abstract-factory.md

Creates families of related agents without specifying concrete classes.
Swapping the factory switches the entire agent family atomically.
"""

from __future__ import annotations

import abc
import os
from dataclasses import dataclass, field

import anthropic


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    content: str
    agent_name: str
    metadata: dict = field(default_factory=dict)


class Agent(abc.ABC):
    """Uniform interface all product agents must satisfy."""

    @abc.abstractmethod
    def run(self, task: str) -> AgentResult: ...

    @property
    @abc.abstractmethod
    def name(self) -> str: ...


# ---------------------------------------------------------------------------
# Abstract Factory
# ---------------------------------------------------------------------------

class AgentFactory(abc.ABC):
    """Declares creation interface for a family of agents."""

    @abc.abstractmethod
    def create_researcher(self) -> Agent: ...

    @abc.abstractmethod
    def create_writer(self) -> Agent: ...

    @abc.abstractmethod
    def create_critic(self) -> Agent: ...

    def supported_roles(self) -> list[str]:
        return ["researcher", "writer", "critic"]

    def validate_family_compatibility(self, agents: list[Agent]) -> bool:
        """All agents must come from the same factory."""
        factory_name = type(self).__name__
        return all(
            agent.name.startswith(factory_name.replace("Factory", "").lower())
            for agent in agents
        )


# ---------------------------------------------------------------------------
# Concrete factory: Research family (Sonnet-grade)
# ---------------------------------------------------------------------------

class _ClaudeAgent(Agent):
    def __init__(self, name: str, system: str, model: str) -> None:
        self._name = name
        self._system = system
        self._model = model
        self._client = anthropic.Anthropic()

    @property
    def name(self) -> str:
        return self._name

    def run(self, task: str) -> AgentResult:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=512,
            system=self._system,
            messages=[{"role": "user", "content": task}],
        )
        return AgentResult(content=msg.content[0].text, agent_name=self._name)


class ResearchAgentFactory(AgentFactory):
    """Produces a research-grade family using Sonnet for depth."""

    MODEL = "claude-sonnet-4-6"

    def create_researcher(self) -> Agent:
        return _ClaudeAgent(
            name="research-researcher",
            system="You are a research agent. Find facts, cite sources, and be thorough.",
            model=self.MODEL,
        )

    def create_writer(self) -> Agent:
        return _ClaudeAgent(
            name="research-writer",
            system="You are a writing agent. Turn research notes into clear, structured prose.",
            model=self.MODEL,
        )

    def create_critic(self) -> Agent:
        return _ClaudeAgent(
            name="research-critic",
            system=(
                "You are a quality critic. Evaluate the output for accuracy, "
                "clarity, and completeness. Return a short JSON verdict."
            ),
            model=self.MODEL,
        )


class FastAgentFactory(AgentFactory):
    """Produces a fast, cheap family using Haiku for throughput."""

    MODEL = "claude-haiku-4-5-20251001"

    def create_researcher(self) -> Agent:
        return _ClaudeAgent(
            name="fast-researcher",
            system="You are a quick-lookup agent. Give concise factual answers.",
            model=self.MODEL,
        )

    def create_writer(self) -> Agent:
        return _ClaudeAgent(
            name="fast-writer",
            system="You are a fast drafting agent. Produce short, punchy copy.",
            model=self.MODEL,
        )

    def create_critic(self) -> Agent:
        return _ClaudeAgent(
            name="fast-critic",
            system="You are a rapid reviewer. Flag only blocking issues in one sentence.",
            model=self.MODEL,
        )


# ---------------------------------------------------------------------------
# Client code — never references concrete agent classes
# ---------------------------------------------------------------------------

def run_pipeline(factory: AgentFactory, topic: str) -> str:
    researcher = factory.create_researcher()
    writer = factory.create_writer()
    critic = factory.create_critic()

    research = researcher.run(f"Research this topic briefly: {topic}")
    draft = writer.run(f"Write a short paragraph about: {research.content}")
    review = critic.run(f"Review this draft:\n{draft.content}")

    return (
        f"[{factory.__class__.__name__}]\n"
        f"Research: {research.content[:120]}...\n"
        f"Draft:    {draft.content[:120]}...\n"
        f"Review:   {review.content[:120]}...\n"
    )


def demo() -> None:
    topic = "prompt caching in large language model APIs"

    print("=== Abstract Factory Demo ===\n")
    print("--- Research family (deep) ---")
    print(run_pipeline(ResearchAgentFactory(), topic))

    print("--- Fast family (cheap) ---")
    print(run_pipeline(FastAgentFactory(), topic))


if __name__ == "__main__":
    demo()
