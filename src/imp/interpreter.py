"""
Interpreter — Prompt DSL
abc: src/abc/interpreter.md

Defines a mini-language for agent workflows and an interpreter that
executes sentences in that language. Each DSL node maps to an agent call.

DSL grammar (simplified):
  Program   := Step*
  Step      := RESEARCH <query>
             | SUMMARIZE <text>
             | CLASSIFY <text> AS <label1> | <label2> | ...
             | TRANSFORM <text> TO <instruction>
             | SEQ ( Step, Step, ... )
"""

from __future__ import annotations

import abc
import re
from dataclasses import dataclass, field
from typing import Any

import anthropic


# ---------------------------------------------------------------------------
# Context — global state threaded through the AST
# ---------------------------------------------------------------------------

@dataclass
class InterpreterContext:
    """Carries global state during an interpreter pass."""
    variables: dict[str, str] = field(default_factory=dict)
    history: list[str] = field(default_factory=list)
    _client: anthropic.Anthropic = field(
        default_factory=anthropic.Anthropic, repr=False
    )

    def set(self, key: str, value: str) -> None:
        self.variables[key] = value
        self.history.append(f"SET {key} = {value[:50]}")

    def get(self, key: str) -> str:
        return self.variables.get(key, f"<undefined:{key}>")

    def call_claude(self, system: str, user: str, max_tokens: int = 300) -> str:
        msg = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text


# ---------------------------------------------------------------------------
# AbstractExpression
# ---------------------------------------------------------------------------

class Expression(abc.ABC):
    """AbstractExpression: every AST node implements interpret()."""

    @abc.abstractmethod
    def interpret(self, ctx: InterpreterContext) -> Any:
        """Evaluate this node given the current context."""
        ...

    @abc.abstractmethod
    def to_instruction(self) -> str:
        """Serialize back to the DSL string."""
        ...


# ---------------------------------------------------------------------------
# Terminal Expressions (atomic agent actions)
# ---------------------------------------------------------------------------

class ResearchExpression(Expression):
    """Terminal: calls a research agent for the given query."""

    def __init__(self, query: str, output_var: str = "result") -> None:
        self._query = query
        self._output_var = output_var

    def interpret(self, ctx: InterpreterContext) -> str:
        result = ctx.call_claude(
            system="You are a research agent. Answer questions concisely with facts.",
            user=self._query,
            max_tokens=400,
        )
        ctx.set(self._output_var, result)
        return result

    def to_instruction(self) -> str:
        return f"RESEARCH {self._query!r} -> {self._output_var}"


class SummarizeExpression(Expression):
    """Terminal: summarizes the given text or variable reference."""

    def __init__(self, text_or_var: str, output_var: str = "summary") -> None:
        self._ref = text_or_var
        self._output_var = output_var

    def interpret(self, ctx: InterpreterContext) -> str:
        text = ctx.get(self._ref) if self._ref.startswith("$") else self._ref
        result = ctx.call_claude(
            system="You are a summarization agent. Summarize in 1-2 sentences.",
            user=text,
            max_tokens=150,
        )
        ctx.set(self._output_var, result)
        return result

    def to_instruction(self) -> str:
        return f"SUMMARIZE {self._ref!r} -> {self._output_var}"


class ClassifyExpression(Expression):
    """Terminal: classifies text into one of the given labels."""

    def __init__(self, text_or_var: str, labels: list[str], output_var: str = "category") -> None:
        self._ref = text_or_var
        self._labels = labels
        self._output_var = output_var

    def interpret(self, ctx: InterpreterContext) -> str:
        text = ctx.get(self._ref) if self._ref.startswith("$") else self._ref
        label_list = " | ".join(self._labels)
        result = ctx.call_claude(
            system=f"Classify the text as exactly one of: {label_list}. One word only.",
            user=text,
            max_tokens=10,
        )
        label = result.strip().lower()
        # Normalize to closest known label
        matched = next((l for l in self._labels if l.lower() in label), self._labels[-1])
        ctx.set(self._output_var, matched)
        return matched

    def to_instruction(self) -> str:
        return f"CLASSIFY {self._ref!r} AS {' | '.join(self._labels)} -> {self._output_var}"


