---
name: proxy
abstract: true
pattern: Proxy
category: structural
extends: []
description: Provide a surrogate for another agent to control access, add caching, enforce rate limits, or log interactions.
---

## Intent
Provide a surrogate or placeholder for another agent to control access to it. A Proxy can add caching, rate-limiting, access control, logging, or lazy initialization without modifying the real agent.

## Participants
- **Subject** — defines the common interface for both RealSubject and Proxy
- **RealSubject** — the real agent that does the actual work
- **Proxy** *(this)* — maintains a reference to the RealSubject; controls access; may pre/post-process requests
- **Client** — interacts only with the Subject interface; unaware of the Proxy

## Proxy Variants
- **Remote Proxy** — represents an agent running in another process or on another node
- **Virtual Proxy** — lazily initializes an expensive agent on first use
- **Protection Proxy** — gates access based on permissions or quotas
- **Caching Proxy** — memoizes results for identical inputs
- **Logging Proxy** — records all interactions for observability

## Abstract Interface
Implementors MUST define:
- `run(task: str, context: dict) -> AgentResult` — intercept the call; apply proxy behavior; delegate to real subject
- `real_subject() -> Agent` — return or lazily create the wrapped agent
- `proxy_type() -> str` — identify the proxy variant (remote/virtual/protection/caching/logging)

## Constraints
- The Proxy MUST implement the same interface as the RealSubject — fully substitutable
- The Proxy MUST delegate to the RealSubject for all actual task work
- A Caching Proxy MUST ensure cache keys include all inputs that affect the output

## Agentic AI Context
Use a Caching Proxy to avoid redundant LLM calls for deterministic subtasks. Use a Protection Proxy to enforce per-user rate limits or capability gates. Use a Remote Proxy to call an agent running as a separate microservice. The proxy is invisible to the orchestrator — it sees only the Subject interface.
