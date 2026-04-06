"""
State — Agent State Machine
abc: src/abc/state.md

An agent's behavior changes based on its current phase.
Demonstrated with a ReAct-style agent:
  PlanningState → ExecutingState → ReviewingState → DoneState
  Any state → ErrorState on failure
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

import anthropic


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class Plan:
    steps: list[str]
    raw: str


@dataclass
class StepResult:
    step: str
    output: str


@dataclass
class AgentResult:
    content: str
    state_history: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# State interface
# ---------------------------------------------------------------------------

class State(abc.ABC):
    """State: encapsulates behavior for a specific phase."""

    @abc.abstractmethod
    def on_enter(self, agent: "StatefulAgent") -> None:
        """Called when the agent transitions into this state."""
        ...

    @abc.abstractmethod
    def handle(self, agent: "StatefulAgent", input: Any) -> Any:
        """Perform the state's primary action."""
        ...

    def on_exit(self, agent: "StatefulAgent") -> None:
        """Called when transitioning out. Default is no-op."""
        ...

    @abc.abstractmethod
    def state_name(self) -> str: ...


# ---------------------------------------------------------------------------
# Context — the agent holding state
# ---------------------------------------------------------------------------

class StatefulAgent:
    """Context: delegates phase-specific behavior to the current State."""

    def __init__(self, system_context: str, model: str = "claude-haiku-4-5-20251001") -> None:
        self._system_context = system_context
        self._model = model
        self._client = anthropic.Anthropic()
        self._state: State = PlanningState()
        self._state_history: list[str] = []
        self._plan: Plan | None = None
        self._step_results: list[StepResult] = []
        self._final_result: AgentResult | None = None

    def transition_to(self, state: State) -> None:
        """Explicit state transition — no implicit transitions allowed."""
        self._state.on_exit(self)
        self._state = state
        self._state_history.append(state.state_name())
        state.on_enter(self)

    def run(self, task: str) -> AgentResult:
        """Drive the state machine from PlanningState to DoneState."""
        self.transition_to(PlanningState())
        current_input: Any = task

        while not isinstance(self._state, DoneState):
            try:
                current_input = self._state.handle(self, current_input)
            except Exception as exc:
                self.transition_to(ErrorState(str(exc)))
                break

        return self._final_result or AgentResult(
            content="Agent terminated without a result.",
            state_history=self._state_history,
        )

    def call_claude(self, system: str, user: str, max_tokens: int = 400) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=self._system_context + "\n\n" + system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text

    @property
    def state_name(self) -> str:
        return self._state.state_name()


# ---------------------------------------------------------------------------
# Concrete States
# ---------------------------------------------------------------------------

class PlanningState(State):
    """Decomposes the task into steps; transitions to ExecutingState."""

    def state_name(self) -> str:
        return "planning"

    def on_enter(self, agent: StatefulAgent) -> None:
        pass  # Could initialize planning resources

    def handle(self, agent: StatefulAgent, input: Any) -> Any:
        task = str(input)
        raw_plan = agent.call_claude(
            system=(
                "You are a planning agent. Decompose the task into 2-4 concrete steps. "
                "Output ONLY a numbered list, one step per line."
            ),
            user=task,
        )
        steps = [
            line.split(".", 1)[-1].strip()
            for line in raw_plan.strip().splitlines()
            if line.strip() and line[0].isdigit()
        ]
        if not steps:
            steps = [task]  # Fallback: treat task as one step

        agent._plan = Plan(steps=steps, raw=raw_plan)
        agent.transition_to(ExecutingState())
        return agent._plan

    def on_exit(self, agent: StatefulAgent) -> None:
        pass


class ExecutingState(State):
    """Executes each step in the plan; transitions to ReviewingState."""

    def state_name(self) -> str:
        return "executing"

    def on_enter(self, agent: StatefulAgent) -> None:
        agent._step_results = []

    def handle(self, agent: StatefulAgent, input: Any) -> Any:
        plan = agent._plan
        assert plan is not None, "ExecutingState entered without a plan"

        for step in plan.steps:
            output = agent.call_claude(
                system="You are an execution agent. Carry out the given step thoroughly.",
                user=step,
            )
            agent._step_results.append(StepResult(step=step, output=output))

        agent.transition_to(ReviewingState())
        return agent._step_results

    def on_exit(self, agent: StatefulAgent) -> None:
        pass


class ReviewingState(State):
    """Evaluates step results; transitions to DoneState or back to PlanningState."""

    def state_name(self) -> str:
        return "reviewing"

    def on_enter(self, agent: StatefulAgent) -> None:
        pass

    def handle(self, agent: StatefulAgent, input: Any) -> Any:
        step_results = agent._step_results
        combined = "\n\n".join(
            f"Step: {r.step}\nOutput: {r.output}" for r in step_results
        )
        synthesis = agent.call_claude(
            system=(
                "You are a synthesis agent. Given a set of step results, "
                "produce a clear, coherent final answer."
            ),
            user=combined,
            max_tokens=600,
        )

        agent._final_result = AgentResult(
            content=synthesis,
            state_history=list(agent._state_history),
        )
        agent.transition_to(DoneState())
        return agent._final_result

    def on_exit(self, agent: StatefulAgent) -> None:
        pass


class DoneState(State):
    """Terminal state — no more transitions."""

    def state_name(self) -> str:
        return "done"

    def on_enter(self, agent: StatefulAgent) -> None:
        pass

    def handle(self, agent: StatefulAgent, input: Any) -> Any:
        return agent._final_result


class ErrorState(State):
    """Error terminal state — logs the failure."""

    def __init__(self, error: str) -> None:
        self._error = error

    def state_name(self) -> str:
        return "error"

    def on_enter(self, agent: StatefulAgent) -> None:
        agent._final_result = AgentResult(
            content=f"Agent failed: {self._error}",
            state_history=list(agent._state_history),
        )

    def handle(self, agent: StatefulAgent, input: Any) -> Any:
        return agent._final_result


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo() -> None:
    print("=== State Demo ===\n")

    agent = StatefulAgent(
        system_context="You are a helpful AI assistant.",
        model="claude-haiku-4-5-20251001",
    )

    result = agent.run(
        "Explain the key differences between supervised and unsupervised learning, "
        "with one example of each."
    )

    print(f"State transitions: {' → '.join(result.state_history)}\n")
    print(f"Final result:\n{result.content}")


if __name__ == "__main__":
    demo()
