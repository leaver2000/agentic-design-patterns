"""
Visitor — Agent Evaluator / Inspector
abc: src/abc/visitor.md

Represents operations to be performed on agent outputs without
changing the agents themselves. Run multiple visitors over the same
output structure in one pass.
"""

from __future__ import annotations

import abc
import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Element types — the output structure visitors traverse
# ---------------------------------------------------------------------------

@dataclass
class Message:
    role: str       # "user" | "assistant"
    content: str
    tokens: int = 0


@dataclass
class ToolCall:
    name: str
    input: dict
    output: str
    tokens_used: int = 0


@dataclass
class AgentOutput:
    """The object structure being visited."""
    messages: list[Message] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def accept(self, visitor: Visitor) -> None:
        """Dispatch to the correct visit method for each element type."""
        for msg in self.messages:
            visitor.visit_message(msg)
        for call in self.tool_calls:
            visitor.visit_tool_call(call)
        visitor.visit_agent_result(self)


# ---------------------------------------------------------------------------
# Visitor interface
# ---------------------------------------------------------------------------

class Visitor(abc.ABC):
    """Visitor: declares visit operations for each element type."""

    @abc.abstractmethod
    def visit_agent_result(self, result: AgentOutput) -> None: ...

    @abc.abstractmethod
    def visit_message(self, msg: Message) -> None: ...

    @abc.abstractmethod
    def visit_tool_call(self, call: ToolCall) -> None: ...

    @abc.abstractmethod
    def summary(self) -> dict: ...


# ---------------------------------------------------------------------------
# Concrete Visitors
# ---------------------------------------------------------------------------

class QualityEvaluator(Visitor):
    """
    EvaluatorVisitor: scores output for clarity, completeness, and length.
    Does NOT modify the structure.
    """

    def __init__(self) -> None:
        self._message_scores: list[float] = []
        self._total_words: int = 0

    def visit_message(self, msg: Message) -> None:
        if msg.role != "assistant":
            return
        words = len(msg.content.split())
        self._total_words += words
        # Heuristic: penalize very short or very long responses
        score = min(1.0, words / 50) if words < 50 else min(1.0, 100 / max(words, 100))
        self._message_scores.append(score)

    def visit_tool_call(self, call: ToolCall) -> None:
        # Score tool calls: give full credit if they have non-empty output
        score = 0.8 if call.output.strip() else 0.2
        self._message_scores.append(score)

    def visit_agent_result(self, result: AgentOutput) -> None:
        pass  # Top-level metadata not scored here

    def summary(self) -> dict:
        if not self._message_scores:
            return {"quality_score": 0.0, "verdict": "no_data"}
        avg = sum(self._message_scores) / len(self._message_scores)
        verdict = "pass" if avg >= 0.6 else ("warn" if avg >= 0.4 else "fail")
        return {
            "quality_score": round(avg, 3),
            "verdict": verdict,
            "total_words": self._total_words,
            "evaluated": len(self._message_scores),
        }


class CostVisitor(Visitor):
    """
    CostVisitor: tallies token usage and estimated spend across all elements.
    """

    # Rough Haiku pricing
    INPUT_PRICE = 0.25 / 1_000_000
    OUTPUT_PRICE = 1.25 / 1_000_000

    def __init__(self) -> None:
        self._input_tokens = 0
        self._output_tokens = 0
        self._tool_tokens = 0

    def visit_message(self, msg: Message) -> None:
        if msg.role == "user":
            self._input_tokens += msg.tokens
        else:
            self._output_tokens += msg.tokens

    def visit_tool_call(self, call: ToolCall) -> None:
        self._tool_tokens += call.tokens_used

    def visit_agent_result(self, result: AgentOutput) -> None:
        pass

    def summary(self) -> dict:
        total = self._input_tokens + self._output_tokens + self._tool_tokens
        cost = (
            self._input_tokens * self.INPUT_PRICE
            + self._output_tokens * self.OUTPUT_PRICE
            + self._tool_tokens * self.OUTPUT_PRICE
        )
        return {
            "input_tokens": self._input_tokens,
            "output_tokens": self._output_tokens,
            "tool_tokens": self._tool_tokens,
            "total_tokens": total,
            "estimated_cost_usd": round(cost, 6),
        }


