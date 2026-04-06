"""
Mediator — Orchestrator
abc: src/abc/mediator.md

Centralizes multi-agent interaction so agents never call each other
directly. Every interaction goes through the Mediator (Orchestrator).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

import anthropic


# ---------------------------------------------------------------------------
# Event and result types
# ---------------------------------------------------------------------------

@dataclass
class AgentEvent:
    sender: str
    event_type: str  # "completed" | "error" | "needs_input"
    payload: dict = field(default_factory=dict)


@dataclass
class AgentResult:
    content: str
    agent: str
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Mediator interface
# ---------------------------------------------------------------------------

class Mediator(abc.ABC):
    """Mediator: centralizes how colleagues communicate."""

    @abc.abstractmethod
    def notify(self, sender: "Colleague", event: str, payload: dict) -> None:
        """Called by colleagues when something happens."""
        ...

    @abc.abstractmethod
    def route(self, task: str) -> "Colleague":
        """Decide which colleague handles the next step."""
        ...


# ---------------------------------------------------------------------------
# Colleague base
# ---------------------------------------------------------------------------

class Colleague(abc.ABC):
    """Colleague: knows only its Mediator; communicates through it."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._mediator: Mediator | None = None

    def set_mediator(self, mediator: Mediator) -> None:
        self._mediator = mediator

    def send(self, event: str, payload: dict) -> None:
        assert self._mediator is not None, "Mediator not set"
        self._mediator.notify(self, event, payload)

    @property
    def name(self) -> str:
        return self._name

    @abc.abstractmethod
    def handle(self, task: str, context: dict | None = None) -> AgentResult: ...


# ---------------------------------------------------------------------------
# Concrete Colleagues
# ---------------------------------------------------------------------------

class _ClaudeColleague(Colleague):
    def __init__(self, name: str, system: str, model: str = "claude-haiku-4-5-20251001") -> None:
        super().__init__(name)
        self._system = system
        self._model = model
        self._client = anthropic.Anthropic()

    def handle(self, task: str, context: dict | None = None) -> AgentResult:
        ctx_text = ""
        if context:
            ctx_text = "\nContext:\n" + "\n".join(f"  {k}: {v}" for k, v in context.items())

        msg = self._client.messages.create(
            model=self._model,
            max_tokens=400,
            system=self._system + ctx_text,
            messages=[{"role": "user", "content": task}],
        )
        result = AgentResult(content=msg.content[0].text, agent=self._name)
        self.send("completed", {"result": result.content[:100]})
        return result


class PlannerColleague(_ClaudeColleague):
    def __init__(self) -> None:
        super().__init__(
            name="planner",
            system=(
                "You are a planning agent. Given a task, break it down into "
                "2-3 specific subtasks as a numbered list. Be concrete."
            ),
        )


class ResearcherColleague(_ClaudeColleague):
    def __init__(self) -> None:
        super().__init__(
            name="researcher",
            system="You are a research agent. Answer questions with specific, factual responses.",
            model="claude-sonnet-4-6",
        )


class WriterColleague(_ClaudeColleague):
    def __init__(self) -> None:
        super().__init__(
            name="writer",
            system=(
                "You are a writing agent. Given research notes, produce a clear, "
                "well-structured paragraph."
            ),
        )


class ReviewerColleague(_ClaudeColleague):
    def __init__(self) -> None:
        super().__init__(
            name="reviewer",
            system=(
                "You are a review agent. Given a draft, respond with JSON: "
                "{\"verdict\": \"pass\"|\"revise\", \"feedback\": str}"
            ),
        )


# ---------------------------------------------------------------------------
# Concrete Mediator — WorkflowOrchestrator
# ---------------------------------------------------------------------------

class WorkflowOrchestrator(Mediator):
    """
    ConcreteMediator: implements cooperative behavior.
    Knows and maintains all colleagues; routes tasks between them.
    Agents are unaware of each other — they only talk to the orchestrator.
    """

    def __init__(self) -> None:
        self._planner = PlannerColleague()
        self._researcher = ResearcherColleague()
        self._writer = WriterColleague()
        self._reviewer = ReviewerColleague()
        self._colleagues = [self._planner, self._researcher, self._writer, self._reviewer]
        self._event_log: list[dict] = []

        for colleague in self._colleagues:
            colleague.set_mediator(self)

    def notify(self, sender: Colleague, event: str, payload: dict) -> None:
        self._event_log.append({"from": sender.name, "event": event, **payload})

    def route(self, task: str) -> Colleague:
        # Simple routing: first agent in the workflow is always the planner
        return self._planner

    def run(self, topic: str) -> AgentResult:
        """Execute the full plan → research → write → review workflow."""
        # 1. Plan
        plan_result = self._planner.handle(
            f"Create a research and writing plan for: {topic}"
        )

        # 2. Research (informed by plan)
        research_result = self._researcher.handle(
            f"Research: {topic}",
            context={"plan": plan_result.content[:300]},
        )

        # 3. Write (informed by research)
        write_result = self._writer.handle(
            f"Write about: {topic}",
            context={"research": research_result.content[:600]},
        )

        # 4. Review
        review_result = self._reviewer.handle(write_result.content)

        return AgentResult(
            content=write_result.content,
            agent="workflow-orchestrator",
            metadata={
                "review": review_result.content,
                "event_log": self._event_log,
            },
        )

    @property
    def event_log(self) -> list[dict]:
        return list(self._event_log)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo() -> None:
    print("=== Mediator Demo ===\n")

    orchestrator = WorkflowOrchestrator()
    result = orchestrator.run("the role of attention mechanisms in large language models")

    print(f"Final output:\n{result.content}\n")
    print(f"Review: {result.metadata['review']}\n")
    print("Event log (agents → mediator):")
    for entry in orchestrator.event_log:
        print(f"  [{entry['from']}] {entry['event']}")


if __name__ == "__main__":
    demo()
