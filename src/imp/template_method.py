"""
Template Method — Workflow Skeleton
abc: src/abc/template-method.md

Defines the skeleton of an agent workflow in a base class.
Subagents fill in the steps without changing the overall structure.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field

import anthropic


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class Plan:
    description: str
    steps: list[str]


@dataclass
class StepResult:
    step: str
    output: str


@dataclass
class AgentResult:
    final_output: str
    plan: Plan
    step_results: list[StepResult]
    agent_type: str


# ---------------------------------------------------------------------------
# AbstractAgent — defines the workflow skeleton
# ---------------------------------------------------------------------------

class WorkflowAgent(abc.ABC):
    """
    AbstractAgent: the template method `run()` is final.
    Subclasses implement plan(), execute(), and review().
    """

    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        self._model = model
        self._client = anthropic.Anthropic()

    # ----------------------------------------------------------------
    # Template method — NOT overridable by ConcreteAgents
    # ----------------------------------------------------------------

    def run(self, task: str) -> AgentResult:  # noqa: B027  (intentionally non-abstract)
        """
        Fixed workflow: plan → hook → execute → review → hook → return.
        ConcreteAgents MUST NOT override this method.
        """
        plan = self.plan(task)
        self._hook_before_execute(plan)
        step_results = self.execute(plan)
        result = self.review(task, step_results)
        self._hook_after_review(result)
        return result

    # ----------------------------------------------------------------
    # Abstract steps — MUST be overridden
    # ----------------------------------------------------------------

    @abc.abstractmethod
    def plan(self, task: str) -> Plan:
        """Step 1: Decompose the task into a concrete plan."""
        ...

    @abc.abstractmethod
    def execute(self, plan: Plan) -> list[StepResult]:
        """Step 2: Carry out each step in the plan."""
        ...

    @abc.abstractmethod
    def review(self, task: str, results: list[StepResult]) -> AgentResult:
        """Step 3: Synthesize step results into a final output."""
        ...

    # ----------------------------------------------------------------
    # Optional hooks — MAY be overridden; MUST call super()
    # ----------------------------------------------------------------

    def _hook_before_execute(self, plan: Plan) -> None:
        """Called after planning, before execution. Default: no-op."""
        pass

    def _hook_after_review(self, result: AgentResult) -> None:
        """Called after review. Default: no-op."""
        pass

    # ----------------------------------------------------------------
    # Shared helper
    # ----------------------------------------------------------------

    def _call(self, system: str, user: str, max_tokens: int = 400) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text


# ---------------------------------------------------------------------------
# Concrete Agents — fill in the steps
# ---------------------------------------------------------------------------

class ResearchAgent(WorkflowAgent):
    """Researches a topic: plan queries → execute searches → synthesize."""

    def plan(self, task: str) -> Plan:
        raw = self._call(
            system="Output a numbered list of 2-3 targeted research queries for this topic. Nothing else.",
            user=task,
        )
        queries = [
            line.split(".", 1)[-1].strip()
            for line in raw.strip().splitlines()
            if line.strip() and line[0].isdigit()
        ]
        return Plan(description=f"Research plan for: {task}", steps=queries or [task])

    def execute(self, plan: Plan) -> list[StepResult]:
        results = []
        for query in plan.steps:
            output = self._call(
                system="You are a research agent. Answer this query with specific facts.",
                user=query,
            )
            results.append(StepResult(step=query, output=output))
        return results

    def review(self, task: str, results: list[StepResult]) -> AgentResult:
        combined = "\n\n".join(f"Query: {r.step}\nFindings: {r.output}" for r in results)
        synthesis = self._call(
            system="Synthesize the research findings into a coherent, well-structured answer.",
            user=f"Original question: {task}\n\n{combined}",
            max_tokens=600,
        )
        return AgentResult(
            final_output=synthesis,
            plan=Plan(description="research", steps=[r.step for r in results]),
            step_results=results,
            agent_type="research-agent",
        )


class CodeAgent(WorkflowAgent):
    """Writes code: plan the implementation → implement → review for quality."""

    def plan(self, task: str) -> Plan:
        raw = self._call(
            system=(
                "You are a planning agent for code. List 2-3 implementation steps. "
                "Output a numbered list only."
            ),
            user=task,
        )
        steps = [
            line.split(".", 1)[-1].strip()
            for line in raw.strip().splitlines()
            if line.strip() and line[0].isdigit()
        ]
        return Plan(description=f"Implementation plan for: {task}", steps=steps or [task])

    def execute(self, plan: Plan) -> list[StepResult]:
        results = []
        for step in plan.steps:
            output = self._call(
                system=(
                    "You are a Python coding agent. Write clean, typed, idiomatic code. "
                    "If this step requires code, write it in a ```python block."
                ),
                user=step,
            )
            results.append(StepResult(step=step, output=output))
        return results

    def review(self, task: str, results: list[StepResult]) -> AgentResult:
        combined = "\n\n".join(f"Step: {r.step}\n{r.output}" for r in results)
        final = self._call(
            system=(
                "You are a code review agent. Combine the implementation steps into a "
                "single, complete, runnable Python module. Fix any inconsistencies."
            ),
            user=f"Task: {task}\n\n{combined}",
            max_tokens=800,
        )
        return AgentResult(
            final_output=final,
            plan=Plan(description="code", steps=[r.step for r in results]),
            step_results=results,
            agent_type="code-agent",
        )

    def _hook_before_execute(self, plan: Plan) -> None:
        """Log the plan before executing."""
        print(f"  [CodeAgent] Plan: {len(plan.steps)} steps")
        super()._hook_before_execute(plan)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo() -> None:
    print("=== Template Method Demo ===\n")

    print("--- ResearchAgent ---")
    researcher = ResearchAgent(model="claude-haiku-4-5-20251001")
    r = researcher.run("What are the trade-offs between BM25 and vector search for RAG?")
    print(f"Plan steps: {r.plan.steps}")
    print(f"Result: {r.final_output[:200]}...\n")

    print("--- CodeAgent ---")
    coder = CodeAgent(model="claude-haiku-4-5-20251001")
    c = coder.run("Write a Python function that chunks a list into batches of size n.")
    print(f"Plan steps: {c.plan.steps}")
    print(f"Result:\n{c.final_output[:400]}")


if __name__ == "__main__":
    demo()