class TransformExpression(Expression):
    """Terminal: transforms text according to an instruction."""

    def __init__(self, text_or_var: str, instruction: str, output_var: str = "transformed") -> None:
        self._ref = text_or_var
        self._instruction = instruction
        self._output_var = output_var

    def interpret(self, ctx: InterpreterContext) -> str:
        text = ctx.get(self._ref) if self._ref.startswith("$") else self._ref
        result = ctx.call_claude(
            system=f"You are a transformation agent. {self._instruction}",
            user=text,
            max_tokens=400,
        )
        ctx.set(self._output_var, result)
        return result

    def to_instruction(self) -> str:
        return f"TRANSFORM {self._ref!r} TO {self._instruction!r} -> {self._output_var}"


# ---------------------------------------------------------------------------
# Non-terminal Expression — sequential composition
# ---------------------------------------------------------------------------

class SequenceExpression(Expression):
    """
    NonterminalExpression: executes child expressions in order.
    The output of each step is available in the context for subsequent steps.
    """

    def __init__(self, steps: list[Expression]) -> None:
        self._steps = steps

    def interpret(self, ctx: InterpreterContext) -> list[Any]:
        return [step.interpret(ctx) for step in self._steps]

    def to_instruction(self) -> str:
        inner = ", ".join(s.to_instruction() for s in self._steps)
        return f"SEQ({inner})"


# ---------------------------------------------------------------------------
# Simple DSL parser
# ---------------------------------------------------------------------------

class WorkflowParser:
    """
    Client helper: parses a workflow definition string into an AST.

    Supported syntax:
      RESEARCH "query" -> var
      SUMMARIZE $var -> var
      CLASSIFY $var AS label1 | label2 -> var
      TRANSFORM $var TO "instruction" -> var
    """

    _RESEARCH_RE = re.compile(r'RESEARCH\s+"([^"]+)"\s*(?:->\s*(\w+))?', re.I)
    _SUMMARIZE_RE = re.compile(r'SUMMARIZE\s+(\$?\w+|"[^"]+")\s*(?:->\s*(\w+))?', re.I)
    _CLASSIFY_RE = re.compile(r'CLASSIFY\s+(\$?\w+)\s+AS\s+([\w\s|]+)\s*(?:->\s*(\w+))?', re.I)
    _TRANSFORM_RE = re.compile(r'TRANSFORM\s+(\$?\w+)\s+TO\s+"([^"]+)"\s*(?:->\s*(\w+))?', re.I)

    def parse(self, program: str) -> Expression:
        lines = [l.strip() for l in program.strip().splitlines() if l.strip()]
        steps = [self._parse_line(line) for line in lines]
        return SequenceExpression(steps) if len(steps) > 1 else steps[0]

    def _parse_line(self, line: str) -> Expression:
        m = self._RESEARCH_RE.match(line)
        if m:
            return ResearchExpression(m.group(1), m.group(2) or "result")

        m = self._SUMMARIZE_RE.match(line)
        if m:
            ref = m.group(1).strip('"')
            return SummarizeExpression(ref, m.group(2) or "summary")

        m = self._CLASSIFY_RE.match(line)
        if m:
            labels = [l.strip() for l in m.group(2).split("|")]
            return ClassifyExpression(m.group(1), labels, m.group(3) or "category")

        m = self._TRANSFORM_RE.match(line)
        if m:
            return TransformExpression(m.group(1), m.group(2), m.group(3) or "transformed")

        raise SyntaxError(f"Cannot parse DSL line: {line!r}")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo() -> None:
    print("=== Interpreter Demo ===\n")

    program = '''
RESEARCH "What are the main benefits of vector databases for AI?" -> research
SUMMARIZE $research -> summary
CLASSIFY $summary AS technical | business | general -> category
TRANSFORM $summary TO "rewrite as a tweet under 280 characters" -> tweet
'''

    parser = WorkflowParser()
    ast = parser.parse(program.strip())
    print(f"AST:\n  {ast.to_instruction()}\n")

    ctx = InterpreterContext()
    results = ast.interpret(ctx)

    print("Execution trace:")
    for entry in ctx.history:
        print(f"  {entry}")
    print()
    print(f"Final variables:")
    for k, v in ctx.variables.items():
        print(f"  {k}: {v[:100]}")


if __name__ == "__main__":
    demo()
