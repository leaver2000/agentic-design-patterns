# Quick Start

## Prerequisites

- Python 3.12+
- An Anthropic API key

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Run a demo

```bash
# List all 23 patterns
python app.py list

# Run a specific pattern's demo (makes live API calls)
python app.py run singleton          # No API calls — good first run
python app.py run visitor            # No API calls — good first run
python app.py run observer
python app.py run decorator
python app.py run memento

# Show description and file locations for a pattern
python app.py info composite
```

## Repository structure

```
src/
  abc/          Abstract pattern definitions — one .md per pattern
  agents/       Concrete agent roles built on top of the abstractions
  imp/          Python implementations — one .py per pattern
  main.md       Master mapping table (GoF → Agentic AI)
docs/           This file and future extended docs
agent-patterns-clean.md   Cleaned GoF source text (cleaned by cleanup.py)
cleanup.py      PDF-to-markdown cleanup pipeline
app.py          CLI runner
```

## Three-layer architecture

Every pattern spans three layers:

| Layer | Location | Purpose |
|---|---|---|
| Abstract spec | `src/abc/<pattern>.md` | GoF-style definition: intent, participants, interface, constraints |
| Agent roles | `src/agents/<role>/` | Concrete agent definitions (system prompts, models, tool lists) |
| Implementation | `src/imp/<pattern>.py` | Runnable Python using the `anthropic` SDK |

Read a pattern top-to-bottom: abstract spec → agent role (if applicable) → implementation.

## Reading the abstract specs

Each `src/abc/*.md` file follows this structure:

- **Intent** — what problem this pattern solves in an agentic context
- **Participants** — abstract roles (factory, agent, client)
- **Abstract Interface** — methods that all implementations must define
- **Constraints** — invariants every implementation must respect
- **Agentic AI Context** — when and why to use this pattern

## Reading the implementations

Each `src/imp/*.py` file follows this structure:

```
# Module docstring — what this file demonstrates
# Abstract base (ABC or Protocol)
# Concrete implementation(s)
# Client code
# demo() function — runnable end-to-end example
```

Run any demo with `python app.py run <pattern>` or directly:
```bash
python src/imp/observer.py
python src/imp/decorator.py
```

## Pattern categories

**Creational** — how agents are created
- `abstract-factory` — families of related agents, atomically swappable
- `builder` — step-by-step pipeline construction
- `factory-method` — deferred agent instantiation
- `prototype` — clone-based agent initialization
- `singleton` — shared infrastructure (tool registry, rate limiter)

**Structural** — how agents are composed
- `adapter` — wraps external APIs as uniform tool interfaces
- `bridge` — decouples agent logic from the model backend
- `composite` — agent trees treated uniformly
- `decorator` — stackable capabilities (memory, logging, retry, guardrails)
- `facade` — single entry point to a multi-agent pipeline
- `flyweight` — shared immutable state (maps to Anthropic prompt caching)
- `proxy` — caching, rate limiting, logging without touching the agent

**Behavioral** — how agents communicate and coordinate
- `chain-of-responsibility` — tiered routing: fast → standard → deep
- `command` — serializable, queueable, undoable task objects
- `interpreter` — mini-language DSL for agent workflows
- `iterator` — streaming and batch output traversal
- `mediator` — centralized multi-agent coordination
- `memento` — conversation checkpoint and restore
- `observer` — event-driven agent architecture
- `state` — agent phase machine (planning → executing → reviewing)
- `strategy` — swappable model backends
- `template-method` — fixed workflow skeleton, customizable steps
- `visitor` — post-hoc output analysis without touching agents

## Cost-conscious demos

Several patterns can be demonstrated without API calls or with minimal usage:

- `singleton` — no API calls; demonstrates thread-safe singleton mechanics
- `visitor` — no API calls; operates on pre-built output structures
- `bridge` (echo backend) — no API calls; uses the `EchoBackend`
- `iterator` (batch mode) — uses Haiku for cheap batch classification
- `flyweight` — uses Haiku; shared config reduces total calls

Patterns that make multiple API calls (e.g., `composite`, `mediator`, `facade`)
will incur proportionally higher cost. Check the demo output for token counts.

## GoF source text

`agent-patterns-clean.md` is a cleaned markdown conversion of the Gang of Four
book, produced by running `cleanup.py` on the source PDF:

```bash
python cleanup.py
```

This is the reference material the pattern specifications are drawn from.
