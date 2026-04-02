---
name: main
extends: []
description: runtime for agentic ai design patterns — registers and dispatches all abstract pattern agents
abstract_patterns: abc/
---


┌─────────────────────┬──────────────────────────────────────────────────────────────────────────────────┐
│     GoF Pattern     │                              Agentic AI Equivalent                               │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Abstract Factory    │ Agent Factory — creates families of specialized agents (researcher, writer,      │
│                     │ critic) with a consistent interface                                              │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Builder             │ Pipeline Builder — step-by-step construction of complex multi-agent workflows    │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Factory Method      │ Agent Spawner — subclass/config decides which agent type to instantiate          │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Prototype           │ Agent Template Cloning — clone a pre-configured agent with its tools and memory  │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Singleton           │ Registry / Shared Service Agent — one instance of a memory store or tool server  │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Adapter             │ Tool Adapter — wraps external APIs as uniform tool interfaces for agents         │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Bridge              │ Model Bridge — separates agent logic from the underlying LLM (swap Claude for    │
│                     │ GPT without changing orchestration)                                              │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Composite           │ Agent Swarm / Hierarchy — tree of agents where orchestrators contain sub-agents  │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Decorator           │ Capability Wrapper — dynamically adds memory, logging, rate-limiting to an agent │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Facade              │ Orchestrator Facade — simplified interface hiding a complex multi-agent system   │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Flyweight           │ Shared Context / Prompt Cache — shared immutable state across many agent         │
│                     │ instances                                                                        │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Proxy               │ Agent Proxy — controls access, adds caching, auth, or logging before reaching    │
│                     │ the real agent                                                                   │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Chain of            │ Agent Pipeline — each agent processes the task or passes it to the next          │
│ Responsibility      │                                                                                  │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Command             │ Task Object — encapsulates an agent invocation as a serializable, queueable unit │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Interpreter         │ Prompt DSL — an agent interprets a structured mini-language for instructions     │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Iterator            │ Agent Stream — iterates over streaming agent outputs or collections of results   │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Mediator            │ Orchestrator — central coordinator for multi-agent interactions, decoupling them │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Memento             │ Conversation Snapshot — save/restore agent state (context, memory, tool state)   │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Observer            │ Event Bus — agents subscribe to events (tool calls, model outputs, errors)       │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ State               │ Agent State Machine — agent behavior changes based on phase (planning,           │
│                     │ executing, reviewing)                                                            │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Strategy            │ Model Strategy — swappable LLM backends with a uniform interface                 │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Template Method     │ Workflow Skeleton — base agent defines the step sequence, subagents fill in the  │
│                     │ steps                                                                            │
├─────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Visitor             │ Agent Evaluator / Inspector — traverses agent outputs applying evaluation,       │
│                     │ logging, or transformation                                                       │
└─────────────────────┴──────────────────────────────────────────────────────────────────────────────────┘