class CitationExtractor(Visitor):
    """
    TransformVisitor: extracts citation-style patterns from all messages.
    Collects [1], [2], ... style inline citations and URL mentions.
    """

    _CITATION_RE = re.compile(r'\[\d+\]')
    _URL_RE = re.compile(r'https?://[^\s<>"]+')

    def __init__(self) -> None:
        self._citations: list[str] = []
        self._urls: list[str] = []

    def visit_message(self, msg: Message) -> None:
        self._citations.extend(self._CITATION_RE.findall(msg.content))
        self._urls.extend(self._URL_RE.findall(msg.content))

    def visit_tool_call(self, call: ToolCall) -> None:
        self._urls.extend(self._URL_RE.findall(call.output))

    def visit_agent_result(self, result: AgentOutput) -> None:
        pass

    def summary(self) -> dict:
        return {
            "inline_citations": sorted(set(self._citations)),
            "urls": sorted(set(self._urls)),
            "citation_count": len(set(self._citations)),
            "url_count": len(set(self._urls)),
        }


class SafetyInspector(Visitor):
    """
    InspectorVisitor: scans for basic safety signals — PII patterns, jailbreak phrases.
    """

    _PII_PATTERNS = [
        re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),              # SSN
        re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),  # Credit card
        re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),  # Email
    ]
    _JAILBREAK_PHRASES = [
        "ignore previous", "disregard your", "you are now", "pretend you are",
    ]

    def __init__(self) -> None:
        self._pii_hits: list[str] = []
        self._jailbreak_hits: list[str] = []

    def visit_message(self, msg: Message) -> None:
        for pattern in self._PII_PATTERNS:
            if pattern.search(msg.content):
                self._pii_hits.append(f"{msg.role}: {pattern.pattern}")
        for phrase in self._JAILBREAK_PHRASES:
            if phrase.lower() in msg.content.lower():
                self._jailbreak_hits.append(phrase)

    def visit_tool_call(self, call: ToolCall) -> None:
        for pattern in self._PII_PATTERNS:
            if pattern.search(call.output):
                self._pii_hits.append(f"tool:{call.name}: {pattern.pattern}")

    def visit_agent_result(self, result: AgentOutput) -> None:
        pass

    def summary(self) -> dict:
        verdict = "pass" if not self._pii_hits and not self._jailbreak_hits else "fail"
        return {
            "verdict": verdict,
            "pii_detected": self._pii_hits,
            "jailbreak_detected": self._jailbreak_hits,
        }


# ---------------------------------------------------------------------------
# Composite visitor — run multiple visitors in a single pass
# ---------------------------------------------------------------------------

class CompositeVisitor(Visitor):
    def __init__(self, visitors: list[Visitor]) -> None:
        self._visitors = visitors

    def visit_agent_result(self, result: AgentOutput) -> None:
        for v in self._visitors:
            v.visit_agent_result(result)

    def visit_message(self, msg: Message) -> None:
        for v in self._visitors:
            v.visit_message(msg)

    def visit_tool_call(self, call: ToolCall) -> None:
        for v in self._visitors:
            v.visit_tool_call(call)

    def summary(self) -> dict:
        return {type(v).__name__: v.summary() for v in self._visitors}


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo() -> None:
    print("=== Visitor Demo ===\n")

    # Build a sample agent output to analyze
    output = AgentOutput(
        messages=[
            Message(
                role="user",
                content="What is RAG? See also https://arxiv.org/abs/2005.11401 [1]",
                tokens=15,
            ),
            Message(
                role="assistant",
                content=(
                    "Retrieval-Augmented Generation (RAG) combines dense retrieval with "
                    "language generation [1]. It was introduced by Lewis et al. (2020) [2]. "
                    "RAG retrieves relevant documents at inference time and conditions the "
                    "model on them, improving factual accuracy without fine-tuning."
                ),
                tokens=72,
            ),
        ],
        tool_calls=[
            ToolCall(
                name="web_search",
                input={"query": "RAG language model"},
                output="Found 3 results: paper on RAG at https://arxiv.org/abs/2005.11401",
                tokens_used=25,
            )
        ],
    )

    # Run all visitors in one pass
    composite = CompositeVisitor([
        QualityEvaluator(),
        CostVisitor(),
        CitationExtractor(),
        SafetyInspector(),
    ])

    output.accept(composite)

    import json
    print("Visitor results (single pass over output structure):")
    print(json.dumps(composite.summary(), indent=2))


if __name__ == "__main__":
    demo()
