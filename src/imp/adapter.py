"""
Adapter — Tool Adapter
abc: src/abc/adapter.md

Converts the interface of an external service or legacy API into the
uniform tool interface that agents expect.
"""

from __future__ import annotations

import abc
import json
import urllib.request
import urllib.parse
from dataclasses import dataclass
from typing import Any

import anthropic


# ---------------------------------------------------------------------------
# Target interface — what agents expect
# ---------------------------------------------------------------------------

@dataclass
class ToolResult:
    content: str
    success: bool
    error: str | None = None


class AgentTool(abc.ABC):
    """Target interface: the standard contract every tool must satisfy."""

    @abc.abstractmethod
    def call(self, name: str, args: dict) -> ToolResult:
        """Invoke the tool with the given arguments."""
        ...

    @abc.abstractmethod
    def tool_schema(self) -> dict:
        """Return JSON schema describing this tool to agents."""
        ...

    @abc.abstractmethod
    def _translate(self, args: dict) -> Any:
        """Convert from agent-facing args to the adaptee's native format."""
        ...

    @abc.abstractmethod
    def _parse_response(self, raw: Any) -> ToolResult:
        """Convert the adaptee's response to ToolResult."""
        ...


# ---------------------------------------------------------------------------
# Adaptee 1: A hypothetical internal search service with a non-standard API
# ---------------------------------------------------------------------------

class LegacySearchService:
    """Existing service with a non-standard interface (the Adaptee)."""

    def query(self, q: str, max_results: int = 5) -> list[dict]:
        """Returns list of {title, snippet, url} — different from what agents expect."""
        # Simulated results (in production this would call an internal API)
        return [
            {
                "title": f"Result for '{q}' #{i+1}",
                "snippet": f"This is a relevant snippet about {q}.",
                "url": f"https://example.com/result-{i+1}",
            }
            for i in range(min(max_results, 3))
        ]


# ---------------------------------------------------------------------------
# Adapter 1: Wraps LegacySearchService into AgentTool
# ---------------------------------------------------------------------------

class SearchToolAdapter(AgentTool):
    """Adapts LegacySearchService to the AgentTool interface."""

    def __init__(self, adaptee: LegacySearchService | None = None) -> None:
        self._adaptee = adaptee or LegacySearchService()

    def tool_schema(self) -> dict:
        return {
            "name": "search",
            "description": "Search for information on a topic.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "max_results": {"type": "integer", "default": 3},
                },
                "required": ["query"],
            },
        }

    def call(self, name: str, args: dict) -> ToolResult:
        try:
            native_args = self._translate(args)
            raw = self._adaptee.query(**native_args)
            return self._parse_response(raw)
        except Exception as exc:
            return ToolResult(content="", success=False, error=str(exc))

    def _translate(self, args: dict) -> dict:
        """Agent uses 'query' + 'max_results'; adaptee uses 'q' + 'max_results'."""
        return {
            "q": args["query"],
            "max_results": args.get("max_results", 3),
        }

    def _parse_response(self, raw: list[dict]) -> ToolResult:
        """Convert list of result dicts to a plain-text ToolResult."""
        if not raw:
            return ToolResult(content="No results found.", success=True)
        lines = [f"{r['title']}\n  {r['snippet']}\n  {r['url']}" for r in raw]
        return ToolResult(content="\n\n".join(lines), success=True)


# ---------------------------------------------------------------------------
# Adaptee 2: A math evaluation service with its own calling convention
# ---------------------------------------------------------------------------

class MathEvalService:
    """Evaluates simple arithmetic expressions — different interface again."""

    def evaluate(self, expression: str) -> float:
        # Use Python eval in a restricted namespace (demo only)
        try:
            result = eval(expression, {"__builtins__": {}}, {})  # noqa: S307
            return float(result)
        except Exception as exc:
            raise ValueError(f"Cannot evaluate {expression!r}: {exc}") from exc


class CalculatorToolAdapter(AgentTool):
    """Adapts MathEvalService to AgentTool interface."""

    def __init__(self, adaptee: MathEvalService | None = None) -> None:
        self._adaptee = adaptee or MathEvalService()

    def tool_schema(self) -> dict:
        return {
            "name": "calculator",
            "description": "Evaluate a mathematical expression and return the result.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Arithmetic expression, e.g. '(3 + 4) * 2'",
                    }
                },
                "required": ["expression"],
            },
        }

    def call(self, name: str, args: dict) -> ToolResult:
        try:
            expr = self._translate(args)
            raw = self._adaptee.evaluate(expr)
            return self._parse_response(raw)
        except Exception as exc:
            return ToolResult(content="", success=False, error=str(exc))

    def _translate(self, args: dict) -> str:
        return args["expression"]

    def _parse_response(self, raw: float) -> ToolResult:
        return ToolResult(content=str(raw), success=True)


# ---------------------------------------------------------------------------
# Agent that uses tools only through the AgentTool interface
# ---------------------------------------------------------------------------

class ToolUsingAgent:
    """Client — interacts with tools only through the AgentTool interface."""

    def __init__(self, tools: list[AgentTool]) -> None:
        self._tools = {t.tool_schema()["name"]: t for t in tools}
        self._client = anthropic.Anthropic()

    def run(self, task: str) -> str:
        schemas = [t.tool_schema() for t in self._tools.values()]
        messages: list[dict] = [{"role": "user", "content": task}]

        while True:
            response = self._client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                tools=schemas,  # type: ignore[arg-type]
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                # Collect all text blocks
                return " ".join(
                    b.text for b in response.content if hasattr(b, "text")
                )

            if response.stop_reason == "tool_use":
                # Execute tool calls through the adapter interface
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool = self._tools.get(block.name)
                        if tool:
                            result = tool.call(block.name, block.input)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result.content if result.success
                                           else f"Error: {result.error}",
                            })

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                break

        return ""


def demo() -> None:
    print("=== Adapter Demo ===\n")

    search = SearchToolAdapter()
    calc = CalculatorToolAdapter()

    # Direct adapter calls (bypassing agent)
    result = search.call("search", {"query": "multi-agent orchestration"})
    print(f"SearchAdapter direct call:\n{result.content}\n")

    result2 = calc.call("calculator", {"expression": "(3 + 4) * 2"})
    print(f"CalculatorAdapter: (3 + 4) * 2 = {result2.content}\n")

    # Agent using both tools through the uniform interface
    agent = ToolUsingAgent([search, calc])
    answer = agent.run("Search for 'agentic AI' and also calculate 17 * 23.")
    print(f"Agent answer:\n{answer}")


if __name__ == "__main__":
    demo()
