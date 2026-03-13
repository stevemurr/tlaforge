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
4. [04-live-todo-handoff/README.md](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/04-live-todo-handoff/README.md)
   Use a live local model to turn scripted user requests into a spec bundle and Pi-ready coding-agent handoff.
5. [05-pi-interactive-spec-loop/README.md](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/05-pi-interactive-spec-loop/README.md)
   Put Pi in the loop from the first turn so it interviews the user and iteratively shapes the draft.

Examples `01` through `03` contain:

- `README.md` with the step-by-step walkthrough
- `build.py` with the builder code
- `spec.tla` with the committed generated output

Example `04` is a live run instead:

- `README.md` with the walkthrough
- `run.py` with the structured session, bundle export, and Pi command generation
- no committed `spec.tla`, because the local model is part of the example

Example `05` is a prompt-and-transcript walkthrough:

- `README.md` with the Pi-first workflow
- `pi-bootstrap-prompt.md` with a reusable prompt for interactive spec discovery
- no committed `spec.tla`, because the point is the iterative requirements loop rather than a fixed output
