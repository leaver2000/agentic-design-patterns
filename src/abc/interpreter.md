---
name: interpreter
abstract: true
pattern: Interpreter
category: behavioral
extends: []
description: Define a representation for a structured instruction grammar and an agent that interprets sentences in that language.
---

## Intent
Given a structured instruction language, define a representation for its grammar along with an agent that uses that representation to interpret and execute instructions in the language.

## Participants
- **AbstractExpression** *(this)* — declares an `interpret()` operation common to all nodes
- **TerminalExpression** *(implementor)* — implements `interpret()` for terminal symbols (atomic agent actions)
- **NonterminalExpression** *(implementor)* — implements `interpret()` for grammar rules; holds child expressions
- **Context** — contains information global to the interpreter (current agent state, variables)
- **Client** — builds the abstract syntax tree (AST) from sentences in the language and invokes `interpret()`

## Abstract Interface
Implementors MUST define:
- `interpret(context: Context) -> Any` — evaluate this expression node given the current context
- `to_instruction() -> str` — serialize this expression back to a human-readable instruction string

## Constraints
- Each grammar rule MUST map to exactly one NonterminalExpression class
- TerminalExpression MUST NOT have children
- The Interpreter MUST NOT modify the grammar structure at runtime — the AST is immutable during interpretation
- Complex languages with many rules SHOULD use a parser generator instead of hand-built expressions

## Agentic AI Context
Use when agents need to execute structured command DSLs — workflow definitions, tool-call sequences, conditional plans, or templated prompts. An Interpreter lets you parse a structured plan like `[search, filter, summarize, cite]` into an AST and execute each node as an agent call. Natural fit for "agent as a programming language runtime."
