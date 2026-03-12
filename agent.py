"""
TLAForge Agent — uses Claude to generate TLA+ specs via the builder library.

Flow:
  1. User describes a system in natural language
  2. We send Claude the builder API + user description
  3. Claude returns Python code that calls the builder
  4. We exec() the code to get a StateMachineSpec object
  5. We emit the TLA+ and optionally validate it
"""

import json
import textwrap
import re
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tlaforge.builder import (
    StateMachineSpec, StateTransition, Definition,
    And, Or, Not, Raw, Var, PrimedVar, StringLit, IntLit,
    BinOp, Unchanged, Implies, Forall, Exists,
    SetLit, Eventually, Always, LeadsTo, FunctionApp, Except
)


# ---------------------------------------------------------------------------
# The API reference we send to the LLM
# ---------------------------------------------------------------------------

BUILDER_API_REFERENCE = '''
You are generating a TLA+ specification using the TLAForge Python builder library.
Your job is to return ONLY a Python code block that:
1. Imports from tlaforge.builder (already done for you)
2. Creates a `spec` variable of type `StateMachineSpec`
3. Populates it with states, transitions, invariants, and liveness properties

## Available Classes

### StateMachineSpec(module_name, ...)
The top-level spec container.

Fields:
- module_name: str               — TLA+ module name
- extends: List[str]             — e.g. ["Integers", "FiniteSets"]
- state_var: str                 — name of the state variable (default: "state")
- aux_vars: List[str]            — additional variable names
- states: List[str]              — all possible state names
- initial_state: str             — starting state
- terminal_states: List[str]     — states with no outgoing transitions
- constants: List[str]           — TLA+ CONSTANTS
- transitions: List[StateTransition]
- invariants: List[Definition]
- liveness: List[Definition]
- helpers: List[Definition]      — helper operator definitions

### StateTransition(name, guards, updates, unchanged, comment)
One action/transition in the state machine.

- guards: List[Expr]    — conditions that must hold (preconditions)
- updates: List[Expr]   — state assignments (postconditions)
- unchanged: List[str]  — variables not modified by this action

### Definition(name, params, body, comment)
A named TLA+ definition (invariant, helper, liveness property).

- params: List[str]     — parameter names (empty for constants)
- body: Expr            — the expression

## Expression Builders

| Class | TLA+ Output | Usage |
|---|---|---|
| Raw("text") | text | Escape hatch for complex expressions |
| Var("x") | x | Variable reference |
| PrimedVar("x") | x' | Post-state variable |
| StringLit("s") | "s" | String literal |
| IntLit(n) | n | Integer literal |
| BinOp(l, "=", r) | l = r | Any binary op: =, #, <, >, <=, >=, +, -, \\in, \\notin |
| And(e1, e2, ...) | /\\ e1 /\\ e2 | Conjunction |
| Or(e1, e2, ...) | \\/ e1 \\/ e2 | Disjunction |
| Not(e) | ~e | Negation |
| Implies(p, q) | p => q | Implication |
| Unchanged("x", "y") | UNCHANGED <<x, y>> | No-change clause |
| Forall("x", domain, body) | \\A x \\in domain : body | Universal quantifier |
| Exists("x", domain, body) | \\E x \\in domain : body | Existential quantifier |
| FunctionApp(f, k) | f[k] | Function lookup |
| Except(f, k, v) | [f EXCEPT ![k] = v] | Function update |
| Eventually(p) | <>(p) | Diamond (liveness) |
| Always(p) | [](p) | Box (safety) |
| LeadsTo(p, q) | p ~> q | Leads-to (liveness) |
| SetLit(e1, e2) | {e1, e2} | Set literal |

## Pattern: Standard State Transition
```python
StateTransition(
    name="MyAction",
    comment="Description of what this action does",
    guards=[
        BinOp(Var("state"), "=", StringLit("from_state")),
        # ... other preconditions
    ],
    updates=[
        BinOp(PrimedVar("state"), "=", StringLit("to_state")),
        # ... other variable updates
    ],
    unchanged=["other_var1", "other_var2"]  # vars not touched
)
```

## Pattern: Invariant Definition
```python
Definition(
    name="MyInvariant",
    comment="What this invariant checks",
    body=Forall("x", Var("SomeSet"), 
                Implies(
                    BinOp(Var("state"), "=", StringLit("bad")),
                    Raw("FALSE")
                ))
)
```

## IMPORTANT RULES
1. Every transition should have a state guard as its first guard
2. Every transition must account for ALL variables — either update them or list in `unchanged`
3. Terminal states must have no outgoing transitions
4. Invariants use current-state variables (no primed vars)
5. Use Raw() for complex expressions that don\'t have a builder (CASE, LET-IN, etc.)
6. The variable `spec` must be assigned at the end

## Output Format
Return ONLY a Python code block. No explanation, no markdown, no TLA+.
```python
# your code here
spec = StateMachineSpec(...)
```
'''


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class TLAForgeAgent:
    def __init__(self):
        self.history = []

    def _call_claude(self, user_message: str) -> str:
        import urllib.request

        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "system": BUILDER_API_REFERENCE,
            "messages": self.history + [{"role": "user", "content": user_message}]
        }

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())

        return data["content"][0]["text"]

    def _extract_code(self, response: str) -> str:
        """Pull Python code out of a response that may have markdown fences."""
        match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
        if match:
            return match.group(1)
        # No fences — assume the whole thing is code
        return response.strip()

    def _exec_code(self, code: str) -> StateMachineSpec:
        """Execute builder code and return the spec object."""
        namespace = {
            "StateMachineSpec": StateMachineSpec,
            "StateTransition": StateTransition,
            "Definition": Definition,
            "And": And, "Or": Or, "Not": Not,
            "Raw": Raw, "Var": Var, "PrimedVar": PrimedVar,
            "StringLit": StringLit, "IntLit": IntLit,
            "BinOp": BinOp, "Unchanged": Unchanged,
            "Implies": Implies, "Forall": Forall, "Exists": Exists,
            "SetLit": SetLit, "Eventually": Eventually,
            "Always": Always, "LeadsTo": LeadsTo,
            "FunctionApp": FunctionApp, "Except": Except,
        }
        exec(code, namespace)
        if "spec" not in namespace:
            raise ValueError("LLM code did not assign a `spec` variable")
        return namespace["spec"]

    def generate(self, description: str, max_retries: int = 3) -> tuple[str, str]:
        """
        Generate a TLA+ spec from a natural language description.
        Returns (tla_source, python_code).
        """
        prompt = f"""Generate a TLA+ spec for the following system:

{description}

Return Python code using the TLAForge builder library that creates a complete spec.
"""
        last_error = None

        for attempt in range(max_retries):
            if attempt == 0:
                message = prompt
            else:
                message = f"""The previous code had an error: {last_error}

Please fix the Python code. Remember:
- Assign the result to `spec`
- Every transition must account for all variables
- Use Unchanged() for vars not modified
- Return ONLY the Python code block
"""

            print(f"  [attempt {attempt + 1}] Calling Claude...")
            response = self._call_claude(message)
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": response})

            code = self._extract_code(response)

            try:
                spec = self._exec_code(code)
                tla = spec.emit()
                print(f"  [attempt {attempt + 1}] Success!")
                return tla, code
            except Exception as e:
                last_error = str(e)
                print(f"  [attempt {attempt + 1}] Error: {e}")
                continue

        raise RuntimeError(f"Failed after {max_retries} attempts. Last error: {last_error}")

    def refine(self, feedback: str) -> tuple[str, str]:
        """
        Refine the previously generated spec based on feedback.
        Continues the conversation so the LLM has context.
        """
        message = f"""Please update the spec based on this feedback:

{feedback}

Return the complete updated Python code block.
"""
        response = self._call_claude(message)
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": response})

        code = self._extract_code(response)
        spec = self._exec_code(code)
        tla = spec.emit()
        return tla, code
