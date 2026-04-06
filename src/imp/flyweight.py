"""
Flyweight — Shared Context / Prompt Cache
abc: src/abc/flyweight.md

Separates intrinsic shared state (system prompt, model, tools) from
extrinsic per-call state (task, conversation history).
This maps directly to Anthropic's prompt caching — the intrinsic state
is the cacheable prefix.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field

import anthropic


# ---------------------------------------------------------------------------
# Intrinsic state (shared, immutable after construction)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentIntrinsicState:
    """
    The shared configuration that is identical across many agent invocations.
    Frozen: immutable after construction. Safe for concurrent use.
    """
    system_prompt: str
    model: str
    max_tokens: int = 512
    tools_json: str = "[]"  # JSON-serialized tool list (frozen requires hashable)

    def flyweight_key(self) -> str:
        payload = f"{self.model}|{self.system_prompt}|{self.max_tokens}|{self.tools_json}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Flyweight — the shared agent instance
# ---------------------------------------------------------------------------

class AgentFlyweight:
    """
    ConcreteFlyweight: stores intrinsic state; receives extrinsic state at call time.
    Must NOT store extrinsic state between calls.
    """

    def __init__(self, intrinsic: AgentIntrinsicState) -> None:
        self._intrinsic = intrinsic
        self._client = anthropic.Anthropic()

    def intrinsic_state(self) -> dict:
        return {
            "system_prompt": self._intrinsic.system_prompt[:80],
            "model": self._intrinsic.model,
            "max_tokens": self._intrinsic.max_tokens,
        }

    def flyweight_key(self) -> str:
        return self._intrinsic.flyweight_key()

    def run(self, task: str, extrinsic: dict | None = None) -> str:
        """
        Execute using intrinsic + extrinsic state combined.
        Extrinsic state is NEVER stored on this instance.
        """
        ext = extrinsic or {}

        # Inject extrinsic context into the user message
        context_prefix = ""
        if ext:
            context_prefix = (
                "Context for this call:\n"
                + "\n".join(f"  {k}: {v}" for k, v in ext.items())
                + "\n\n"
            )

        tools = json.loads(self._intrinsic.tools_json)
        kwargs: dict = {
            "model": self._intrinsic.model,
            "max_tokens": self._intrinsic.max_tokens,
            "system": self._intrinsic.system_prompt,
            "messages": [{"role": "user", "content": context_prefix + task}],
        }
        if tools:
            kwargs["tools"] = tools

        msg = self._client.messages.create(**kwargs)
        return msg.content[0].text


# ---------------------------------------------------------------------------
# Flyweight Factory — ensures sharing; one instance per intrinsic config
# ---------------------------------------------------------------------------

class AgentFlyweightFactory:
    """
    Creates and caches AgentFlyweight instances.
    Returns the SAME instance for identical intrinsic configurations.
    """

    def __init__(self) -> None:
        self._pool: dict[str, AgentFlyweight] = {}
        self._lock = threading.Lock()

    def get_flyweight(self, intrinsic: AgentIntrinsicState) -> AgentFlyweight:
        key = intrinsic.flyweight_key()
        with self._lock:
            if key not in self._pool:
                self._pool[key] = AgentFlyweight(intrinsic)
            return self._pool[key]

    def pool_size(self) -> int:
        return len(self._pool)

    def pool_keys(self) -> list[str]:
        return list(self._pool.keys())


# ---------------------------------------------------------------------------
# Pre-built flyweights (module-level factory)
# ---------------------------------------------------------------------------

_factory = AgentFlyweightFactory()

_SUMMARIZER_INTRINSIC = AgentIntrinsicState(
    system_prompt=(
        "You are a document summarization agent. "
        "Produce a 2-3 sentence summary. Be concise."
    ),
    model="claude-haiku-4-5-20251001",
    max_tokens=200,
)

_CLASSIFIER_INTRINSIC = AgentIntrinsicState(
    system_prompt=(
        "You are a text classification agent. "
        "Classify the input into: technical | creative | analytical | other. "
        "Respond with the category name only."
    ),
    model="claude-haiku-4-5-20251001",
    max_tokens=10,
)


def get_summarizer() -> AgentFlyweight:
    return _factory.get_flyweight(_SUMMARIZER_INTRINSIC)


def get_classifier() -> AgentFlyweight:
    return _factory.get_flyweight(_CLASSIFIER_INTRINSIC)


def get_factory() -> AgentFlyweightFactory:
    return _factory


# ---------------------------------------------------------------------------
# Demo — simulate a document processing pipeline
# ---------------------------------------------------------------------------

def demo() -> None:
    print("=== Flyweight Demo ===\n")

    factory = get_factory()
    summarizer = get_summarizer()
    classifier = get_classifier()

    # Multiple calls reuse the same flyweight instance
    s1 = get_summarizer()
    s2 = get_summarizer()
    assert s1 is s2, "Flyweight violated: two different instances for same config"
    print(f"Summarizer flyweight key: {summarizer.flyweight_key()}")
    print(f"Classifier flyweight key: {classifier.flyweight_key()}")
    print(f"Pool size: {factory.pool_size()} (2 unique configs)\n")

    # Simulate processing 3 documents with per-doc extrinsic state
    documents = [
        {"id": "doc-1", "text": "Transformer models use self-attention mechanisms to process sequences in parallel."},
        {"id": "doc-2", "text": "The Eiffel Tower was built in 1889 for the World's Fair in Paris."},
        {"id": "doc-3", "text": "Gradient descent minimizes a loss function by iteratively adjusting parameters."},
    ]

    for doc in documents:
        # Extrinsic state: per-document context (never stored on flyweight)
        extrinsic = {"document_id": doc["id"]}

        summary = summarizer.run(doc["text"], extrinsic)
        category = classifier.run(doc["text"])

        print(f"[{doc['id']}]")
        print(f"  Category: {category.strip()}")
        print(f"  Summary:  {summary.strip()[:120]}")
        print()

    print(f"Pool size after {len(documents)} docs: {factory.pool_size()} (unchanged — flyweights are shared)")


if __name__ == "__main__":
    demo()
