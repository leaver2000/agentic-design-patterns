"""
Builder — Pipeline Builder
abc: src/abc/builder.md

Separates the construction of a complex agent pipeline from its representation.
The Director holds the recipe; the Builder holds the materials.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Callable

import anthropic


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

@dataclass
class Tool:
    name: str
    description: str
    handler: Callable[[dict], str]


@dataclass
class Memory:
    store: dict = field(default_factory=dict)

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def set(self, key: str, value: str) -> None:
        self.store[key] = value


@dataclass
class BuiltAgent:
    system_prompt: str
    model: str
    tools: list[Tool]
    memory: Memory | None
    _client: anthropic.Anthropic = field(default_factory=anthropic.Anthropic, repr=False)

    def run(self, task: str) -> str:
        # Inject memory context if available
        context = ""
        if self.memory:
            items = list(self.memory.store.items())[:3]
            if items:
                context = "\nRelevant context:\n" + "\n".join(
                    f"  {k}: {v}" for k, v in items
                )

        msg = self._client.messages.create(
            model=self.model,
            max_tokens=512,
            system=self.system_prompt + context,
            messages=[{"role": "user", "content": task}],
        )
        return msg.content[0].text


# ---------------------------------------------------------------------------
# Abstract Builder
# ---------------------------------------------------------------------------

class AgentBuilder(abc.ABC):
    """Abstract interface every concrete builder must implement."""

    @abc.abstractmethod
    def set_system_prompt(self, prompt: str) -> AgentBuilder: ...

    @abc.abstractmethod
    def add_tool(self, tool: Tool) -> AgentBuilder: ...

    @abc.abstractmethod
    def add_memory(self, memory: Memory) -> AgentBuilder: ...

    @abc.abstractmethod
    def set_model(self, model: str) -> AgentBuilder: ...

    @abc.abstractmethod
    def build(self) -> BuiltAgent: ...

    def reset(self) -> AgentBuilder:
        """Clear builder state so it can be reused."""
        return self


# ---------------------------------------------------------------------------
# Concrete Builders
# ---------------------------------------------------------------------------

class StandardAgentBuilder(AgentBuilder):
    """Builds a fully featured agent with tools and memory."""

    def __init__(self) -> None:
        self._prompt: str = ""
        self._model: str = "claude-haiku-4-5-20251001"
        self._tools: list[Tool] = []
        self._memory: Memory | None = None
        self._ready = False

    def set_system_prompt(self, prompt: str) -> StandardAgentBuilder:
        self._prompt = prompt
        return self

    def add_tool(self, tool: Tool) -> StandardAgentBuilder:
        self._tools.append(tool)
        return self

    def add_memory(self, memory: Memory) -> StandardAgentBuilder:
        self._memory = memory
        return self

    def set_model(self, model: str) -> StandardAgentBuilder:
        self._model = model
        return self

    def build(self) -> BuiltAgent:
        if not self._prompt:
            raise ValueError("System prompt is required before build()")
        agent = BuiltAgent(
            system_prompt=self._prompt,
            model=self._model,
            tools=list(self._tools),
            memory=self._memory,
        )
        # Reset for reuse
        self._prompt = ""
        self._tools = []
        self._memory = None
        return agent


class LightweightAgentBuilder(AgentBuilder):
    """Builds a minimal agent — no tools, no memory."""

    def __init__(self) -> None:
        self._prompt: str = ""
        self._model: str = "claude-haiku-4-5-20251001"

    def set_system_prompt(self, prompt: str) -> LightweightAgentBuilder:
        self._prompt = prompt
        return self

    def add_tool(self, tool: Tool) -> LightweightAgentBuilder:
        # Lightweight builder silently ignores tools
        return self

    def add_memory(self, memory: Memory) -> LightweightAgentBuilder:
        # Lightweight builder silently ignores memory
        return self

    def set_model(self, model: str) -> LightweightAgentBuilder:
        self._model = model
        return self

    def build(self) -> BuiltAgent:
        if not self._prompt:
            raise ValueError("System prompt is required before build()")
        return BuiltAgent(
            system_prompt=self._prompt,
            model=self._model,
            tools=[],
            memory=None,
        )


# ---------------------------------------------------------------------------
# Director — holds the construction recipe
# ---------------------------------------------------------------------------

class ResearchPipelineDirector:
    """Constructs a research pipeline regardless of which builder is used."""

    def __init__(self, builder: AgentBuilder) -> None:
        self._builder = builder

    def build_researcher(self) -> BuiltAgent:
        mem = Memory({"domain": "academic", "style": "formal citations"})
        return (
            self._builder
            .set_system_prompt(
                "You are a research agent. Find relevant facts and cite sources."
            )
            .add_memory(mem)
            .set_model("claude-sonnet-4-6")
            .build()
        )

    def build_summarizer(self) -> BuiltAgent:
        return (
            self._builder
            .set_system_prompt(
                "You are a summarization agent. Condense research into key points."
            )
            .set_model("claude-haiku-4-5-20251001")
            .build()
        )


def demo() -> None:
    print("=== Builder Demo ===\n")

    topic = "multi-agent AI orchestration frameworks"

    # Full-featured pipeline
    director = ResearchPipelineDirector(StandardAgentBuilder())
    researcher = director.build_researcher()
    summarizer = director.build_summarizer()

    research = researcher.run(f"What are the key concepts in: {topic}?")
    summary = summarizer.run(f"Summarize in 2 sentences:\n{research}")

    print("Full pipeline:")
    print(f"  Research: {research[:150]}...")
    print(f"  Summary:  {summary}\n")

    # Lightweight pipeline — same director, different builder
    director2 = ResearchPipelineDirector(LightweightAgentBuilder())
    researcher2 = director2.build_researcher()
    research2 = researcher2.run(f"What are the key concepts in: {topic}?")
    print("Lightweight pipeline:")
    print(f"  Research: {research2[:150]}...")


if __name__ == "__main__":
    demo()
