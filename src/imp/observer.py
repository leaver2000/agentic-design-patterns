"""
Observer — Event Bus
abc: src/abc/observer.md

Defines a one-to-many dependency between agents so that when one
emits an event, all subscribed observers are notified automatically.
Foundation for event-driven agent architectures.
"""

from __future__ import annotations

import abc
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

import anthropic


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

class EventType(str, Enum):
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TOOL_CALLED = "tool.called"
    TOKEN_EMITTED = "token.emitted"
    COST_INCURRED = "cost.incurred"


@dataclass
class AgentEvent:
    event_type: EventType
    source: str
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.monotonic)


# ---------------------------------------------------------------------------
# Observer interface
# ---------------------------------------------------------------------------

class Observer(abc.ABC):
    """Observer: receives notifications from Subjects."""

    @abc.abstractmethod
    def on_event(self, event: AgentEvent) -> None:
        """
        Handle an event. MUST NOT raise — catch and handle internally.
        """
        ...

    @abc.abstractmethod
    def subscribes_to(self) -> list[EventType]:
        """Declare which event types this observer handles."""
        ...


# ---------------------------------------------------------------------------
# Subject mixin
# ---------------------------------------------------------------------------

class Subject:
    """Subject: maintains observer list; emits events."""

    def __init__(self) -> None:
        self._observers: list[Observer] = []
        self._lock = threading.Lock()

    def subscribe(self, observer: Observer) -> None:
        with self._lock:
            if observer not in self._observers:
                self._observers.append(observer)

    def unsubscribe(self, observer: Observer) -> None:
        with self._lock:
            self._observers = [o for o in self._observers if o is not observer]

    def emit(self, event: AgentEvent) -> None:
        with self._lock:
            observers = list(self._observers)
        for observer in observers:
            if event.event_type in observer.subscribes_to():
                try:
                    observer.on_event(event)
                except Exception:
                    pass  # Observers MUST NOT raise; silently swallow


# ---------------------------------------------------------------------------
# Observable Agent (Subject + agent logic combined)
# ---------------------------------------------------------------------------

class ObservableAgent(Subject):
    """An agent that emits events at key lifecycle points."""

    def __init__(self, name: str, system: str, model: str = "claude-haiku-4-5-20251001") -> None:
        super().__init__()
        self._name = name
        self._system = system
        self._model = model
        self._client = anthropic.Anthropic()

    def run(self, task: str) -> str:
        self.emit(AgentEvent(
            event_type=EventType.TASK_STARTED,
            source=self._name,
            payload={"task": task[:80]},
        ))

        try:
            msg = self._client.messages.create(
                model=self._model,
                max_tokens=400,
                system=self._system,
                messages=[{"role": "user", "content": task}],
            )
            content = msg.content[0].text

            # Estimate cost (rough: $0.25/M input, $1.25/M output for Haiku)
            input_tokens = msg.usage.input_tokens
            output_tokens = msg.usage.output_tokens

            self.emit(AgentEvent(
                event_type=EventType.COST_INCURRED,
                source=self._name,
                payload={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "model": self._model,
                },
            ))
            self.emit(AgentEvent(
                event_type=EventType.TASK_COMPLETED,
                source=self._name,
                payload={"result": content[:100], "tokens": output_tokens},
            ))
            return content

        except Exception as exc:
            self.emit(AgentEvent(
                event_type=EventType.TASK_FAILED,
                source=self._name,
                payload={"error": str(exc)},
            ))
            raise


# ---------------------------------------------------------------------------
# Concrete Observers
# ---------------------------------------------------------------------------

class LoggingObserver(Observer):
    """Records all events to an in-memory log."""

    def __init__(self) -> None:
        self._log: list[str] = []

    def subscribes_to(self) -> list[EventType]:
        return list(EventType)  # Subscribe to everything

    def on_event(self, event: AgentEvent) -> None:
        entry = f"[{event.source}] {event.event_type.value} — {event.payload}"
        self._log.append(entry)

    @property
    def log(self) -> list[str]:
        return list(self._log)


class CostTracker(Observer):
    """Accumulates token usage and cost across all agents."""

    # Haiku pricing (approx, per 1M tokens)
    PRICE_INPUT = 0.25 / 1_000_000
    PRICE_OUTPUT = 1.25 / 1_000_000

    def __init__(self) -> None:
        self._total_input = 0
        self._total_output = 0

    def subscribes_to(self) -> list[EventType]:
        return [EventType.COST_INCURRED]

    def on_event(self, event: AgentEvent) -> None:
        self._total_input += event.payload.get("input_tokens", 0)
        self._total_output += event.payload.get("output_tokens", 0)

    @property
    def total_cost_usd(self) -> float:
        return (
            self._total_input * self.PRICE_INPUT
            + self._total_output * self.PRICE_OUTPUT
        )

    @property
    def summary(self) -> dict:
        return {
            "input_tokens": self._total_input,
            "output_tokens": self._total_output,
            "estimated_cost_usd": round(self.total_cost_usd, 6),
        }


class FailureAlerter(Observer):
    """Fires an alert callback on task failures."""

    def __init__(self, alert: Callable[[str], None] | None = None) -> None:
        self._alert = alert or print

    def subscribes_to(self) -> list[EventType]:
        return [EventType.TASK_FAILED]

    def on_event(self, event: AgentEvent) -> None:
        self._alert(
            f"ALERT: Agent {event.source!r} failed — {event.payload.get('error', 'unknown')}"
        )


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo() -> None:
    print("=== Observer Demo ===\n")

    # Create agent (Subject)
    agent = ObservableAgent(
        "research-agent",
        "You are a research agent. Answer questions concisely.",
    )

    # Attach observers
    logger = LoggingObserver()
    cost_tracker = CostTracker()
    alerter = FailureAlerter(alert=lambda msg: print(f"  >> {msg}"))

    agent.subscribe(logger)
    agent.subscribe(cost_tracker)
    agent.subscribe(alerter)

    # Run tasks
    tasks = [
        "What is retrieval-augmented generation?",
        "What are the main advantages of vector databases?",
    ]

    for task in tasks:
        print(f"Running: {task}")
        result = agent.run(task)
        print(f"  {result[:120]}...\n")

    # Observer reports
    print("Event log:")
    for entry in logger.log:
        print(f"  {entry}")

    print(f"\nCost summary: {cost_tracker.summary}")

    # Unsubscribe logger and verify
    agent.unsubscribe(logger)
    print(f"\nAfter unsubscribe, logger entries: {len(logger.log)} (no new entries)")
    agent.run("One more task.")
    print(f"  Logger entries (should be unchanged): {len(logger.log)}")


if __name__ == "__main__":
    demo()
