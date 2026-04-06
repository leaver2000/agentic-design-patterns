"""
Prototype — Agent Template Cloning
abc: src/abc/prototype.md

Creates new agents by cloning a pre-configured prototype, avoiding
repeated initialization costs.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

import anthropic


# ---------------------------------------------------------------------------
# Configuration types
# ---------------------------------------------------------------------------

@dataclass
class AgentConfig:
    name: str
    system_prompt: str
    model: str
    tools: list[str] = field(default_factory=list)
    memory_seed: dict[str, str] = field(default_factory=dict)
    temperature: float = 1.0
    max_tokens: int = 512


# ---------------------------------------------------------------------------
# Prototype + ConcretePrototype
# ---------------------------------------------------------------------------

class AgentPrototype:
    """
    A live, configured agent instance that can clone itself.
    The clone is fully independent — mutations do not affect the prototype.
    """

    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._client = anthropic.Anthropic()

    def prototype_id(self) -> str:
        return self._config.name

    def clone(self) -> AgentPrototype:
        """Deep-copy this prototype into an independent instance."""
        cloned_config = copy.deepcopy(self._config)
        return AgentPrototype(cloned_config)

    def configure(self, **overrides: Any) -> AgentPrototype:
        """
        Apply selective overrides to THIS instance (call after clone(), never on prototype).
        Returns self for chaining.
        """
        for key, value in overrides.items():
            if not hasattr(self._config, key):
                raise AttributeError(f"AgentConfig has no field {key!r}")
            setattr(self._config, key, value)
        return self

    def run(self, task: str) -> str:
        system = self._config.system_prompt
        if self._config.memory_seed:
            seed_text = "\n".join(
                f"{k}: {v}" for k, v in self._config.memory_seed.items()
            )
            system += f"\n\nContext:\n{seed_text}"

        msg = self._client.messages.create(
            model=self._config.model,
            max_tokens=self._config.max_tokens,
            system=system,
            messages=[{"role": "user", "content": task}],
        )
        return msg.content[0].text

    def __repr__(self) -> str:
        return (
            f"AgentPrototype(id={self._config.name!r}, "
            f"model={self._config.model!r})"
        )


# ---------------------------------------------------------------------------
# Prototype Registry
# ---------------------------------------------------------------------------

class PrototypeRegistry:
    """
    Stores named prototypes and vends clones on request.
    Ensures the stored prototypes are never modified.
    """

    def __init__(self) -> None:
        self._registry: dict[str, AgentPrototype] = {}

    def register(self, prototype: AgentPrototype) -> None:
        key = prototype.prototype_id()
        if key in self._registry:
            raise KeyError(f"Prototype {key!r} already registered")
        self._registry[key] = prototype

    def clone(self, prototype_id: str, **overrides: Any) -> AgentPrototype:
        """Return a new clone of the named prototype, with optional overrides."""
        proto = self._registry.get(prototype_id)
        if proto is None:
            raise KeyError(f"No prototype registered as {prototype_id!r}")
        instance = proto.clone()
        if overrides:
            instance.configure(**overrides)
        return instance

    def registered_ids(self) -> list[str]:
        return list(self._registry.keys())


# ---------------------------------------------------------------------------
# Pre-built registry (module-level singleton)
# ---------------------------------------------------------------------------

_registry = PrototypeRegistry()

_registry.register(AgentPrototype(AgentConfig(
    name="researcher",
    system_prompt=(
        "You are a research agent. Answer questions with factual, "
        "well-structured responses. Cite your reasoning."
    ),
    model="claude-sonnet-4-6",
    max_tokens=600,
)))

_registry.register(AgentPrototype(AgentConfig(
    name="summarizer",
    system_prompt="You are a summarization agent. Be concise — 2-3 sentences maximum.",
    model="claude-haiku-4-5-20251001",
    max_tokens=200,
)))

_registry.register(AgentPrototype(AgentConfig(
    name="critic",
    system_prompt=(
        "You are a quality critic. Score the input on accuracy, clarity, "
        "and completeness (0.0-1.0 each). Return JSON only."
    ),
    model="claude-haiku-4-5-20251001",
    max_tokens=200,
)))


def get_registry() -> PrototypeRegistry:
    return _registry


def demo() -> None:
    print("=== Prototype Demo ===\n")
    registry = get_registry()
    print(f"Registered prototypes: {registry.registered_ids()}\n")

    # Standard researcher clone
    r1 = registry.clone("researcher")
    answer = r1.run("What is the difference between RAG and fine-tuning?")
    print(f"[researcher] {answer[:200]}...\n")

    # Verbose variant — same prototype, different max_tokens
    r2 = registry.clone("researcher", name="researcher-verbose", max_tokens=1000)
    answer2 = r2.run("What is the difference between RAG and fine-tuning?")
    print(f"[researcher-verbose] {answer2[:200]}...\n")

    # Summarizer
    summarizer = registry.clone("summarizer")
    summary = summarizer.run(answer)
    print(f"[summarizer] {summary}\n")

    # Critic
    critic = registry.clone("critic")
    verdict = critic.run(answer)
    print(f"[critic] {verdict}")


if __name__ == "__main__":
    demo()
