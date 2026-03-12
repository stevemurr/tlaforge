"""Deterministic draft patch application."""

from __future__ import annotations

from .draft import (
    AddAssumptionOp,
    AddOpenQuestionOp,
    AndExpr,
    AssignmentDraft,
    BinaryExpr,
    DraftPatch,
    ExprDraft,
    MachineDraft,
    NotExpr,
    OrExpr,
    PatchOperation,
    PutRuleOp,
    PutStateOp,
    PutTransitionOp,
    PutVariableOp,
    RefExpr,
    RemoveAssumptionOp,
    RemoveRuleOp,
    RemoveStateOp,
    RemoveTransitionOp,
    RemoveVariableOp,
    RenameStateOp,
    RenameVariableOp,
    ResolveOpenQuestionOp,
    SetInitialStateOp,
    SetModuleNameOp,
    SetSummaryOp,
    ValidationIssue,
)


def apply_patch_to_draft(
    draft: MachineDraft,
    patch: DraftPatch,
) -> tuple[MachineDraft, list[ValidationIssue]]:
    working = draft.model_copy(deep=True)
    for index, operation in enumerate(patch.operations):
        issue = _apply_operation(working, operation, index)
        if issue is not None:
            return draft.model_copy(deep=True), [issue]
    return working, []


def _apply_operation(
    draft: MachineDraft,
    operation: PatchOperation,
    index: int,
) -> ValidationIssue | None:
    if isinstance(operation, SetModuleNameOp):
        draft.module_name = operation.module_name
        return None
    if isinstance(operation, SetSummaryOp):
        draft.summary = operation.summary
        return None
    if isinstance(operation, PutStateOp):
        _upsert_named(draft.states, operation.state)
        return None
    if isinstance(operation, RemoveStateOp):
        return _remove_state(draft, operation, index)
    if isinstance(operation, RenameStateOp):
        return _rename_state(draft, operation, index)
    if isinstance(operation, SetInitialStateOp):
        draft.initial_state = operation.initial_state
        return None
    if isinstance(operation, PutVariableOp):
        _upsert_named(draft.variables, operation.variable)
        return None
    if isinstance(operation, RemoveVariableOp):
        return _remove_variable(draft, operation, index)
    if isinstance(operation, RenameVariableOp):
        return _rename_variable(draft, operation, index)
    if isinstance(operation, PutTransitionOp):
        _upsert_named(draft.transitions, operation.transition)
        return None
    if isinstance(operation, RemoveTransitionOp):
        return _remove_named(draft.transitions, operation.name, index, "transition")
    if isinstance(operation, PutRuleOp):
        _upsert_named(draft.rules, operation.rule)
        return None
    if isinstance(operation, RemoveRuleOp):
        return _remove_named(draft.rules, operation.name, index, "rule")
    if isinstance(operation, AddAssumptionOp):
        if operation.text in draft.assumptions:
            return _issue(index, "duplicate_assumption", "assumption already exists")
        draft.assumptions.append(operation.text)
        return None
    if isinstance(operation, RemoveAssumptionOp):
        if operation.text not in draft.assumptions:
            return _issue(index, "assumption_not_found", "assumption does not exist")
        draft.assumptions.remove(operation.text)
        return None
    if isinstance(operation, AddOpenQuestionOp):
        if _find_named(draft.open_questions, operation.question.id, attr="id") is not None:
            return _issue(index, "duplicate_open_question", "open question id already exists")
        draft.open_questions.append(operation.question)
        return None
    if isinstance(operation, ResolveOpenQuestionOp):
        existing = _find_named(draft.open_questions, operation.question_id, attr="id")
        if existing is None:
            return _issue(index, "open_question_not_found", "open question does not exist")
        existing.status = "resolved"
        existing.answer = operation.answer
        return None
    raise AssertionError(f"Unhandled patch operation: {operation!r}")


def _remove_state(
    draft: MachineDraft,
    operation: RemoveStateOp,
    index: int,
) -> ValidationIssue | None:
    state_index = _find_index(draft.states, operation.name)
    if state_index is None:
        return _issue(index, "state_not_found", f"state {operation.name!r} does not exist")
    if draft.initial_state == operation.name:
        return _issue(index, "state_in_use", "cannot remove the current initial state")
    if any(
        transition.from_state == operation.name or transition.to_state == operation.name
        for transition in draft.transitions
    ):
        return _issue(index, "state_in_use", "cannot remove a state referenced by transitions")
    draft.states.pop(state_index)
    return None


