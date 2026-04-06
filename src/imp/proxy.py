"""
Proxy — Agent Proxy
abc: src/abc/proxy.md

Provides a surrogate for another agent. Demonstrated variants:
  - CachingProxy    — memoizes results for identical inputs
  - RateLimitProxy  — enforces per-agent call budget
  - LoggingProxy    — records all interactions
"""

from __future__ import annotations

import abc
import hashlib
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic


# ---------------------------------------------------------------------------
# Subject interface — shared by RealSubject and all Proxies
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    content: str
    agent_name: str
    metadata: dict = field(default_factory=dict)


class AgentSubject(abc.ABC):
    """Subject: the common interface. Clients use only this."""

    @abc.abstractmethod
    def run(self, task: str, context: dict | None = None) -> AgentResult: ...

    @property
    @abc.abstractmethod
    def name(self) -> str: ...


# ---------------------------------------------------------------------------
# Real Subject
# ---------------------------------------------------------------------------

class ClaudeAgent(AgentSubject):
    def __init__(self, name: str, system: str, model: str = "claude-haiku-4-5-20251001") -> None:
        self._name = name
        self._system = system
        self._model = model
        self._client = anthropic.Anthropic()

    @property
    def name(self) -> str:
        return self._name

    def run(self, task: str, context: dict | None = None) -> AgentResult:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=400,
            system=self._system,
            messages=[{"role": "user", "content": task}],
        )
        return AgentResult(content=msg.content[0].text, agent_name=self._name)


# ---------------------------------------------------------------------------
# Base Proxy
# ---------------------------------------------------------------------------

class AgentProxy(AgentSubject, abc.ABC):
    """Base Proxy: wraps a RealSubject; implements the same Subject interface."""

    def __init__(self, real_subject: AgentSubject) -> None:
        self._subject = real_subject

    def real_subject(self) -> AgentSubject:
        return self._subject

    @property
    def name(self) -> str:
        return self._subject.name

    @property
    @abc.abstractmethod
    def proxy_type(self) -> str: ...


# ---------------------------------------------------------------------------
# Caching Proxy
# ---------------------------------------------------------------------------

class CachingProxy(AgentProxy):
    """Memoizes results for identical (task, context) inputs."""

    proxy_type = "caching"

    def __init__(self, real_subject: AgentSubject, max_entries: int = 100) -> None:
        super().__init__(real_subject)
        self._cache: dict[str, AgentResult] = {}
        self._max_entries = max_entries
        self._hits = 0
        self._misses = 0

    def _cache_key(self, task: str, context: dict | None) -> str:
        payload = f"{task}|{sorted((context or {}).items())}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def run(self, task: str, context: dict | None = None) -> AgentResult:
        key = self._cache_key(task, context)
        if key in self._cache:
            self._hits += 1
            result = self._cache[key]
            result.metadata["cache"] = "hit"
            return result

        self._misses += 1
        result = self._subject.run(task, context)
        if len(self._cache) < self._max_entries:
            self._cache[key] = result
        result.metadata["cache"] = "miss"
        return result

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total else 0.0,
            "entries": len(self._cache),
        }


# ---------------------------------------------------------------------------
# Rate Limit Proxy
# ---------------------------------------------------------------------------

class RateLimitProxy(AgentProxy):
    """Enforces a maximum number of calls per time window."""

    proxy_type = "rate_limit"

    def __init__(
        self,
        real_subject: AgentSubject,
        max_calls: int = 10,
        window_seconds: float = 60.0,
    ) -> None:
        super().__init__(real_subject)
        self._max_calls = max_calls
        self._window = window_seconds
        self._calls: list[float] = []
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        cutoff = now - self._window
        self._calls = [t for t in self._calls if t > cutoff]

    def run(self, task: str, context: dict | None = None) -> AgentResult:
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            if len(self._calls) >= self._max_calls:
                oldest = self._calls[0]
                wait = self._window - (now - oldest)
                raise RuntimeError(
                    f"Rate limit exceeded: {self._max_calls} calls/{self._window}s. "
                    f"Retry in {wait:.1f}s."
                )
            self._calls.append(now)

        return self._subject.run(task, context)

    @property
    def remaining_calls(self) -> int:
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            return max(0, self._max_calls - len(self._calls))


# ---------------------------------------------------------------------------
# Logging Proxy
# ---------------------------------------------------------------------------

class LoggingProxy(AgentProxy):
    """Records all interactions for observability."""

    proxy_type = "logging"

    @dataclass
    class LogEntry:
        task: str
        response: str
        latency_s: float
        error: str | None = None

    def __init__(self, real_subject: AgentSubject) -> None:
        super().__init__(real_subject)
        self._log: list[LoggingProxy.LogEntry] = []

    def run(self, task: str, context: dict | None = None) -> AgentResult:
        start = time.perf_counter()
        try:
            result = self._subject.run(task, context)
            elapsed = time.perf_counter() - start
            self._log.append(self.LogEntry(
                task=task[:100],
                response=result.content[:100],
                latency_s=round(elapsed, 3),
            ))
            result.metadata["logged"] = True
            return result
        except Exception as exc:
            elapsed = time.perf_counter() - start
            self._log.append(self.LogEntry(
                task=task[:100],
                response="",
                latency_s=round(elapsed, 3),
                error=str(exc),
            ))
            raise

    @property
    def log(self) -> list[LogEntry]:
        return list(self._log)

    def summary(self) -> dict:
        if not self._log:
            return {"total": 0}
        latencies = [e.latency_s for e in self._log]
        errors = [e for e in self._log if e.error]
        return {
            "total": len(self._log),
            "errors": len(errors),
            "avg_latency_s": round(sum(latencies) / len(latencies), 3),
            "max_latency_s": max(latencies),
        }


def demo() -> None:
    print("=== Proxy Demo ===\n")

    base = ClaudeAgent(
        "base-agent",
        "You are a helpful assistant. Answer concisely.",
    )

    # Layer: LoggingProxy(CachingProxy(RateLimitProxy(base)))
    rate_limited = RateLimitProxy(base, max_calls=20, window_seconds=60)
    cached = CachingProxy(rate_limited, max_entries=50)
    logged = LoggingProxy(cached)

    task = "What is attention in transformer models?"

    print("--- First call (cache miss) ---")
    r1 = logged.run(task)
    print(f"Answer: {r1.content[:100]}...")
    print(f"Metadata: {r1.metadata}\n")

    print("--- Second call (cache hit) ---")
    r2 = logged.run(task)
    print(f"Answer: {r2.content[:100]}...")
    print(f"Metadata: {r2.metadata}\n")

    print(f"Cache stats: {cached.stats}")
    print(f"Log summary: {logged.summary()}")
    print(f"Remaining rate-limit calls: {rate_limited.remaining_calls}")


if __name__ == "__main__":
    demo()
