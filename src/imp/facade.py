"""
Facade — Orchestrator Facade
abc: src/abc/facade.md

Provides a single entry point to a complex multi-agent subsystem.
Callers see one method; the internal pipeline is hidden.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field

import anthropic


# ---------------------------------------------------------------------------
# Internal subsystem agents (not exposed to callers)
# ---------------------------------------------------------------------------

@dataclass
class _AgentResult:
    content: str
    agent: str


class _SubsystemAgent(abc.ABC):
    @abc.abstractmethod
    def run(self, input_text: str) -> _AgentResult: ...


class _Claude(_SubsystemAgent):
    def __init__(self, name: str, system: str, model: str = "claude-haiku-4-5-20251001") -> None:
        self._name = name
        self._system = system
        self._model = model
        self._client = anthropic.Anthropic()

    def run(self, input_text: str) -> _AgentResult:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=400,
            system=self._system,
            messages=[{"role": "user", "content": input_text}],
        )
        return _AgentResult(content=msg.content[0].text, agent=self._name)

    def health(self) -> bool:
        try:
            self._client.messages.create(
                model=self._model,
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Response type returned to callers
# ---------------------------------------------------------------------------

@dataclass
class AnswerResponse:
    answer: str
    sources_used: bool
    quality_verdict: str
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------

class ResearchFacade:
    """
    Facade: exposes a single `answer(question)` method.

    Internally coordinates:
      1. Planner   — decomposes the question into search queries
      2. Retriever — simulates document retrieval
      3. Synthesizer — produces a grounded answer
      4. Critic    — quality-checks the answer
    """

    def __init__(self) -> None:
        self._planner = _Claude(
            "planner",
            "You are a query planning agent. Given a question, output 2-3 targeted "
            "search queries as a numbered list. Nothing else.",
        )
        self._retriever = _Claude(
            "retriever",
            "You are a retrieval agent. Given search queries, simulate finding relevant "
            "passages and return them as bulleted excerpts.",
        )
        self._synthesizer = _Claude(
            "synthesizer",
            "You are a synthesis agent. Given a question and retrieved passages, write "
            "a clear, grounded answer. Cite each claim with [passage N].",
            model="claude-sonnet-4-6",
        )
        self._critic = _Claude(
            "critic",
            "You are a quality critic. Respond with JSON only: "
            "{\"verdict\": \"pass\"|\"warn\"|\"fail\", \"score\": float, \"note\": str}",
        )

    # Public interface — the only method callers need
    def answer(self, question: str) -> AnswerResponse:
        """Single entry point: question in, answer out."""
        # 1. Plan
        queries_result = self._planner.run(question)

        # 2. Retrieve
        retrieve_prompt = f"Queries:\n{queries_result.content}\n\nFind relevant passages."
        passages_result = self._retriever.run(retrieve_prompt)

        # 3. Synthesize
        synth_prompt = (
            f"Question: {question}\n\n"
            f"Passages:\n{passages_result.content}\n\n"
            "Write a grounded answer."
        )
        answer_result = self._synthesizer.run(synth_prompt)

        # 4. Critique
        critique_result = self._critic.run(
            f"Question: {question}\nAnswer:\n{answer_result.content}"
        )

        verdict = self._extract_verdict(critique_result.content)
        return AnswerResponse(
            answer=answer_result.content,
            sources_used=True,
            quality_verdict=verdict,
            metadata={
                "queries": queries_result.content[:200],
                "critique": critique_result.content[:200],
            },
        )

    def health_check(self) -> dict:
        """Report readiness of each internal agent."""
        agents = [self._planner, self._retriever, self._synthesizer, self._critic]
        return {a._name: a.health() for a in agents}  # type: ignore[attr-defined]

    def subsystem_agents(self) -> list[_SubsystemAgent]:
        return [self._planner, self._retriever, self._synthesizer, self._critic]

    @staticmethod
    def _extract_verdict(critique: str) -> str:
        import json, re  # noqa: E401
        try:
            match = re.search(r'\{.*\}', critique, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return data.get("verdict", "unknown")
        except Exception:
            pass
        return "unknown"


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo() -> None:
    print("=== Facade Demo ===\n")

    facade = ResearchFacade()

    question = "What are the main benefits of using a vector database for RAG?"
    print(f"Question: {question}\n")

    response = facade.answer(question)
    print(f"Answer:\n{response.answer}\n")
    print(f"Quality verdict: {response.quality_verdict}")
    print(f"Queries used: {response.metadata['queries'][:100]}...")


if __name__ == "__main__":
    demo()
