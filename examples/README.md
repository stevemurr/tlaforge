# Examples

This folder is the human-first quick start for TLAForge.

## Before You Start

From the repo root, install the package in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Learning Path

1. [01-traffic-light/README.md](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/01-traffic-light/README.md)
   Start with the smallest useful state machine.
2. [02-todo-workflow/README.md](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/02-todo-workflow/README.md)
   Add a terminal state and a simple invariant.
3. [03-retrying-job/README.md](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/03-retrying-job/README.md)
   Add an auxiliary variable, a constant, and a richer invariant.

Each example contains:

- `README.md` with the step-by-step walkthrough
- `build.py` with the builder code
- `spec.tla` with the committed generated output
