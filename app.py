"""
Agentic AI Design Patterns — CLI runner

Usage:
  python app.py list                    # List all 23 patterns
  python app.py run <pattern>           # Run a pattern's demo
  python app.py info <pattern>          # Show pattern description

Examples:
  python app.py list
  python app.py run singleton
  python app.py run observer
  python app.py info composite
"""

import importlib
import sys
import textwrap
from pathlib import Path


# ---------------------------------------------------------------------------
# Pattern registry — name → (module_path, category, description)
# ---------------------------------------------------------------------------

PATTERNS: dict[str, tuple[str, str, str]] = {
    # Creational
    "abstract-factory": (
        "src.imp.abstract_factory", "creational",
        "Creates families of related agents without specifying concrete classes. "
        "Swap the factory to switch the entire agent family atomically."
    ),
    "builder": (
        "src.imp.builder", "creational",
        "Separates pipeline construction from its representation. "
        "The Director holds the recipe; the Builder holds the materials."
    ),
    "factory-method": (
        "src.imp.factory_method", "creational",
        "Defines an interface for spawning an agent; subclasses decide which "
        "concrete agent to instantiate based on runtime context."
    ),
    "prototype": (
        "src.imp.prototype", "creational",
        "Creates new agents by cloning a pre-configured prototype, "
        "avoiding repeated initialization costs."
    ),
    "singleton": (
        "src.imp.singleton", "creational",
        "Ensures shared infrastructure (tool registry, rate limiter) "
        "has exactly one instance per process."
    ),
    # Structural
    "adapter": (
        "src.imp.adapter", "structural",
        "Converts the interface of an external API or legacy tool into "
        "the uniform tool interface that agents expect."
    ),
    "bridge": (
        "src.imp.bridge", "structural",
        "Decouples agent task logic from the model backend. "
        "Swap Claude for GPT without changing the agent."
    ),
    "composite": (
        "src.imp.composite", "structural",
        "Composes agents into tree structures. "
        "Orchestrators and leaf agents are treated uniformly."
    ),
    "decorator": (
        "src.imp.decorator", "structural",
        "Dynamically attaches capabilities (memory, logging, retry, guardrails) "
        "to any agent without subclassing. Decorators stack cleanly."
    ),
    "facade": (
        "src.imp.facade", "structural",
        "Provides a single entry point to a complex multi-agent subsystem. "
        "Callers see one method; the pipeline is hidden."
    ),
    "flyweight": (
        "src.imp.flyweight", "structural",
        "Shares immutable configuration across many agent instances. "
        "Maps directly to Anthropic prompt caching."
    ),
    "proxy": (
        "src.imp.proxy", "structural",
        "Provides a surrogate agent that adds caching, rate limiting, "
        "or logging without modifying the real agent."
    ),
    # Behavioral
    "chain-of-responsibility": (
        "src.imp.chain_of_responsibility", "behavioral",
        "Passes a task along a chain of handlers until one handles it. "
        "Enables tiered routing: fast → standard → deep."
    ),
    "command": (
        "src.imp.command", "behavioral",
        "Encapsulates an agent invocation as a serializable, queueable, "
        "retryable, undoable object."
    ),
    "interpreter": (
        "src.imp.interpreter", "behavioral",
        "Defines a mini-language for agent workflows and an interpreter "
        "that executes sentences in that language."
    ),
    "iterator": (
        "src.imp.iterator", "behavioral",
        "Provides sequential access to agent outputs without exposing "
        "the generation mechanism. Supports streaming and batch variants."
    ),
    "mediator": (
        "src.imp.mediator", "behavioral",
        "Centralizes multi-agent interaction. Every agent communicates "
        "only through the Mediator — never directly."
    ),
    "memento": (
        "src.imp.memento", "behavioral",
        "Captures and externalizes agent state (conversation history, memory) "
        "for checkpoint, restore, and resume."
    ),
    "observer": (
        "src.imp.observer", "behavioral",
        "Defines a one-to-many dependency between agents. "
        "Foundation for event-driven agent architectures."
    ),
    "state": (
        "src.imp.state", "behavioral",
        "An agent's behavior changes based on its current phase. "
        "Replaces nested if/elif logic with clean state objects."
    ),
    "strategy": (
        "src.imp.strategy", "behavioral",
        "Defines a family of model backends and makes them interchangeable. "
        "A StrategySelector picks cheapest capable backend at runtime."
    ),
    "template-method": (
        "src.imp.template_method", "behavioral",
        "Defines the workflow skeleton in a base class. "
        "Subagents fill in the steps without changing the structure."
    ),
    "visitor": (
        "src.imp.visitor", "behavioral",
        "Represents operations on agent outputs without modifying the agents. "
        "Run quality, cost, citation, and safety checks in one pass."
    ),
}

