"""
TLAForge - A Python library for programmatically constructing TLA+ specs.
The LLM calls these classes instead of generating raw TLA+ text.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

class Expr:
    """Base for all TLA+ expressions."""
    def emit(self) -> str:
        raise NotImplementedError


class Raw(Expr):
    """Escape hatch: raw TLA+ string when no builder covers it."""
    def __init__(self, text: str):
        self.text = text

    def emit(self) -> str:
        return self.text


class Var(Expr):
    def __init__(self, name: str):
        self.name = name

    def emit(self) -> str:
        return self.name


class PrimedVar(Expr):
    """Represents var' (post-state variable)."""
    def __init__(self, name: str):
        self.name = name

    def emit(self) -> str:
        return f"{self.name}'"


class IntLit(Expr):
    def __init__(self, value: int):
        self.value = value

    def emit(self) -> str:
        return str(self.value)


class BoolLit(Expr):
    def __init__(self, value: bool):
        self.value = value

    def emit(self) -> str:
        return "TRUE" if self.value else "FALSE"


class StringLit(Expr):
    def __init__(self, value: str):
        self.value = value

    def emit(self) -> str:
        return f'"{self.value}"'


class SetLit(Expr):
    """{ e1, e2, ... }"""
    def __init__(self, *elements: Expr):
        self.elements = list(elements)

    def emit(self) -> str:
        if not self.elements:
            return "{}"
        inner = ", ".join(e.emit() for e in self.elements)
        return "{" + inner + "}"


class SetOf(Expr):
    r"""{ x \in S : P(x) }"""
    def __init__(self, var: str, domain: Expr, predicate: Expr):
        self.var = var
        self.domain = domain
        self.predicate = predicate

    def emit(self) -> str:
        return f"{{  {self.var} \\in {self.domain.emit()} : {self.predicate.emit()}  }}"


class FunctionApp(Expr):
    """f[arg]"""
    def __init__(self, func: Expr, arg: Expr):
        self.func = func
        self.arg = arg

    def emit(self) -> str:
        return f"{self.func.emit()}[{self.arg.emit()}]"


class Except(Expr):
    """[f EXCEPT ![key] = val]"""
    def __init__(self, func: Expr, key: Expr, val: Expr):
        self.func = func
        self.key = key
        self.val = val

    def emit(self) -> str:
        return f"[{self.func.emit()} EXCEPT ![{self.key.emit()}] = {self.val.emit()}]"


class BinOp(Expr):
    def __init__(self, left: Expr, op: str, right: Expr):
        self.left = left
        self.op = op
        self.right = right

    def emit(self) -> str:
        return f"{self.left.emit()} {self.op} {self.right.emit()}"


class And(Expr):
    """Conjunct list: /\\ e1 /\\ e2 ..."""
    def __init__(self, *exprs: Expr):
        self.exprs = list(exprs)

    def add(self, expr: Expr) -> And:
        self.exprs.append(expr)
        return self

    def emit(self) -> str:
        if len(self.exprs) == 1:
            return self.exprs[0].emit()
        lines = [f"/\\ {e.emit()}" for e in self.exprs]
        return "\n    ".join(lines)


class Or(Expr):
    """Disjunct list: \\/ e1 \\/ e2 ..."""
    def __init__(self, *exprs: Expr):
        self.exprs = list(exprs)

    def emit(self) -> str:
        if len(self.exprs) == 1:
            return self.exprs[0].emit()
        lines = [f"\\/ {e.emit()}" for e in self.exprs]
        return "\n    ".join(lines)


class Not(Expr):
    def __init__(self, expr: Expr):
        self.expr = expr

    def emit(self) -> str:
        return f"~{self.expr.emit()}"


class Implies(Expr):
    def __init__(self, antecedent: Expr, consequent: Expr):
        self.antecedent = antecedent
        self.consequent = consequent

    def emit(self) -> str:
        return f"{self.antecedent.emit()} => {self.consequent.emit()}"


class Unchanged(Expr):
    """UNCHANGED <<v1, v2, ...>>"""
    def __init__(self, *vars: str):
        self.vars = list(vars)

    def emit(self) -> str:
        if len(self.vars) == 1:
            return f"UNCHANGED {self.vars[0]}"
        inner = ", ".join(self.vars)
        return f"UNCHANGED <<{inner}>>"


class Forall(Expr):
    """\\A x \\in S : P"""
    def __init__(self, var: str, domain: Expr, body: Expr):
        self.var = var
        self.domain = domain
        self.body = body

    def emit(self) -> str:
        return f"\\A {self.var} \\in {self.domain.emit()} : {self.body.emit()}"


