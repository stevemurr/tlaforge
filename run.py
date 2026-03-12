#!/usr/bin/env python3
"""
TLAForge CLI — generate TLA+ specs from natural language.

Usage:
    python run.py "describe your system here"
    python run.py --demo
    python run.py --from-file description.txt
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from tlaforge.agent import TLAForgeAgent


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


def main():
    parser = argparse.ArgumentParser(description="TLAForge: Generate TLA+ specs with AI")
    parser.add_argument("description", nargs="?", help="Natural language system description")
    parser.add_argument("--demo", action="store_true", help="Run the todo app demo")
    parser.add_argument("--traffic", action="store_true", help="Run the traffic light demo")
    parser.add_argument("--from-file", metavar="FILE", help="Read description from file")
    parser.add_argument("--output", metavar="FILE", help="Write TLA+ to file")
    parser.add_argument("--interactive", action="store_true", help="Enter refinement loop after generation")
    args = parser.parse_args()

    # Determine description
    if args.demo:
        description = DEMO_DESCRIPTION
        print("=== TLAForge Demo: Todo App ===\n")
    elif args.traffic:
        description = TRAFFIC_LIGHT_DESCRIPTION
        print("=== TLAForge Demo: Traffic Light ===\n")
    elif args.from_file:
        with open(args.from_file) as f:
            description = f.read()
        print(f"=== TLAForge: Generating spec from {args.from_file} ===\n")
    elif args.description:
        description = args.description
        print("=== TLAForge: Generating spec ===\n")
    else:
        parser.print_help()
        sys.exit(1)

    print(f"Description:\n{description.strip()}\n")
    print("-" * 50)
    print("Generating TLA+ spec...\n")

    agent = TLAForgeAgent()

    tla, code = agent.generate(description)

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
        with open(args.output, "w") as f:
            f.write(tla)
        print(f"\nTLA+ written to: {args.output}")

        code_path = args.output.replace(".tla", "_builder.py")
        with open(code_path, "w") as f:
            f.write(code)
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
            tla, code = agent.refine(feedback)

            print("\nUpdated TLA+:")
            print("-" * 40)
            print(tla)

            if args.output:
                with open(args.output, "w") as f:
                    f.write(tla)
                print(f"\nUpdated TLA+ written to: {args.output}")


if __name__ == "__main__":
    main()
