# TLAForge

A Python library for programmatically generating TLA+ specs, with an LLM agent that uses the library to produce correct output.

## The Core Idea

Instead of asking an LLM to generate raw TLA+ text (which breaks on syntax errors), the LLM generates **Python code that calls a builder library**. The library enforces syntactic correctness — the LLM only has to get the semantics right.

```
User describes system in natural language
        ↓
LLM receives builder API as context
        ↓
LLM generates Python code calling builder classes
        ↓
Builder emits syntactically valid TLA+
        ↓
(optional) TLC model checker validates
        ↓
Counterexamples feed back to LLM for refinement
```

## Usage

### As a library (manual spec construction)

```python
from tlaforge import *

spec = StateMachineSpec(
    module_name="TrafficLight",
    states=["red", "green", "yellow"],
    initial_state="red",
    terminal_states=[]
)

spec.transitions.append(StateTransition(
    name="GreenToYellow",
    comment="Timer expires on green",
    guards=[BinOp(Var("state"), "=", StringLit("green"))],
    updates=[BinOp(PrimedVar("state"), "=", StringLit("yellow"))],
    unchanged=[]
))

spec.invariants.append(Definition(
    name="AlwaysOneState",
    body=BinOp(Var("state"), "\\in", Var("States"))
))

print(spec.emit())
```

### As an LLM agent

```python
from tlaforge import TLAForgeAgent

agent = TLAForgeAgent()

tla, code = agent.generate("""
    A simple order processing system with states:
    pending, processing, shipped, delivered, cancelled.
    Orders can be cancelled from pending or processing.
    Once shipped, an order cannot be cancelled.
""")

print(tla)

# Refine based on feedback
tla, code = agent.refine("Add a 'returned' state reachable from delivered")
```

### CLI

```bash
# Run the todo app demo
python run.py --demo

# Describe a system inline
python run.py "An elevator that moves between floors 1-10"

# From a file, with output saved and interactive refinement
python run.py --from-file my_system.txt --output spec.tla --interactive
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

## Why This Architecture Works

The key insight is **separating concerns**:

- **Syntax** is handled by the library (guaranteed correct by construction)
- **Semantics** is handled by the LLM (what states/transitions/invariants make sense)
- **Validation** is handled by TLC (finds logical errors the LLM missed)

This is the same pattern as SQL query builders vs raw SQL, or AST manipulation vs string-based code generation. The LLM makes far fewer errors when it's constrained to valid API calls rather than free-form text generation.

## Project Structure

```
tlaforge/
├── tlaforge/
│   ├── __init__.py
│   ├── builder.py    # Core expression/spec builder classes
│   └── agent.py      # LLM agent that calls the builder
├── run.py            # CLI
└── README.md
```
