"""Semantic validation for structured machine drafts."""

from __future__ import annotations

from collections import Counter

from .draft import (
    AndExpr,
    BinaryExpr,
    BoolExpr,
    ExprDraft,
    IntExpr,
    MachineDraft,
    NotExpr,
    OpenQuestion,
    OrExpr,
    RefExpr,
    RuleDraft,
    StringExpr,
    TransitionDraft,
    ValidationIssue,
    ValidationResult,
    VariableDraft,
)


ExprType = str


class DraftValidator:
    """Validate a structured draft for semantic correctness and handoff readiness."""

    @classmethod
    def validate(cls, draft: MachineDraft) -> ValidationResult:
        issues: list[ValidationIssue] = []
        state_names = [state.name for state in draft.states]
        variable_names = [variable.name for variable in draft.variables]
        transition_names = [transition.name for transition in draft.transitions]
        rule_names = [rule.name for rule in draft.rules]
        question_ids = [question.id for question in draft.open_questions]

        cls._collect_duplicates(issues, state_names, "duplicate_state", "states")
        cls._collect_duplicates(issues, variable_names, "duplicate_variable", "variables")
        cls._collect_duplicates(issues, transition_names, "duplicate_transition", "transitions")
        cls._collect_duplicates(issues, rule_names, "duplicate_rule", "rules")
        cls._collect_duplicates(issues, question_ids, "duplicate_open_question", "open_questions", key="id")
        cls._collect_duplicates(issues, draft.assumptions, "duplicate_assumption", "assumptions")

        known_states = set(state_names)
        terminal_states = {state.name for state in draft.states if state.terminal}
        variables = {variable.name: variable for variable in draft.variables}
        symbols: dict[str, ExprType] = {"States": "state_set", draft.state_var: "state"}
        symbols.update({name: variable.type for name, variable in variables.items()})

        if draft.module_name is None or not draft.module_name.strip():
            issues.append(
                ValidationIssue.error(
                    code="missing_module_name",
                    message="module_name is required before handoff",
                    path="module_name",
                )
            )

        if draft.initial_state is None:
            issues.append(
                ValidationIssue.error(
                    code="missing_initial_state",
                    message="initial_state is required before handoff",
                    path="initial_state",
                )
            )
        elif draft.initial_state not in known_states:
            issues.append(
                ValidationIssue.error(
                    code="unknown_initial_state",
                    message=f"initial_state {draft.initial_state!r} is not declared",
                    path="initial_state",
                )
            )

        for index, variable in enumerate(draft.variables):
            cls._validate_variable(variable, issues, index)

        for index, transition in enumerate(draft.transitions):
            cls._validate_transition(
                draft=draft,
                transition=transition,
                issues=issues,
                index=index,
                known_states=known_states,
                terminal_states=terminal_states,
                symbols=symbols,
            )

        for index, rule in enumerate(draft.rules):
            cls._validate_rule(
                draft=draft,
                rule=rule,
                issues=issues,
                index=index,
                known_states=known_states,
                symbols=symbols,
            )

        for index, question in enumerate(draft.open_questions):
            cls._validate_open_question(question, issues, index)

        return ValidationResult.from_issues(issues)

    @staticmethod
    def _collect_duplicates(
        issues: list[ValidationIssue],
        values: list[str],
        code: str,
        path_prefix: str,
        *,
        key: str = "name",
    ) -> None:
        counts = Counter(values)
        for value, count in counts.items():
            if count > 1:
                issues.append(
                    ValidationIssue.error(
                        code=code,
                        message=f"{value!r} appears multiple times",
                        path=path_prefix,
                    )
                )

    @classmethod
    def _validate_variable(
        cls,
        variable: VariableDraft,
        issues: list[ValidationIssue],
        index: int,
    ) -> None:
        if variable.initial is None:
            issues.append(
                ValidationIssue.error(
                    code="missing_variable_initial",
                    message=f"variable {variable.name!r} is missing an initial value",
                    path=f"variables[{index}].initial",
                )
            )

    @classmethod
    def _validate_transition(
        cls,
        *,
        draft: MachineDraft,
        transition: TransitionDraft,
        issues: list[ValidationIssue],
        index: int,
        known_states: set[str],
        terminal_states: set[str],
        symbols: dict[str, ExprType],
    ) -> None:
        if transition.from_state not in known_states:
            issues.append(
                ValidationIssue.error(
                    code="unknown_transition_state",
                    message=f"transition {transition.name!r} references unknown from_state {transition.from_state!r}",
                    path=f"transitions[{index}].from_state",
                )
            )
        if transition.to_state not in known_states:
            issues.append(
                ValidationIssue.error(
                    code="unknown_transition_state",
                    message=f"transition {transition.name!r} references unknown to_state {transition.to_state!r}",
                    path=f"transitions[{index}].to_state",
                )
            )
        if transition.from_state in terminal_states:
            issues.append(
                ValidationIssue.error(
                    code="terminal_state_outgoing_transition",
                    message=f"terminal state {transition.from_state!r} cannot have outgoing transitions",
                    path=f"transitions[{index}].from_state",
                )
            )

        seen_targets: set[str] = set()
        for assignment_index, assignment in enumerate(transition.assignments):
            if assignment.target not in symbols or assignment.target in {"States", draft.state_var}:
                issues.append(
                    ValidationIssue.error(
                        code="unknown_assignment_target",
                        message=f"assignment target {assignment.target!r} is not a declared variable",
                        path=f"transitions[{index}].assignments[{assignment_index}].target",
                    )
                )
            elif assignment.target in seen_targets:
                issues.append(
                    ValidationIssue.error(
                        code="duplicate_assignment_target",
                        message=f"assignment target {assignment.target!r} appears multiple times",
                        path=f"transitions[{index}].assignments[{assignment_index}].target",
                    )
                )
            seen_targets.add(assignment.target)
            cls._validate_expr(
                draft=draft,
                expr=assignment.value,
                issues=issues,
                path=f"transitions[{index}].assignments[{assignment_index}].value",
                known_states=known_states,
                symbols=symbols,
            )

        for guard_index, guard in enumerate(transition.guards):
            cls._validate_expr(
                draft=draft,
                expr=guard,
                issues=issues,
                path=f"transitions[{index}].guards[{guard_index}]",
                known_states=known_states,
                symbols=symbols,
                expected="bool",
            )

    @classmethod
    def _validate_rule(
        cls,
        *,
        draft: MachineDraft,
        rule: RuleDraft,
        issues: list[ValidationIssue],
        index: int,
        known_states: set[str],
        symbols: dict[str, ExprType],
    ) -> None:
        cls._validate_expr(
            draft=draft,
            expr=rule.expr,
            issues=issues,
            path=f"rules[{index}].expr",
            known_states=known_states,
            symbols=symbols,
            expected="bool",
        )

    @staticmethod
    def _validate_open_question(
        question: OpenQuestion,
        issues: list[ValidationIssue],
        index: int,
    ) -> None:
        if question.required and question.status != "resolved":
            issues.append(
                ValidationIssue.error(
                    code="required_open_question",
                    message=f"required open question {question.id!r} is unresolved",
                    path=f"open_questions[{index}]",
                )
            )

    @classmethod
    def _validate_expr(
        cls,
        *,
        draft: MachineDraft,
        expr: ExprDraft,
        issues: list[ValidationIssue],
        path: str,
        known_states: set[str],
        symbols: dict[str, ExprType],
        expected: ExprType | None = None,
    ) -> ExprType | None:
        expr_type = cls._infer_expr_type(
            draft=draft,
            expr=expr,
            issues=issues,
            path=path,
            known_states=known_states,
            symbols=symbols,
        )
        if expected is not None and expr_type is not None and expr_type != expected:
            issues.append(
                ValidationIssue.error(
                    code="unexpected_expression_type",
                    message=f"expression must evaluate to {expected}, got {expr_type}",
                    path=path,
                )
            )
        return expr_type

    @classmethod
    def _infer_expr_type(
        cls,
        *,
        draft: MachineDraft,
        expr: ExprDraft,
        issues: list[ValidationIssue],
        path: str,
        known_states: set[str],
        symbols: dict[str, ExprType],
    ) -> ExprType | None:
        if isinstance(expr, RefExpr):
            if expr.name not in symbols:
                issues.append(
                    ValidationIssue.error(
                        code="unknown_symbol",
                        message=f"reference {expr.name!r} is not declared",
                        path=path,
                    )
                )
                return None
            return symbols[expr.name]

        if isinstance(expr, StringExpr):
            return "string"

        if isinstance(expr, IntExpr):
            return "int"

        if isinstance(expr, BoolExpr):
            return "bool"

        if isinstance(expr, BinaryExpr):
            left_type = cls._infer_expr_type(
                draft=draft,
                expr=expr.left,
                issues=issues,
                path=f"{path}.left",
                known_states=known_states,
                symbols=symbols,
            )
            right_type = cls._infer_expr_type(
                draft=draft,
                expr=expr.right,
                issues=issues,
                path=f"{path}.right",
                known_states=known_states,
                symbols=symbols,
            )
            return cls._validate_binary_expr(
                draft=draft,
                expr=expr,
                left_type=left_type,
                right_type=right_type,
                issues=issues,
                path=path,
                known_states=known_states,
            )

        if isinstance(expr, AndExpr | OrExpr):
            for item_index, item in enumerate(expr.items):
                item_type = cls._infer_expr_type(
                    draft=draft,
                    expr=item,
                    issues=issues,
                    path=f"{path}.items[{item_index}]",
                    known_states=known_states,
                    symbols=symbols,
                )
                if item_type is not None and item_type != "bool":
                    issues.append(
                        ValidationIssue.error(
                            code="unexpected_expression_type",
                            message="logical expressions require boolean items",
                            path=f"{path}.items[{item_index}]",
                        )
                    )
            return "bool"

        if isinstance(expr, NotExpr):
            item_type = cls._infer_expr_type(
                draft=draft,
                expr=expr.item,
                issues=issues,
                path=f"{path}.item",
                known_states=known_states,
                symbols=symbols,
            )
            if item_type is not None and item_type != "bool":
                issues.append(
                    ValidationIssue.error(
                        code="unexpected_expression_type",
                        message="not expressions require a boolean operand",
                        path=f"{path}.item",
                    )
                )
            return "bool"

        raise AssertionError(f"Unhandled expression draft: {expr!r}")

    @classmethod
    def _validate_binary_expr(
        cls,
        *,
        draft: MachineDraft,
        expr: BinaryExpr,
        left_type: ExprType | None,
        right_type: ExprType | None,
        issues: list[ValidationIssue],
        path: str,
        known_states: set[str],
    ) -> ExprType | None:
        if expr.op in {"+", "-"}:
            cls._require_type_pair(issues, path, left_type, right_type, "int", "arithmetic")
            return "int"

        if expr.op in {"<", "<=", ">", ">="}:
            cls._require_type_pair(issues, path, left_type, right_type, "int", "comparison")
            return "bool"

        if expr.op in {"in", "not_in"}:
            if not isinstance(expr.right, RefExpr) or expr.right.name != "States":
                issues.append(
                    ValidationIssue.error(
                        code="invalid_membership_target",
                        message="membership expressions may only target States in v1",
                        path=f"{path}.right",
                    )
                )
            if not cls._is_state_expr(expr.left, draft.state_var):
                issues.append(
                    ValidationIssue.error(
                        code="invalid_membership_source",
                        message="membership expressions must use the state variable or a state literal",
                        path=f"{path}.left",
                    )
                )
            if isinstance(expr.left, StringExpr) and expr.left.value not in known_states:
                issues.append(
                    ValidationIssue.error(
                        code="unknown_state_literal",
                        message=f"state literal {expr.left.value!r} is not declared",
                        path=f"{path}.left",
                    )
                )
            return "bool"

        if expr.op in {"=", "!="}:
            if not cls._types_compatible_for_equality(left_type, right_type):
                issues.append(
                    ValidationIssue.error(
                        code="incompatible_equality",
                        message=f"cannot compare {left_type or 'unknown'} to {right_type or 'unknown'}",
                        path=path,
                    )
                )
            cls._validate_state_literal_comparison(expr, issues, path, draft.state_var, known_states)
            return "bool"

        raise AssertionError(f"Unhandled binary operator: {expr.op}")

    @staticmethod
    def _require_type_pair(
        issues: list[ValidationIssue],
        path: str,
        left_type: ExprType | None,
        right_type: ExprType | None,
        expected: ExprType,
        context: str,
    ) -> None:
        if left_type == expected and right_type == expected:
            return
        issues.append(
            ValidationIssue.error(
                code="unexpected_expression_type",
                message=f"{context} expressions require {expected} operands",
                path=path,
            )
        )

    @staticmethod
    def _types_compatible_for_equality(left_type: ExprType | None, right_type: ExprType | None) -> bool:
        if left_type is None or right_type is None:
            return False
        if left_type == right_type:
            return True
        compatible_pairs = {("state", "string"), ("string", "state")}
        return (left_type, right_type) in compatible_pairs

    @staticmethod
    def _is_state_expr(expr: ExprDraft, state_var: str) -> bool:
        return isinstance(expr, RefExpr) and expr.name == state_var or isinstance(expr, StringExpr)

    @staticmethod
    def _validate_state_literal_comparison(
        expr: BinaryExpr,
        issues: list[ValidationIssue],
        path: str,
        state_var: str,
        known_states: set[str],
    ) -> None:
        comparisons = (
            (expr.left, expr.right, f"{path}.right"),
            (expr.right, expr.left, f"{path}.left"),
        )
        for side_a, side_b, state_path in comparisons:
            if isinstance(side_a, RefExpr) and side_a.name == state_var and isinstance(side_b, StringExpr):
                if side_b.value not in known_states:
                    issues.append(
                        ValidationIssue.error(
                            code="unknown_state_literal",
                            message=f"state literal {side_b.value!r} is not declared",
                            path=state_path,
                        )
                    )