CATEGORIES = ["creational", "structural", "behavioral"]
CATEGORY_PATTERNS: dict[str, list[str]] = {cat: [] for cat in CATEGORIES}
for name, (_, cat, _) in PATTERNS.items():
    CATEGORY_PATTERNS[cat].append(name)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(args: list[str]) -> int:
    print("\nAgentic AI Design Patterns (GoF → AI)\n")
    for category in CATEGORIES:
        print(f"  {category.upper()}")
        for name in CATEGORY_PATTERNS[category]:
            _, _, desc = PATTERNS[name]
            short = desc.split(".")[0][:65]
            print(f"    {name:<28}  {short}")
        print()
    print(f"  Total: {len(PATTERNS)} patterns\n")
    print("  Run a demo:  python app.py run <pattern-name>")
    print("  Show info:   python app.py info <pattern-name>\n")
    return 0


def cmd_info(args: list[str]) -> int:
    if not args:
        print("Usage: python app.py info <pattern-name>")
        return 1
    name = args[0]
    if name not in PATTERNS:
        print(f"Unknown pattern: {name!r}")
        print(f"Available: {', '.join(sorted(PATTERNS))}")
        return 1
    module_path, category, desc = PATTERNS[name]
    print(f"\n{name}  [{category}]")
    print("-" * (len(name) + len(category) + 4))
    print(textwrap.fill(desc, width=72))
    print()
    print(f"  Abstract spec:    src/abc/{name}.md")
    print(f"  Implementation:   {module_path.replace('.', '/')}.py")
    print()
    return 0


def cmd_run(args: list[str]) -> int:
    if not args:
        print("Usage: python app.py run <pattern-name>")
        print(f"Available patterns: {', '.join(sorted(PATTERNS))}")
        return 1

    name = args[0]
    if name not in PATTERNS:
        print(f"Unknown pattern: {name!r}")
        print(f"Available: {', '.join(sorted(PATTERNS))}")
        return 1

    module_path, category, _ = PATTERNS[name]
    print(f"\nRunning demo: {name}  [{category}]")
    print("=" * 60)

    # Add project root to sys.path so `src.imp.*` imports work
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure `anthropic` is installed: pip install anthropic")
        return 1

    demo_fn = getattr(module, "demo", None)
    if demo_fn is None:
        print(f"Module {module_path} has no demo() function.")
        return 1

    try:
        demo_fn()
    except Exception as e:
        print(f"\nDemo failed: {e}")
        print("Check that ANTHROPIC_API_KEY is set in your environment.")
        return 1

    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

COMMANDS = {
    "list": cmd_list,
    "run": cmd_run,
    "info": cmd_info,
}


def main() -> int:
    argv = sys.argv[1:]

    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0

    command = argv[0]
    rest = argv[1:]

    if command not in COMMANDS:
        print(f"Unknown command: {command!r}")
        print(f"Available commands: {', '.join(COMMANDS)}")
        return 1

    return COMMANDS[command](rest)


if __name__ == "__main__":
    sys.exit(main())