def _rename_state(
    draft: MachineDraft,
    operation: RenameStateOp,
    index: int,
) -> ValidationIssue | None:
    state_index = _find_index(draft.states, operation.old_name)
    if state_index is None:
        return _issue(index, "state_not_found", f"state {operation.old_name!r} does not exist")
    if _find_index(draft.states, operation.new_name) is not None:
        return _issue(index, "duplicate_state", f"state {operation.new_name!r} already exists")
    draft.states[state_index].name = operation.new_name
    if draft.initial_state == operation.old_name:
        draft.initial_state = operation.new_name
    for transition in draft.transitions:
        if transition.from_state == operation.old_name:
            transition.from_state = operation.new_name
        if transition.to_state == operation.old_name:
            transition.to_state = operation.new_name
    return None


def _remove_variable(
    draft: MachineDraft,
    operation: RemoveVariableOp,
    index: int,
) -> ValidationIssue | None:
    variable_index = _find_index(draft.variables, operation.name)
    if variable_index is None:
        return _issue(index, "variable_not_found", f"variable {operation.name!r} does not exist")
    if _draft_references_variable(draft, operation.name):
        return _issue(index, "variable_in_use", "cannot remove a referenced variable")
    draft.variables.pop(variable_index)
    return None


def _rename_variable(
    draft: MachineDraft,
    operation: RenameVariableOp,
    index: int,
) -> ValidationIssue | None:
    variable_index = _find_index(draft.variables, operation.old_name)
    if variable_index is None:
        return _issue(index, "variable_not_found", f"variable {operation.old_name!r} does not exist")
    if _find_index(draft.variables, operation.new_name) is not None:
        return _issue(index, "duplicate_variable", f"variable {operation.new_name!r} already exists")
    draft.variables[variable_index].name = operation.new_name
    for transition in draft.transitions:
        transition.assignments = [
            AssignmentDraft(
                target=operation.new_name if assignment.target == operation.old_name else assignment.target,
                value=_rename_ref_in_expr(assignment.value, operation.old_name, operation.new_name),
            )
            for assignment in transition.assignments
        ]
        transition.guards = [
            _rename_ref_in_expr(guard, operation.old_name, operation.new_name)
            for guard in transition.guards
        ]
    for rule_index, rule in enumerate(draft.rules):
        draft.rules[rule_index] = rule.model_copy(
            update={"expr": _rename_ref_in_expr(rule.expr, operation.old_name, operation.new_name)}
        )
    return None


def _upsert_named(items: list, item) -> None:
    existing_index = _find_index(items, item.name)
    if existing_index is None:
        items.append(item)
        return
    items[existing_index] = item


def _remove_named(items: list, name: str, index: int, item_type: str) -> ValidationIssue | None:
    existing_index = _find_index(items, name)
    if existing_index is None:
        return _issue(index, f"{item_type}_not_found", f"{item_type} {name!r} does not exist")
    items.pop(existing_index)
    return None


def _find_named(items: list, value: str, *, attr: str = "name"):
    for item in items:
        if getattr(item, attr) == value:
            return item
    return None


def _find_index(items: list, name: str) -> int | None:
    for index, item in enumerate(items):
        if item.name == name:
            return index
    return None


def _issue(index: int, code: str, message: str) -> ValidationIssue:
    return ValidationIssue.error(code=code, message=message, path=f"patch.operations[{index}]")


def _draft_references_variable(draft: MachineDraft, name: str) -> bool:
    for transition in draft.transitions:
        if any(assignment.target == name for assignment in transition.assignments):
            return True
        if any(_expr_references_ref(assignment.value, name) for assignment in transition.assignments):
            return True
        if any(_expr_references_ref(guard, name) for guard in transition.guards):
            return True
    return any(_expr_references_ref(rule.expr, name) for rule in draft.rules)


def _expr_references_ref(expr: ExprDraft, name: str) -> bool:
    if isinstance(expr, RefExpr):
        return expr.name == name
    if isinstance(expr, BinaryExpr):
        return _expr_references_ref(expr.left, name) or _expr_references_ref(expr.right, name)
    if isinstance(expr, AndExpr | OrExpr):
        return any(_expr_references_ref(item, name) for item in expr.items)
    if isinstance(expr, NotExpr):
        return _expr_references_ref(expr.item, name)
    return False


def _rename_ref_in_expr(expr: ExprDraft, old_name: str, new_name: str) -> ExprDraft:
    if isinstance(expr, RefExpr) and expr.name == old_name:
        return RefExpr(name=new_name)
    if isinstance(expr, BinaryExpr):
        return expr.model_copy(
            update={
                "left": _rename_ref_in_expr(expr.left, old_name, new_name),
                "right": _rename_ref_in_expr(expr.right, old_name, new_name),
            }
        )
    if isinstance(expr, AndExpr | OrExpr):
        return expr.model_copy(
            update={"items": [_rename_ref_in_expr(item, old_name, new_name) for item in expr.items]}
        )
    if isinstance(expr, NotExpr):
        return expr.model_copy(update={"item": _rename_ref_in_expr(expr.item, old_name, new_name)})
    return expr
