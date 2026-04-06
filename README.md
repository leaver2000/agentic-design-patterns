# Agentic AI Design Patterns

A companion work mapping all 23 Gang of Four design patterns to modern agentic AI architecture, using the Anthropic SDK as the reference implementation.

**Source:** *Design Patterns: Elements of Reusable Object-Oriented Software* (Gamma, Helm, Johnson, Vlissides)

## Premise

The GoF patterns are timeless structural solutions to recurring object-oriented problems. Agentic AI systems — multi-agent orchestration, tool use, memory, pipelines — exhibit the same architectural problems. The mapping is natural and provides a proven vocabulary for AI engineering.

## Pattern Mapping

| GoF Pattern | Agentic AI Equivalent |
|---|---|
| Abstract Factory | Agent Factory — creates families of specialized agents (researcher, writer, critic) with a consistent interface |
| Builder | Pipeline Builder — step-by-step construction of complex multi-agent workflows |
| Factory Method | Agent Spawner — subclass/config decides which agent type to instantiate |
| Prototype | Agent Template Cloning — clone a pre-configured agent with its tools and memory |
| Singleton | Registry / Shared Service Agent — one instance of a memory store or tool server |
| Adapter | Tool Adapter — wraps external APIs as uniform tool interfaces for agents |
| Bridge | Model Bridge — separates agent logic from the underlying LLM (swap Claude for GPT without changing orchestration) |
| Composite | Agent Swarm / Hierarchy — tree of agents where orchestrators contain sub-agents |
| Decorator | Capability Wrapper — dynamically adds memory, logging, rate-limiting to an agent |
| Facade | Orchestrator Facade — simplified interface hiding a complex multi-agent system |
| Flyweight | Shared Context / Prompt Cache — shared immutable state across many agent instances |
| Proxy | Agent Proxy — controls access, adds caching, auth, or logging before reaching the real agent |
| Chain of Responsibility | Agent Pipeline — each agent processes the task or passes it to the next |
| Command | Task Object — encapsulates an agent invocation as a serializable, queueable unit |
| Interpreter | Prompt DSL — an agent interprets a structured mini-language for instructions |
| Iterator | Agent Stream — iterates over streaming agent outputs or collections of results |
| Mediator | Orchestrator — central coordinator for multi-agent interactions, decoupling them |
| Memento | Conversation Snapshot — save/restore agent state (context, memory, tool state) |
| Observer | Event Bus — agents subscribe to events (tool calls, model outputs, errors) |
| State | Agent State Machine — agent behavior changes based on phase (planning, executing, reviewing) |
| Strategy | Model Strategy — swappable LLM backends with a uniform interface |
| Template Method | Workflow Skeleton — base agent defines the step sequence, subagents fill in the steps |
| Visitor | Agent Evaluator / Inspector — traverses agent outputs applying evaluation, logging, or transformation |

## Repository Structure

```
src/
  abc/          # Abstract pattern definitions (one .md per pattern)
  agents/       # Concrete agent roles: orchestrator, researcher, coder, critic, pipeline
  imp/          # Concrete pattern implementations
  main.md       # Runtime registry — maps all 23 patterns to their agentic equivalents
docs/           # Extended documentation
agent-patterns-clean.md   # Cleaned GoF source text (output of cleanup.py)
cleanup.py      # PDF-to-markdown cleanup pipeline (10 steps)
```

### Abstract Pattern Files (`src/abc/`)

Each file follows the GoF structure adapted for agents:

- **Intent** — what problem the pattern solves in an agentic context
- **Participants** — abstract roles (factory, agent, client)
- **Abstract Interface** — methods implementors must define
- **Constraints** — invariants that all implementations must respect
- **Agentic AI Context** — when to apply this pattern

### Each pattern entry (in full form) covers

- Intent, Motivation, Applicability, Structure
- Participants, Collaborations, Consequences
- Implementation notes (Anthropic SDK)
- Sample Code (Python, `anthropic` SDK)
- Known Uses (LangGraph, CrewAI, AutoGen, Claude Code)
- Related Patterns

## Source Text

`agent-patterns-clean.md` is a cleaned markdown conversion of the GoF book, produced by `cleanup.py` from the source PDF. The cleanup pipeline handles OCR artifacts, hyphenated word-wraps, character-spacing corruption, Smalltalk `#symbol` formatting, and adds heading structure and code fences.

Verification: H1=1, H2=16, H3=82, H4=264, 499 code blocks, word count delta 2.1%.
