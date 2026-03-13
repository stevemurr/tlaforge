# TLAForge

TLAForge is a small Python package for building TLA+ state machine specs with Python objects instead of raw strings.

The package now has two main layers:

1. A deterministic builder/compiler backend.
2. A structured session API for conversationally building machine drafts without generating Python code from the model.

The quickest human-first path is still the builder library plus the examples in [examples/README.md](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/README.md).

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

## Structured Session Usage

The primary high-level API is `TLAForgeSession`, which manages a typed `MachineDraft` and only exports a handoff artifact when the draft is ready.

```python
from tlaforge import (
    BinaryExpr,
    DraftPatch,
    PutRuleOp,
    PutStateOp,
    PutTransitionOp,
    RefExpr,
    RuleDraft,
    SetInitialStateOp,
    SetModuleNameOp,
    StateDraft,
    TLAForgeSession,
    TransitionDraft,
)

session = TLAForgeSession.new(summary="Traffic light controller")
session.apply_patch(
    DraftPatch(
        operations=[
            SetModuleNameOp(module_name="TrafficLight"),
            PutStateOp(state=StateDraft(name="red")),
            PutStateOp(state=StateDraft(name="green")),
            PutStateOp(state=StateDraft(name="yellow")),
            SetInitialStateOp(initial_state="red"),
            PutTransitionOp(transition=TransitionDraft(name="RedToGreen", from_state="red", to_state="green")),
            PutTransitionOp(transition=TransitionDraft(name="GreenToYellow", from_state="green", to_state="yellow")),
            PutTransitionOp(transition=TransitionDraft(name="YellowToRed", from_state="yellow", to_state="red")),
            PutRuleOp(
                rule=RuleDraft(
                    name="ValidState",
                    kind="invariant",
                    expr=BinaryExpr(op="in", left=RefExpr(name="state"), right=RefExpr(name="States")),
                )
            ),
        ]
    )
)

artifact = session.export_handoff()
print(artifact.tla_source)
```

To drive a session from an LLM, use a structured client such as `OpenAICompatibleStructuredClient`. The model returns validated `AssistantTurn` data, not Python code.

For a local OpenAI-compatible model server, use the local-provider preset instead of repeating provider-specific knobs inline:

```python
from tlaforge import OpenAICompatibleStructuredClient

client = OpenAICompatibleStructuredClient.local(
    model="nemotron3-nano",
    api_key="sk-change-me",
    base_url="http://192.168.1.237:4000",
)
```

This preset enables strict JSON-schema responses and disables provider "thinking" so structured output stays stable.

## Expression Builders

| Class | TLA+ Output |
|---|---|
| `Raw("text")` | `text` |
| `Var("x")` | `x` |
| `PrimedVar("x")` | `x'` |
| `StringLit("s")` | `"s"` |
| `IntLit(n)` | `n` |
| `BoolLit(True)` | `TRUE` |
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

## Running Tests

Install the test extras in your virtual environment:

```bash
python -m pip install -e '.[test]'
```

Then run the canonical coverage command:

```bash
python -m pytest --cov=tlaforge --cov=build_backend --cov-report=term-missing --cov-fail-under=90
```

## Live Provider Tests

The live suite is opt-in and hits a real local OpenAI-compatible model provider through the same `OpenAICompatibleStructuredClient` runtime path used by the library.

Required environment variables:

- `TLAFORGE_LIVE_BASE_URL`
- `TLAFORGE_LIVE_MODEL`
- `TLAFORGE_LIVE_API_KEY`

The local provider requires authentication even for health/model checks, and the live harness disables provider "thinking" to keep structured output deterministic enough for schema validation.

Run the live tests with:

```bash
env TLAFORGE_LIVE_BASE_URL=http://192.168.1.237:4000 \
    TLAFORGE_LIVE_MODEL=nemotron3-nano \
    TLAFORGE_LIVE_API_KEY=sk-change-me \
    python -m pytest -m live_network tests/test_llm_live.py -vv
```

## Project Layout

```text
tlaforge/
├── tlaforge/
│   ├── __init__.py
│   ├── builder.py
│   ├── compiler.py
│   ├── draft.py
│   ├── llm.py
│   ├── patches.py
│   ├── session.py
│   └── validation.py
├── examples/
├── tests/
└── README.md
```
