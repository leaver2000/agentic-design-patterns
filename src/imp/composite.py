"""
Composite — Agent Swarm / Hierarchy
abc: src/abc/composite.md

Composes agents into tree structures so that orchestrators and leaf
agents are treated uniformly. Clients call run() on any node.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

import anthropic


# ---------------------------------------------------------------------------
# Component interface — shared by Leaf and Composite
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    content: str
    agent_name: str
    children: list[AgentResult] = field(default_factory=list)


class AgentComponent(abc.ABC):
    """
    Component: uniform interface for leaf agents and orchestrators.
    Callers never need to distinguish between them.
    """

    @abc.abstractmethod
    def run(self, task: str, context: dict | None = None) -> AgentResult: ...

    @abc.abstractmethod
    def describe(self) -> dict: ...

    # Default no-op implementations — Composites override these
    def add_child(self, agent: AgentComponent) -> None:
        raise TypeError(f"{type(self).__name__} is a leaf and cannot have children")

    def remove_child(self, agent: AgentComponent) -> None:
        raise TypeError(f"{type(self).__name__} is a leaf and cannot have children")

    def children(self) -> list[AgentComponent]:
        return []


# ---------------------------------------------------------------------------
# Leaf — a single Claude-backed agent
# ---------------------------------------------------------------------------

class LeafAgent(AgentComponent):
    """Leaf: performs actual work; has no children."""

    def __init__(self, name: str, system: str, model: str = "claude-haiku-4-5-20251001") -> None:
        self._name = name
        self._system = system
        self._model = model
        self._client = anthropic.Anthropic()

    def run(self, task: str, context: dict | None = None) -> AgentResult:
        ctx_text = ""
        if context:
            ctx_text = "\n\nContext:\n" + "\n".join(f"  {k}: {v}" for k, v in context.items())

        msg = self._client.messages.create(
            model=self._model,
            max_tokens=400,
            system=self._system + ctx_text,
            messages=[{"role": "user", "content": task}],
        )
        return AgentResult(content=msg.content[0].text, agent_name=self._name)

    def describe(self) -> dict:
        return {"type": "leaf", "name": self._name, "model": self._model}


# ---------------------------------------------------------------------------
# Composite — orchestrator that delegates to children
# ---------------------------------------------------------------------------

class CompositeAgent(AgentComponent):
    """
    Composite: holds child AgentComponents; delegates work to them.
    Treats leaf agents and sub-orchestrators identically.
    """

    def __init__(self, name: str, system: str, model: str = "claude-haiku-4-5-20251001") -> None:
        self._name = name
        self._system = system
        self._model = model
        self._children: list[AgentComponent] = []
        self._client = anthropic.Anthropic()

    def add_child(self, agent: AgentComponent) -> None:
        self._children.append(agent)

    def remove_child(self, agent: AgentComponent) -> None:
        self._children.remove(agent)

    def children(self) -> list[AgentComponent]:
        return list(self._children)

    def run(self, task: str, context: dict | None = None) -> AgentResult:
        # 1. Ask the orchestrator how to decompose the task
        child_names = [c.describe()["name"] for c in self._children]
        decomp_prompt = (
            f"You coordinate these agents: {child_names}.\n"
            f"Task: {task}\n\n"
            "For each agent, write one line: AGENT_NAME: <subtask to assign>\n"
            "Every agent must receive an assignment."
        )
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=300,
            system=self._system,
            messages=[{"role": "user", "content": decomp_prompt}],
        )
        assignments = self._parse_assignments(msg.content[0].text, child_names)

        # 2. Dispatch to each child
        child_results: list[AgentResult] = []
        for child in self._children:
            subtask = assignments.get(child.describe()["name"], task)
            result = child.run(subtask, context)
            child_results.append(result)

        # 3. Merge results
        merged_input = "\n\n".join(
            f"[{r.agent_name}]\n{r.content}" for r in child_results
        )
        merge_msg = self._client.messages.create(
            model=self._model,
            max_tokens=500,
            system="You are a synthesis agent. Merge the following sub-results into a coherent answer.",
            messages=[{"role": "user", "content": f"Original task: {task}\n\n{merged_input}"}],
        )

        return AgentResult(
            content=merge_msg.content[0].text,
            agent_name=self._name,
            children=child_results,
        )

    def _parse_assignments(self, text: str, names: list[str]) -> dict[str, str]:
        """Extract AGENT_NAME: <subtask> pairs from the orchestrator response."""
        assignments: dict[str, str] = {}
        for line in text.splitlines():
            for name in names:
                if line.strip().startswith(name + ":"):
                    assignments[name] = line.split(":", 1)[1].strip()
        # Fallback: give everyone the full task
        for name in names:
            assignments.setdefault(name, "Handle your part of the task.")
        return assignments

    def describe(self) -> dict:
        return {
            "type": "composite",
            "name": self._name,
            "model": self._model,
            "children": [c.describe() for c in self._children],
        }


# ---------------------------------------------------------------------------
# Example hierarchy
# ---------------------------------------------------------------------------

def build_research_tree() -> AgentComponent:
    """
    Root
      └─ ResearchOrchestrator (Composite)
           ├─ WebResearcher (Leaf)
           ├─ Synthesizer (Leaf)
           └─ QualityChecker (Composite)
                ├─ FactChecker (Leaf)
                └─ ClarityReviewer (Leaf)
    """
    fact_checker = LeafAgent(
        "fact-checker",
        "You verify factual claims. List any unsupported assertions.",
    )
    clarity_reviewer = LeafAgent(
        "clarity-reviewer",
        "You assess clarity and structure. Flag confusing passages.",
    )
    quality_checker = CompositeAgent(
        "quality-checker",
        "You coordinate fact-checking and clarity review.",
    )
    quality_checker.add_child(fact_checker)
    quality_checker.add_child(clarity_reviewer)

    web_researcher = LeafAgent(
        "web-researcher",
        "You research topics and gather relevant information.",
        model="claude-sonnet-4-6",
    )
    synthesizer = LeafAgent(
        "synthesizer",
        "You synthesize research into a clear, structured response.",
    )

    root = CompositeAgent(
        "research-orchestrator",
        "You orchestrate a research pipeline: research, synthesize, then quality-check.",
        model="claude-sonnet-4-6",
    )
    root.add_child(web_researcher)
    root.add_child(synthesizer)
    root.add_child(quality_checker)

    return root


def demo() -> None:
    import json
    print("=== Composite Demo ===\n")

    root = build_research_tree()
    print("Agent tree:")
    print(json.dumps(root.describe(), indent=2))
    print()

    result = root.run("What are the main trade-offs between RAG and fine-tuning for LLMs?")
    print(f"Root result:\n{result.content}\n")
    print("Child results:")
    for child in result.children:
        print(f"  [{child.agent_name}]: {child.content[:100]}...")


if __name__ == "__main__":
    demo()
