"""
Command — Task Object
abc: src/abc/command.md

Encapsulates an agent invocation as a serializable, queueable,
retryable object. Supports an in-memory task queue with execute/undo.
"""

from __future__ import annotations

import abc
import json
import queue
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import anthropic


# ---------------------------------------------------------------------------
# Command interface
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    content: str
    agent: str


class Command(abc.ABC):
    """Command: declares the interface for executing an operation."""

    @abc.abstractmethod
    def execute(self) -> AgentResult: ...

    @abc.abstractmethod
    def undo(self) -> None:
        """Reverse the effect of execute(), if reversible. No-op if not."""
        ...

    @abc.abstractmethod
    def serialize(self) -> dict:
        """Produce a JSON-serializable representation."""
        ...

    @abc.abstractmethod
    def task_id(self) -> str:
        """Stable identifier for deduplication and idempotency."""
        ...

    @classmethod
    @abc.abstractmethod
    def deserialize(cls, data: dict) -> Command: ...


# ---------------------------------------------------------------------------
# Receiver — the agent that does actual work
# ---------------------------------------------------------------------------

class AgentReceiver:
    def __init__(self, name: str, system: str, model: str = "claude-haiku-4-5-20251001") -> None:
        self._name = name
        self._system = system
        self._model = model
        self._client = anthropic.Anthropic()
        self._last_result: str | None = None

    def invoke(self, task: str) -> AgentResult:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=400,
            system=self._system,
            messages=[{"role": "user", "content": task}],
        )
        self._last_result = msg.content[0].text
        return AgentResult(content=self._last_result, agent=self._name)

    def revoke(self) -> None:
        """Clears the last result (undo semantics for stateful receivers)."""
        self._last_result = None


# ---------------------------------------------------------------------------
# Concrete Commands
# ---------------------------------------------------------------------------

_RECEIVERS: dict[str, AgentReceiver] = {}
_RECEIVERS_LOCK = threading.Lock()


def _get_receiver(agent_name: str, system: str, model: str) -> AgentReceiver:
    with _RECEIVERS_LOCK:
        if agent_name not in _RECEIVERS:
            _RECEIVERS[agent_name] = AgentReceiver(agent_name, system, model)
        return _RECEIVERS[agent_name]


class AgentInvokeCommand(Command):
    """
    ConcreteCommand: binds one agent invocation with its arguments.
    Self-contained — carries everything needed to execute or replay.
    """

    def __init__(
        self,
        agent_name: str,
        system_prompt: str,
        task: str,
        model: str = "claude-haiku-4-5-20251001",
        task_id: str | None = None,
    ) -> None:
        self._agent_name = agent_name
        self._system_prompt = system_prompt
        self._task = task
        self._model = model
        self._id = task_id or str(uuid.uuid4())
        self._result: AgentResult | None = None
        self._executed = False

    def task_id(self) -> str:
        return self._id

    def execute(self) -> AgentResult:
        if self._executed:
            # Idempotent: return cached result
            assert self._result is not None
            return self._result
        receiver = _get_receiver(self._agent_name, self._system_prompt, self._model)
        self._result = receiver.invoke(self._task)
        self._executed = True
        return self._result

    def undo(self) -> None:
        if not self._executed:
            return  # No-op: never executed
        receiver = _get_receiver(self._agent_name, self._system_prompt, self._model)
        receiver.revoke()
        self._result = None
        self._executed = False

    def serialize(self) -> dict:
        return {
            "type": "AgentInvokeCommand",
            "task_id": self._id,
            "agent_name": self._agent_name,
            "system_prompt": self._system_prompt,
            "task": self._task,
            "model": self._model,
        }

    @classmethod
    def deserialize(cls, data: dict) -> AgentInvokeCommand:
        return cls(
            agent_name=data["agent_name"],
            system_prompt=data["system_prompt"],
            task=data["task"],
            model=data.get("model", "claude-haiku-4-5-20251001"),
            task_id=data["task_id"],
        )


# ---------------------------------------------------------------------------
# Invoker — the task queue
# ---------------------------------------------------------------------------

@dataclass
class QueuedTask:
    command: Command
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"  # pending | running | done | failed
    result: AgentResult | None = None
    error: str | None = None


class AgentTaskQueue:
    """
    Invoker: manages the lifecycle of Commands.
    Supports enqueue, execute-all, and undo.
    """

    def __init__(self) -> None:
        self._queue: list[QueuedTask] = []
        self._history: list[QueuedTask] = []

    def enqueue(self, command: Command) -> str:
        qt = QueuedTask(command=command)
        self._queue.append(qt)
        return command.task_id()

    def run_all(self) -> list[QueuedTask]:
        completed: list[QueuedTask] = []
        while self._queue:
            qt = self._queue.pop(0)
            qt.status = "running"
            try:
                qt.result = qt.command.execute()
                qt.status = "done"
            except Exception as exc:
                qt.error = str(exc)
                qt.status = "failed"
            self._history.append(qt)
            completed.append(qt)
        return completed

    def undo_last(self) -> bool:
        if not self._history:
            return False
        qt = self._history.pop()
        qt.command.undo()
        qt.status = "undone"
        return True

    def export_queue(self) -> list[dict]:
        """Serialize pending commands for persistence or inspection."""
        return [qt.command.serialize() for qt in self._queue]

    def pending_count(self) -> int:
        return len(self._queue)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo() -> None:
    print("=== Command Demo ===\n")

    queue = AgentTaskQueue()

    # Enqueue several agent invocations as Command objects
    tid1 = queue.enqueue(AgentInvokeCommand(
        agent_name="researcher",
        system_prompt="You are a research agent. Give concise factual answers.",
        task="What is a vector database?",
    ))
    tid2 = queue.enqueue(AgentInvokeCommand(
        agent_name="summarizer",
        system_prompt="You are a summarization agent. Be brief.",
        task="Summarize in one sentence: multi-agent AI systems enable parallelism and specialization.",
    ))
    tid3 = queue.enqueue(AgentInvokeCommand(
        agent_name="classifier",
        system_prompt="Classify text as: technical | creative | other. One word only.",
        task="Implement a binary search tree in Python.",
    ))

    print(f"Queued {queue.pending_count()} tasks")
    print(f"Serialized queue:\n{json.dumps(queue.export_queue(), indent=2)}\n")

    # Run all
    results = queue.run_all()
    print("Results:")
    for qt in results:
        print(f"  [{qt.command.task_id()[:8]}...] status={qt.status}")
        if qt.result:
            print(f"    → {qt.result.content[:100]}...")
        if qt.error:
            print(f"    ERROR: {qt.error}")
    print()

    # Undo last
    print("Undoing last command...")
    undone = queue.undo_last()
    print(f"Undo successful: {undone}")


if __name__ == "__main__":
    demo()
