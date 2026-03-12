"""Deterministic compilation from structured drafts to builder objects."""

from __future__ import annotations

from .builder import (
    And,
    BinOp,
    BoolLit,
    Definition,
    Expr,
    IntLit,
    Not,
    Or,
    PrimedVar,
    StateMachineSpec,
    StateTransition,
    StringLit,
    Var,
)
from .draft import (
    AndExpr,
    BinaryExpr,
    BoolExpr,
    ExprDraft,
    IntExpr,
    MachineDraft,
    NotExpr,
    OrExpr,
    RefExpr,
    StringExpr,
)
from .errors import DraftNotReadyError
from .validation import DraftValidator


class DraftCompiler:
    """Compile validated drafts into deterministic builder objects and TLA+."""

    def compile(self, draft: MachineDraft) -> StateMachineSpec:
        validation = DraftValidator.validate(draft)
        if not validation.ready:
            raise DraftNotReadyError(validation)

        assert draft.module_name is not None
        spec = StateMachineSpec(
            module_name=draft.module_name,
            state_var=draft.state_var,
            aux_vars=[variable.name for variable in draft.variables],
            aux_init={
                variable.name: self._compile_scalar_initial(variable.initial)
                for variable in draft.variables
            },
            states=[state.name for state in draft.states],
            initial_state=draft.initial_state,
            terminal_states=[state.name for state in draft.states if state.terminal],
        )

        for transition in draft.transitions:
            assigned_targets = {assignment.target for assignment in transition.assignments}
            spec.transitions.append(
                StateTransition(
                    name=transition.name,
                    guards=[
                        BinOp(Var(draft.state_var), "=", StringLit(transition.from_state)),
                        *[self._compile_expr(expr) for expr in transition.guards],
                    ],
                    updates=[
                        BinOp(PrimedVar(draft.state_var), "=", StringLit(transition.to_state)),
                        *[
                            BinOp(PrimedVar(assignment.target), "=", self._compile_expr(assignment.value))
                            for assignment in transition.assignments
                        ],
                    ],
                    unchanged=[
                        variable.name
                        for variable in draft.variables
                        if variable.name not in assigned_targets
                    ],
                    comment=transition.description,
                )
            )

        for rule in draft.rules:
            definition = Definition(
                name=rule.name,
                body=self._compile_expr(rule.expr),
                comment=rule.description,
            )
            if rule.kind == "helper":
                spec.helpers.append(definition)
            elif rule.kind == "invariant":
                spec.invariants.append(definition)
            elif rule.kind == "liveness":
                spec.liveness.append(definition)
            else:
                raise AssertionError(f"Unhandled rule kind: {rule.kind}")

        spec.validate()
        return spec

    def emit(self, draft: MachineDraft) -> str:
        return self.compile(draft).emit()

    def _compile_scalar_initial(self, value: int | bool | str | None) -> Expr:
        if isinstance(value, bool):
            return BoolLit(value)
        if isinstance(value, int):
            return IntLit(value)
        if isinstance(value, str):
            return StringLit(value)
        raise AssertionError(f"Unsupported initial value: {value!r}")

    def _compile_expr(self, expr: ExprDraft) -> Expr:
        if isinstance(expr, RefExpr):
            return Var(expr.name)
        if isinstance(expr, StringExpr):
            return StringLit(expr.value)
        if isinstance(expr, IntExpr):
            return IntLit(expr.value)
        if isinstance(expr, BoolExpr):
            return BoolLit(expr.value)
        if isinstance(expr, BinaryExpr):
            op = {
                "=": "=",
                "!=": "#",
                "<": "<",
                "<=": "<=",
                ">": ">",
                ">=": ">=",
                "+": "+",
                "-": "-",
                "in": "\\in",
                "not_in": "\\notin",
            }[expr.op]
            return BinOp(self._compile_expr(expr.left), op, self._compile_expr(expr.right))
        if isinstance(expr, AndExpr):
            return And(*(self._compile_expr(item) for item in expr.items))
        if isinstance(expr, OrExpr):
            return Or(*(self._compile_expr(item) for item in expr.items))
        if isinstance(expr, NotExpr):
            return Not(self._compile_expr(expr.item))
        raise AssertionError(f"Unhandled expression draft: {expr!r}")