class Exists(Expr):
    """\\E x \\in S : P"""
    def __init__(self, var: str, domain: Expr, body: Expr):
        self.var = var
        self.domain = domain
        self.body = body

    def emit(self) -> str:
        return f"\\E {self.var} \\in {self.domain.emit()} : {self.body.emit()}"


class LeadsTo(Expr):
    """P ~> Q (liveness)"""
    def __init__(self, p: Expr, q: Expr):
        self.p = p
        self.q = q

    def emit(self) -> str:
        return f"{self.p.emit()} ~> {self.q.emit()}"


class Eventually(Expr):
    """<> P"""
    def __init__(self, p: Expr):
        self.p = p

    def emit(self) -> str:
        return f"<>({self.p.emit()})"


class Always(Expr):
    """[] P"""
    def __init__(self, p: Expr):
        self.p = p

    def emit(self) -> str:
        return f"[]({self.p.emit()})"


# ---------------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------------

@dataclass
class Definition:
    name: str
    params: List[str] = field(default_factory=list)
    body: Expr = field(default_factory=lambda: Raw("TRUE"))
    comment: Optional[str] = None

    def emit(self) -> str:
        lines = []
        if self.comment:
            lines.append(f"\\* {self.comment}")
        sig = self.name
        if self.params:
            sig += f"({', '.join(self.params)})"
        lines.append(f"{sig} ==")
        lines.append(f"    {self.body.emit()}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# State Machine builder — the primary high-level API
# ---------------------------------------------------------------------------

@dataclass
class StateTransition:
    name: str
    guards: List[Expr] = field(default_factory=list)
    updates: List[Expr] = field(default_factory=list)
    unchanged: List[str] = field(default_factory=list)
    comment: Optional[str] = None

    def to_definition(self) -> Definition:
        body_parts = self.guards + self.updates
        if self.unchanged:
            body_parts.append(Unchanged(*self.unchanged))
        body = And(*body_parts) if body_parts else Raw("TRUE")
        return Definition(
            name=self.name,
            body=body,
            comment=self.comment
        )


@dataclass
class StateMachineSpec:
    """
    High-level builder for a state machine TLA+ spec.
    The LLM populates this object; the library emits valid TLA+.
    """
    module_name: str
    extends: List[str] = field(default_factory=lambda: ["Integers", "FiniteSets", "Sequences"])

    # Variables
    state_var: str = "state"
    aux_vars: List[str] = field(default_factory=list)
    aux_init: Dict[str, Expr] = field(default_factory=dict)

    # States
    states: List[str] = field(default_factory=list)
    initial_state: Optional[str] = None
    terminal_states: List[str] = field(default_factory=list)

    # Constants
    constants: List[str] = field(default_factory=list)

    # Transitions
    transitions: List[StateTransition] = field(default_factory=list)

    # Invariants
    invariants: List[Definition] = field(default_factory=list)

    # Liveness properties
    liveness: List[Definition] = field(default_factory=list)

    # Extra definitions (helpers, type invariants, etc.)
    helpers: List[Definition] = field(default_factory=list)

    def all_vars(self) -> List[str]:
        return [self.state_var] + self.aux_vars

    def _validate_aux_init(self, errors: List[str] | None = None) -> None:
        missing = [name for name in self.aux_vars if name not in self.aux_init]
        extras = [name for name in self.aux_init if name not in self.aux_vars]
        local_errors = []

        if missing:
            local_errors.append(
                "missing initial values for auxiliary variables: "
                + ", ".join(sorted(missing))
            )
        if extras:
            local_errors.append(
                "aux_init includes names not declared in aux_vars: "
                + ", ".join(sorted(extras))
            )
        if errors is not None:
            errors.extend(local_errors)
            return
        if local_errors:
            raise ValueError("; ".join(local_errors))

    def _extract_transition_edge(self, transition: StateTransition) -> tuple[str | None, str | None]:
        from_state = None
        to_state = None
        if transition.guards:
            first_guard = transition.guards[0]
            if (
                isinstance(first_guard, BinOp)
                and isinstance(first_guard.left, Var)
                and first_guard.left.name == self.state_var
                and first_guard.op == "="
                and isinstance(first_guard.right, StringLit)
            ):
                from_state = first_guard.right.value

        for update in transition.updates:
            if (
                isinstance(update, BinOp)
                and isinstance(update.left, PrimedVar)
                and update.left.name == self.state_var
                and update.op == "="
                and isinstance(update.right, StringLit)
            ):
                to_state = update.right.value
                break
        return from_state, to_state

    def validate(self) -> None:
        errors: List[str] = []

        if not self.module_name.strip():
            errors.append("module_name must not be empty")

        self._validate_aux_init(errors)

        if self.state_var in self.aux_vars:
            errors.append(f"state_var {self.state_var!r} may not also appear in aux_vars")

        for label, values in (
            ("states", self.states),
            ("aux_vars", self.aux_vars),
            ("terminal_states", self.terminal_states),
            ("transitions", [transition.name for transition in self.transitions]),
        ):
            duplicates = [value for value, count in Counter(values).items() if count > 1]
            if duplicates:
                errors.append(f"duplicate values in {label}: {', '.join(sorted(duplicates))}")

        if self.initial_state is not None and self.initial_state not in self.states:
            errors.append(f"initial_state {self.initial_state!r} is not declared in states")

        unknown_terminal_states = sorted(set(self.terminal_states) - set(self.states))
        if unknown_terminal_states:
            errors.append(
                "terminal_states reference unknown states: " + ", ".join(unknown_terminal_states)
            )

        for transition in self.transitions:
            from_state, to_state = self._extract_transition_edge(transition)
            if from_state is not None and from_state not in self.states:
                errors.append(
                    f"transition {transition.name!r} references unknown from_state {from_state!r}"
                )
            if to_state is not None and to_state not in self.states:
                errors.append(
                    f"transition {transition.name!r} references unknown to_state {to_state!r}"
                )
            if from_state is not None and from_state in self.terminal_states:
                errors.append(
                    f"transition {transition.name!r} leaves terminal state {from_state!r}"
                )

        if errors:
            raise ValueError("; ".join(errors))

    def _emit_header(self) -> str:
        bar = "-" * 20
        lines = [f"{bar} MODULE {self.module_name} {bar}"]
        if self.extends:
            lines.append(f"EXTENDS {', '.join(self.extends)}")
        return "\n".join(lines)

    def _emit_constants(self) -> str:
        if not self.constants:
            return ""
        return "CONSTANTS\n    " + ",\n    ".join(self.constants)

    def _emit_variables(self) -> str:
        return "VARIABLES\n    " + ",\n    ".join(self.all_vars())

    def _emit_states_set(self) -> str:
        states_str = ", ".join(f'"{s}"' for s in self.states)
        return f"States == {{{states_str}}}"

    def _emit_init(self) -> str:
        self._validate_aux_init()
        lines = ["Init =="]
        if self.initial_state:
            lines.append(f'    /\\ {self.state_var} = "{self.initial_state}"')
        for v in self.aux_vars:
            lines.append(f"    /\\ {v} = {self.aux_init[v].emit()}")
        return "\n".join(lines)

    def _emit_valid_transitions(self) -> str:
        """Emit a ValidTransition operator from the transition graph."""
        if not self.transitions:
            return ""

        # Collect from/to pairs
        from_map: Dict[str, List[str]] = {}
        for t in self.transitions:
            # Try to extract from/to from guards
            # Convention: first guard often checks current state
            pass

        # Just emit the transitions as individual actions
        return ""

    def _emit_next(self) -> str:
        if not self.transitions:
            return "Next == FALSE  \\* No transitions defined"
        transition_names = "\n    \\/ ".join(t.name for t in self.transitions)
        return f"Next ==\n    \\/ {transition_names}"

    def _emit_spec(self) -> str:
        vars_tuple = "<<" + ", ".join(self.all_vars()) + ">>"
        return (
            f"Spec ==\n"
            f"    /\\ Init\n"
            f"    /\\ [][Next]_{vars_tuple}\n"
            f"    /\\ WF_{vars_tuple}(Next)"
        )

    def emit(self) -> str:
        self.validate()
        sections = [
            self._emit_header(),
            "",
            self._emit_constants() if self.constants else "",
            self._emit_variables(),
            "",
            "\\* --- States ---",
            self._emit_states_set(),
            "",
            "\\* --- Helpers ---",
            *[d.emit() + "\n" for d in self.helpers],
            "\\* --- Initial State ---",
            self._emit_init(),
            "",
            "\\* --- Transitions ---",
            *[t.to_definition().emit() + "\n" for t in self.transitions],
            "\\* --- Next State ---",
            self._emit_next(),
            "",
            "\\* --- Invariants ---",
            *[d.emit() + "\n" for d in self.invariants],
            "\\* --- Liveness ---",
            *[d.emit() + "\n" for d in self.liveness],
            "\\* --- Spec ---",
            self._emit_spec(),
            "",
            "=" * 40,
        ]
        return "\n".join(s for s in sections if s is not None)
