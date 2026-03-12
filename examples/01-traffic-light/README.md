# Traffic Light

## Problem Statement

Model a single traffic light that cycles through `red`, `green`, and `yellow`.

## State Model

- States: `red`, `green`, `yellow`
- Initial state: `red`
- No auxiliary variables yet

## Code Walk-Through

1. Create a `StateMachineSpec` with the module name, state list, and initial state.
2. Add one `StateTransition` per timer-driven edge in the cycle.
3. Add a small invariant that says `state \in States`.

The full builder code lives in [build.py](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/01-traffic-light/build.py).

## Run Command

Assuming you already created and activated a virtual environment, then ran `python -m pip install -e .` from the repo root:

```bash
python examples/01-traffic-light/build.py
```

The committed output is in [spec.tla](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/01-traffic-light/spec.tla).

## What To Change Next

Try adding a `flashing` state and one extra transition to see how the emitted `Next` operator changes.
