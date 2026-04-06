"""
Memento — Conversation Snapshot
abc: src/abc/memento.md

Captures and externalizes agent state (conversation history, working memory)
so it can be restored without violating encapsulation.
The Caretaker treats the Memento as opaque.
"""

from __future__ import annotations

import abc
import json
import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import anthropic


# ---------------------------------------------------------------------------
# Message type
# ---------------------------------------------------------------------------

@dataclass
class Message:
    role: str
    content: str


# ---------------------------------------------------------------------------
# Memento — the snapshot object
# ---------------------------------------------------------------------------

class Memento:
    """
    Stores the internal state of the Originator.
    Only the Originator may read/write the internal data.
    The Caretaker treats this as opaque.
    """

    def __init__(self, state: dict) -> None:
        self._state = copy.deepcopy(state)
        self._snapshot_id = f"snap-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')}"
        self._created_at = datetime.now(timezone.utc)

    def snapshot_id(self) -> str:
        return self._snapshot_id

    def created_at(self) -> datetime:
        return self._created_at

    def serialize(self) -> str:
        """Produce a portable JSON representation for storage."""
        return json.dumps({
            "snapshot_id": self._snapshot_id,
            "created_at": self._created_at.isoformat(),
            "state": self._state,
        })

    @classmethod
    def deserialize(cls, data: str) -> Memento:
        parsed = json.loads(data)
        m = cls(parsed["state"])
        m._snapshot_id = parsed["snapshot_id"]
        m._created_at = datetime.fromisoformat(parsed["created_at"])
        return m

    # Only the Originator should call this
    def _get_state(self) -> dict:
        return copy.deepcopy(self._state)


# ---------------------------------------------------------------------------
# Originator — the agent
# ---------------------------------------------------------------------------

class ConversationAgent:
    """
    Originator: creates Mementos of its state and restores from them.
    State = conversation history + working memory + turn count.
    """

    def __init__(self, name: str, system: str, model: str = "claude-haiku-4-5-20251001") -> None:
        self._name = name
        self._system = system
        self._model = model
        self._history: list[Message] = []
        self._memory: dict[str, str] = {}
        self._turns: int = 0
        self._client = anthropic.Anthropic()

    def chat(self, user_message: str) -> str:
        self._history.append(Message(role="user", content=user_message))

        api_messages = [{"role": m.role, "content": m.content} for m in self._history]
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=400,
            system=self._system,
            messages=api_messages,
        )
        response = msg.content[0].text
        self._history.append(Message(role="assistant", content=response))
        self._turns += 1
        return response

    def remember(self, key: str, value: str) -> None:
        self._memory[key] = value

    def recall(self, key: str) -> str | None:
        return self._memory.get(key)

    # Memento interface
    def save(self) -> Memento:
        """Capture full state as a Memento."""
        state = {
            "history": [{"role": m.role, "content": m.content} for m in self._history],
            "memory": dict(self._memory),
            "turns": self._turns,
        }
        return Memento(state)

    def load(self, memento: Memento) -> None:
        """Restore state from a Memento. Idempotent for the same Memento."""
        state = memento._get_state()
        self._history = [Message(**m) for m in state["history"]]
        self._memory = state["memory"]
        self._turns = state["turns"]

    @property
    def turns(self) -> int:
        return self._turns

    @property
    def history_length(self) -> int:
        return len(self._history)


# ---------------------------------------------------------------------------
# Caretaker — manages Mementos without inspecting them
# ---------------------------------------------------------------------------

class ConversationCaretaker:
    """
    Caretaker: saves and retrieves Mementos.
    Never inspects or modifies Memento contents.
    Backed by an in-memory store; serialize() for persistence.
    """

    def __init__(self) -> None:
        self._store: dict[str, Memento] = {}

    def save(self, name: str, memento: Memento) -> str:
        key = memento.snapshot_id()
        self._store[key] = memento
        return key

    def restore(self, snapshot_id: str) -> Memento:
        if snapshot_id not in self._store:
            raise KeyError(f"Snapshot {snapshot_id!r} not found")
        return self._store[snapshot_id]

    def list_snapshots(self) -> list[dict]:
        return [
            {"id": m.snapshot_id(), "created_at": m.created_at().isoformat()}
            for m in self._store.values()
        ]

    def export(self, snapshot_id: str) -> str:
        """Serialize a snapshot for external storage (DB, S3, etc.)."""
        return self.restore(snapshot_id).serialize()

    def import_snapshot(self, serialized: str) -> str:
        m = Memento.deserialize(serialized)
        self._store[m.snapshot_id()] = m
        return m.snapshot_id()


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo() -> None:
    print("=== Memento Demo ===\n")

    agent = ConversationAgent(
        "assistant",
        "You are a helpful assistant. Maintain conversation context.",
    )
    caretaker = ConversationCaretaker()

    # Turn 1
    r1 = agent.chat("My name is Alex and I'm working on a RAG system.")
    print(f"Turn 1: {r1[:100]}")

    # Turn 2
    r2 = agent.chat("What are the main components I need?")
    print(f"Turn 2: {r2[:100]}")

    # Save snapshot after 2 turns
    snap1 = agent.save()
    snap_id = caretaker.save("after-turn-2", snap1)
    print(f"\nSnapshot saved: {snap_id}")
    print(f"Agent state: {agent.turns} turns, {agent.history_length} messages\n")

    # Turn 3 — diverge
    r3 = agent.chat("Actually, let's talk about something completely different.")
    print(f"Turn 3 (diverged): {r3[:100]}")
    print(f"Agent state: {agent.turns} turns, {agent.history_length} messages\n")

    # Restore to the snapshot
    agent.load(caretaker.restore(snap_id))
    print(f"After restore: {agent.turns} turns, {agent.history_length} messages")

    # Continue from the restored state — context is intact
    r4 = agent.chat("What embedding model would you recommend for my RAG system?")
    print(f"Turn 3 (restored): {r4[:150]}\n")

    # Round-trip serialization
    exported = caretaker.export(snap_id)
    imported_id = caretaker.import_snapshot(exported)
    print(f"Serialization round-trip — imported as: {imported_id}")
    print(f"Snapshots: {caretaker.list_snapshots()}")


if __name__ == "__main__":
    demo()
