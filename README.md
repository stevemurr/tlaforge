# TLAForge

TLAForge is a small Python package for building TLA+ state machine specs with Python objects instead of raw strings.

The human-first path is the builder library plus the examples in [examples/README.md](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/README.md). The Anthropic-backed agent remains available as a secondary prototype entrypoint.

## Quick Start

Install the package in editable mode from the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Then work through the example ladder:

1. [examples/01-traffic-light/README.md](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/01-traffic-light/README.md)
2. [examples/02-todo-workflow/README.md](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/02-todo-workflow/README.md)
3. [examples/03-retrying-job/README.md](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/03-retrying-job/README.md)

## Builder-First Usage

```python
from tlaforge import (
    BinOp,
    Definition,
    PrimedVar,
    StateMachineSpec,
    StateTransition,
    StringLit,
    Var,
)

spec = StateMachineSpec(
    module_name="TrafficLight",
    states=["red", "green", "yellow"],
    initial_state="red",
)

spec.transitions.append(
    StateTransition(
        name="GreenToYellow",
        comment="Timer expires on green",
        guards=[BinOp(Var("state"), "=", StringLit("green"))],
        updates=[BinOp(PrimedVar("state"), "=", StringLit("yellow"))],
    )
)

spec.invariants.append(
    Definition(
        name="ValidState",
        comment="The controller is always in one named state",
        body=BinOp(Var("state"), "\\in", Var("States")),
    )
)

print(spec.emit())
```

If you add auxiliary variables, declare their initial values explicitly:

```python
from tlaforge import IntLit, StateMachineSpec

spec = StateMachineSpec(
    module_name="RetryingJob",
    states=["queued", "running", "failed"],
    initial_state="queued",
    aux_vars=["retries"],
    aux_init={"retries": IntLit(0)},
)
```

## Expression Builders

| Class | TLA+ Output |
|---|---|
| `Raw("text")` | `text` |
| `Var("x")` | `x` |
| `PrimedVar("x")` | `x'` |
| `StringLit("s")` | `"s"` |
| `IntLit(n)` | `n` |
| `BinOp(l, "=", r)` | `l = r` |
| `And(e1, e2)` | `/\ e1 /\ e2` |
| `Or(e1, e2)` | `\/ e1 \/ e2` |
| `Not(e)` | `~e` |
| `Unchanged("x", "y")` | `UNCHANGED <<x, y>>` |
| `Forall("x", domain, body)` | `\A x \in domain : body` |
| `Exists("x", domain, body)` | `\E x \in domain : body` |
| `Eventually(p)` | `<>(p)` |
| `Always(p)` | `[](p)` |
| `LeadsTo(p, q)` | `p ~> q` |
| `FunctionApp(f, k)` | `f[k]` |
| `Except(f, k, v)` | `[f EXCEPT ![k] = v]` |
| `SetOf("x", domain, p)` | `{ x \in domain : p }` |

## CLI Prototype

The package-native CLI is:

```bash
python -m tlaforge.cli --help
```

This CLI uses the Anthropic-backed agent path, so it is not the main quick start. To use it, set `ANTHROPIC_API_KEY` and then run one of these:

```bash
python -m tlaforge.cli --demo
python -m tlaforge.cli --traffic
python -m tlaforge.cli "An elevator that moves between floors 1-10"
python -m tlaforge.cli --from-file my_system.txt --output spec.tla --interactive
```

## Running Tests

Install the test extras in your virtual environment:

```bash
python -m pip install -e '.[test]'
```

Then run the canonical coverage command:

```bash
python -m pytest --cov=tlaforge --cov=build_backend --cov-report=term-missing --cov-fail-under=90
```

## Project Layout

```text
tlaforge/
├── tlaforge/
│   ├── __init__.py
│   ├── agent.py
│   ├── builder.py
│   └── cli.py
├── examples/
├── tests/
└── README.md
```
