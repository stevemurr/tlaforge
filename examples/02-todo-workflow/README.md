# Todo Workflow

## Problem Statement

Model a single todo moving from `pending` to `in_progress` to `complete`, with `archived` as a terminal state.

## State Model

- States: `pending`, `in_progress`, `complete`, `archived`
- Initial state: `pending`
- Terminal state: `archived`

## Code Walk-Through

1. Start with the same `StateMachineSpec` pattern as the traffic light.
2. Add a terminal state by listing `archived` in `terminal_states`.
3. Add transitions for starting, pausing, completing, and archiving.
4. Add a simple invariant that keeps the workflow type-safe: `state \in States`.

The full builder code lives in [build.py](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/02-todo-workflow/build.py).

## Run Command

Assuming you already created and activated a virtual environment, then ran `python -m pip install -e .` from the repo root:

```bash
python examples/02-todo-workflow/build.py
```

The committed output is in [spec.tla](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/02-todo-workflow/spec.tla).

## What To Change Next

Try adding a `cancelled` state and decide which existing states are allowed to transition into it.
