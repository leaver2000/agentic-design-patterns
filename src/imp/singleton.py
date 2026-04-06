"""
Singleton — Registry / Shared Service Agent
abc: src/abc/singleton.md

Ensures shared infrastructure (tool registry, rate-limit tracker,
embedding cache) has exactly one instance per process.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable


# ---------------------------------------------------------------------------
# Singleton base — thread-safe double-checked locking
# ---------------------------------------------------------------------------

class _SingletonMeta(type):
    _instances: dict[type, object] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):  # type: ignore[override]
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

    def reset(cls) -> None:  # type: ignore[misc]
        """For testing only — clears the cached instance."""
        with cls._lock:
            cls._instances.pop(cls, None)


# ---------------------------------------------------------------------------
# Concrete Singleton 1: Tool Registry
# ---------------------------------------------------------------------------

@dataclass
class ToolDefinition:
    name: str
    description: str
    handler: Callable[[dict], str]
    input_schema: dict = field(default_factory=dict)


class ToolRegistry(metaclass=_SingletonMeta):
    """
    Central registry for all tools available to agents in this session.
    Thread-safe. One instance per process.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._lock = threading.RLock()

    def register(self, tool: ToolDefinition) -> None:
        with self._lock:
            if tool.name in self._tools:
                raise KeyError(f"Tool {tool.name!r} already registered")
            self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition:
        with self._lock:
            if name not in self._tools:
                raise KeyError(f"Tool {name!r} not found in registry")
            return self._tools[name]

    def call(self, name: str, args: dict) -> str:
        return self.get(name).handler(args)

    def list_tools(self) -> list[str]:
        with self._lock:
            return list(self._tools.keys())

    def to_anthropic_schema(self) -> list[dict]:
        """Return tools in Anthropic API format."""
        with self._lock:
            return [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema or {
                        "type": "object",
                        "properties": {},
                    },
                }
                for t in self._tools.values()
            ]


# ---------------------------------------------------------------------------
# Concrete Singleton 2: Rate Limit Tracker
# ---------------------------------------------------------------------------

@dataclass
class _BucketState:
    tokens: float
    last_refill: float


class RateLimitTracker(metaclass=_SingletonMeta):
    """
    Token-bucket rate limiter shared across all agents in the session.
    Prevents any single agent from monopolizing API quota.
    """

    DEFAULT_CAPACITY = 100_000   # tokens per minute
    DEFAULT_REFILL_RATE = 100_000 / 60  # tokens per second

    def __init__(self) -> None:
        self._buckets: dict[str, _BucketState] = {}
        self._lock = threading.RLock()

    def _get_or_create_bucket(self, agent_id: str) -> _BucketState:
        if agent_id not in self._buckets:
            self._buckets[agent_id] = _BucketState(
                tokens=self.DEFAULT_CAPACITY,
                last_refill=time.monotonic(),
            )
        return self._buckets[agent_id]

    def _refill(self, bucket: _BucketState) -> None:
        now = time.monotonic()
        elapsed = now - bucket.last_refill
        bucket.tokens = min(
            self.DEFAULT_CAPACITY,
            bucket.tokens + elapsed * self.DEFAULT_REFILL_RATE,
        )
        bucket.last_refill = now

    def consume(self, agent_id: str, tokens: int) -> bool:
        """
        Attempt to consume `tokens` from the agent's bucket.
        Returns True if allowed, False if rate-limited.
        """
        with self._lock:
            bucket = self._get_or_create_bucket(agent_id)
            self._refill(bucket)
            if bucket.tokens >= tokens:
                bucket.tokens -= tokens
                return True
            return False

    def available(self, agent_id: str) -> float:
        with self._lock:
            bucket = self._get_or_create_bucket(agent_id)
            self._refill(bucket)
            return bucket.tokens

    def reset_agent(self, agent_id: str) -> None:
        with self._lock:
            self._buckets.pop(agent_id, None)


# ---------------------------------------------------------------------------
# Module-level accessors (preferred over direct instantiation)
# ---------------------------------------------------------------------------

def tool_registry() -> ToolRegistry:
    return ToolRegistry()


def rate_limiter() -> RateLimitTracker:
    return RateLimitTracker()


# ---------------------------------------------------------------------------
# Pre-register built-in tools
# ---------------------------------------------------------------------------

def _setup_default_tools() -> None:
    reg = tool_registry()
    if "echo" not in reg.list_tools():
        reg.register(ToolDefinition(
            name="echo",
            description="Echo the input back. Useful for testing.",
            handler=lambda args: args.get("text", ""),
            input_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        ))
        reg.register(ToolDefinition(
            name="word_count",
            description="Count the number of words in a string.",
            handler=lambda args: str(len(args.get("text", "").split())),
            input_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        ))


_setup_default_tools()


def demo() -> None:
    print("=== Singleton Demo ===\n")

    # Tool Registry singleton
    reg1 = tool_registry()
    reg2 = tool_registry()
    assert reg1 is reg2, "Singleton violated: two different ToolRegistry instances"
    print(f"ToolRegistry is singleton: {reg1 is reg2}")
    print(f"Registered tools: {reg1.list_tools()}")
    print(f"echo('hello') → {reg1.call('echo', {'text': 'hello'})}")
    print(f"word_count('the quick brown fox') → {reg1.call('word_count', {'text': 'the quick brown fox'})}\n")

    # Rate Limiter singleton
    rl1 = rate_limiter()
    rl2 = rate_limiter()
    assert rl1 is rl2, "Singleton violated: two different RateLimitTracker instances"
    print(f"RateLimitTracker is singleton: {rl1 is rl2}")

    allowed = rl1.consume("agent-1", 1000)
    print(f"agent-1 consumes 1000 tokens: {'allowed' if allowed else 'rate-limited'}")
    print(f"agent-1 remaining tokens: {rl1.available('agent-1'):.0f}")


if __name__ == "__main__":
    demo()
