"""Package-native CLI for the Anthropic-backed TLAForge agent."""

from __future__ import annotations

import argparse
from pathlib import Path

from .agent import TLAForgeAgent


DEMO_DESCRIPTION = """
A todo application with the following behavior:

- Users can add todos. Each todo has a title and starts in 'pending' state.
- A todo can be started (pending -> in_progress)
- A todo can be completed (in_progress -> complete)  
- A todo can be archived from any non-archived state
- A todo can be un-started (in_progress -> pending)
- Archived is a terminal state — no transitions out
- There is a maximum number of todos (MaxTodos constant)
- Todos can only be deleted if they are archived first

Key invariants:
- Todo count never exceeds MaxTodos
- Archived todos cannot transition to any other state
- A todo's ID never changes once assigned
"""

TRAFFIC_LIGHT_DESCRIPTION = """
A traffic light controller for a single intersection:

States: red, green, yellow
- green -> yellow (timer expires)
- yellow -> red (timer expires)  
- red -> green (timer expires)

This is a simple cycle. The invariant is that the light is always
in exactly one state, and yellow is always between green and red.
"""


def _load_description(args: argparse.Namespace) -> tuple[str, str]:
    if args.demo:
        return "TLAForge Demo: Todo App", DEMO_DESCRIPTION
    if args.traffic:
        return "TLAForge Demo: Traffic Light", TRAFFIC_LIGHT_DESCRIPTION
    if args.from_file:
        path = Path(args.from_file)
        return f"TLAForge: Generating spec from {path}", path.read_text(encoding="utf-8")
    if args.description:
        return "TLAForge: Generating spec", args.description
    raise ValueError("Missing description input")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Anthropic-backed TLAForge prototype CLI. "
            "For the human-first quick start, start with the examples/ folder."
        )
    )
    parser.add_argument("description", nargs="?", help="Natural language system description")
    parser.add_argument("--demo", action="store_true", help="Run the todo app demo")
    parser.add_argument("--traffic", action="store_true", help="Run the traffic light demo")
    parser.add_argument("--from-file", metavar="FILE", help="Read description from file")
    parser.add_argument("--output", metavar="FILE", help="Write TLA+ to file")
    parser.add_argument("--interactive", action="store_true", help="Enter refinement loop after generation")
    args = parser.parse_args(argv)

    if not any([args.demo, args.traffic, args.from_file, args.description]):
        parser.print_help()
        return 1

    title, description = _load_description(args)
    print(f"=== {title} ===\n")

    print(f"Description:\n{description.strip()}\n")
    print("-" * 50)
    print("Generating TLA+ spec...\n")

    agent = TLAForgeAgent()
    try:
        tla, code = agent.generate(description)
    except Exception as exc:
        parser.exit(status=1, message=f"Error: {exc}\n")

    print("\n" + "=" * 50)
    print("Generated Python (builder code):")
    print("=" * 50)
    print(code)

    print("\n" + "=" * 50)
    print("Generated TLA+:")
    print("=" * 50)
    print(tla)

    # Write output
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(tla, encoding="utf-8")
        print(f"\nTLA+ written to: {output_path}")

        code_path = output_path.with_name(f"{output_path.stem}_builder.py")
        code_path.write_text(code, encoding="utf-8")
        print(f"Builder code written to: {code_path}")

    # Interactive refinement loop
    if args.interactive:
        print("\n" + "=" * 50)
        print("Entering refinement mode. Type 'quit' to exit.")
        print("=" * 50)

        while True:
            feedback = input("\nRefinement feedback (or 'quit'): ").strip()
            if feedback.lower() in ("quit", "exit", "q"):
                break
            if not feedback:
                continue

            print("\nRefining spec...")
            try:
                tla, code = agent.refine(feedback)
            except Exception as exc:
                print(f"Error: {exc}")
                continue

            print("\nUpdated TLA+:")
            print("-" * 40)
            print(tla)

            if args.output:
                Path(args.output).write_text(tla, encoding="utf-8")
                print(f"\nUpdated TLA+ written to: {args.output}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
