"""Typed draft, patch, and session-facing schemas for TLAForge."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator


ScalarType = Literal["int", "bool", "string"]
QuestionStatus = Literal["open", "resolved"]
RuleKind = Literal["helper", "invariant", "liveness"]
BinaryOperator = Literal["=", "!=", "<", "<=", ">", ">=", "+", "-", "in", "not_in"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def _require_non_empty(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value


class ConversationMessage(StrictModel):
    role: Literal["user", "assistant"]
    content: str

    @field_validator("content")
    @classmethod
    def _validate_content(cls, value: str) -> str:
        return _require_non_empty(value, "content")


class StateDraft(StrictModel):
    name: str
    terminal: bool = False
    description: str | None = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _require_non_empty(value, "state name")


class VariableDraft(StrictModel):
    name: str
    type: ScalarType
    initial: int | bool | str | None = None
    description: str | None = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _require_non_empty(value, "variable name")

    @field_validator("initial")
    @classmethod
    def _validate_initial(cls, value: int | bool | str | None, info: ValidationInfo):
        variable_type = info.data.get("type")
        if value is None or variable_type is None:
            return value
        if variable_type == "bool" and isinstance(value, bool):
            return value
        if variable_type == "int" and isinstance(value, int) and not isinstance(value, bool):
            return value
        if variable_type == "string" and isinstance(value, str):
            return value
        raise ValueError(f"initial value does not match variable type {variable_type!r}")


class RefExpr(StrictModel):
    kind: Literal["ref"] = "ref"
    name: str

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _require_non_empty(value, "reference name")


class StringExpr(StrictModel):
    kind: Literal["string"] = "string"
    value: str


class IntExpr(StrictModel):
    kind: Literal["int"] = "int"
    value: int


class BoolExpr(StrictModel):
    kind: Literal["bool"] = "bool"
    value: bool


class BinaryExpr(StrictModel):
    kind: Literal["binary"] = "binary"
    op: BinaryOperator
    left: ExprDraft
    right: ExprDraft


class AndExpr(StrictModel):
    kind: Literal["and"] = "and"
    items: list[ExprDraft] = Field(min_length=1)


class OrExpr(StrictModel):
    kind: Literal["or"] = "or"
    items: list[ExprDraft] = Field(min_length=1)


class NotExpr(StrictModel):
    kind: Literal["not"] = "not"
    item: ExprDraft


ExprDraft = Annotated[
    RefExpr | StringExpr | IntExpr | BoolExpr | BinaryExpr | AndExpr | OrExpr | NotExpr,
    Field(discriminator="kind"),
]


class AssignmentDraft(StrictModel):
    target: str
    value: ExprDraft

    @field_validator("target")
    @classmethod
    def _validate_target(cls, value: str) -> str:
        return _require_non_empty(value, "assignment target")


class TransitionDraft(StrictModel):
    name: str
    from_state: str
    to_state: str
    guards: list[ExprDraft] = Field(default_factory=list)
    assignments: list[AssignmentDraft] = Field(default_factory=list)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _require_non_empty(value, "transition name")

    @field_validator("from_state", "to_state")
    @classmethod
    def _validate_state_name(cls, value: str) -> str:
        return _require_non_empty(value, "transition state name")


class RuleDraft(StrictModel):
    name: str
    kind: RuleKind
    expr: ExprDraft
    description: str | None = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _require_non_empty(value, "rule name")


class OpenQuestion(StrictModel):
    id: str
    text: str
    required: bool = False
    status: QuestionStatus = "open"
    answer: str | None = None

    @field_validator("id", "text")
    @classmethod
    def _validate_fields(cls, value: str, info: ValidationInfo) -> str:
        return _require_non_empty(value, info.field_name.replace("_", " "))

    @model_validator(mode="after")
    def _validate_resolution(self) -> OpenQuestion:
        if self.status == "resolved" and self.answer is not None and not self.answer.strip():
            raise ValueError("resolved answers must not be empty")
        return self


class MachineDraft(StrictModel):
    module_name: str | None = None
    summary: str | None = None
    state_var: str = "state"
    states: list[StateDraft] = Field(default_factory=list)
    initial_state: str | None = None
    variables: list[VariableDraft] = Field(default_factory=list)
    transitions: list[TransitionDraft] = Field(default_factory=list)
    rules: list[RuleDraft] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)

    @field_validator("state_var")
    @classmethod
    def _validate_state_var(cls, value: str) -> str:
        return _require_non_empty(value, "state variable name")


class SetModuleNameOp(StrictModel):
    op: Literal["set_module_name"] = "set_module_name"
    module_name: str

    @field_validator("module_name")
    @classmethod
    def _validate_module_name(cls, value: str) -> str:
        return _require_non_empty(value, "module name")


class SetSummaryOp(StrictModel):
    op: Literal["set_summary"] = "set_summary"
    summary: str | None = None


class PutStateOp(StrictModel):
    op: Literal["put_state"] = "put_state"
    state: StateDraft


class RemoveStateOp(StrictModel):
    op: Literal["remove_state"] = "remove_state"
    name: str

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _require_non_empty(value, "state name")


class RenameStateOp(StrictModel):
    op: Literal["rename_state"] = "rename_state"
    old_name: str
    new_name: str

    @field_validator("old_name", "new_name")
    @classmethod
    def _validate_name(cls, value: str, info: ValidationInfo) -> str:
        return _require_non_empty(value, info.field_name.replace("_", " "))


class SetInitialStateOp(StrictModel):
    op: Literal["set_initial_state"] = "set_initial_state"
    initial_state: str | None = None


class PutVariableOp(StrictModel):
    op: Literal["put_variable"] = "put_variable"
    variable: VariableDraft


class RemoveVariableOp(StrictModel):
    op: Literal["remove_variable"] = "remove_variable"
    name: str

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _require_non_empty(value, "variable name")


class RenameVariableOp(StrictModel):
    op: Literal["rename_variable"] = "rename_variable"
    old_name: str
    new_name: str

    @field_validator("old_name", "new_name")
    @classmethod
    def _validate_name(cls, value: str, info: ValidationInfo) -> str:
        return _require_non_empty(value, info.field_name.replace("_", " "))


class PutTransitionOp(StrictModel):
    op: Literal["put_transition"] = "put_transition"
    transition: TransitionDraft


class RemoveTransitionOp(StrictModel):
    op: Literal["remove_transition"] = "remove_transition"
    name: str

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _require_non_empty(value, "transition name")


class PutRuleOp(StrictModel):
    op: Literal["put_rule"] = "put_rule"
    rule: RuleDraft


class RemoveRuleOp(StrictModel):
    op: Literal["remove_rule"] = "remove_rule"
    name: str

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _require_non_empty(value, "rule name")


class AddAssumptionOp(StrictModel):
    op: Literal["add_assumption"] = "add_assumption"
    text: str

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        return _require_non_empty(value, "assumption text")


class RemoveAssumptionOp(StrictModel):
    op: Literal["remove_assumption"] = "remove_assumption"
    text: str

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        return _require_non_empty(value, "assumption text")


class AddOpenQuestionOp(StrictModel):
    op: Literal["add_open_question"] = "add_open_question"
    question: OpenQuestion


class ResolveOpenQuestionOp(StrictModel):
    op: Literal["resolve_open_question"] = "resolve_open_question"
    question_id: str
    answer: str | None = None

    @field_validator("question_id")
    @classmethod
    def _validate_question_id(cls, value: str) -> str:
        return _require_non_empty(value, "question id")


PatchOperation = Annotated[
    SetModuleNameOp
    | SetSummaryOp
    | PutStateOp
    | RemoveStateOp
    | RenameStateOp
    | SetInitialStateOp
    | PutVariableOp
    | RemoveVariableOp
    | RenameVariableOp
    | PutTransitionOp
    | RemoveTransitionOp
    | PutRuleOp
    | RemoveRuleOp
    | AddAssumptionOp
    | RemoveAssumptionOp
    | AddOpenQuestionOp
    | ResolveOpenQuestionOp,
    Field(discriminator="op"),
]


class DraftPatch(StrictModel):
    operations: list[PatchOperation] = Field(default_factory=list)


class ValidationIssue(StrictModel):
    severity: Literal["error", "warning"] = "error"
    code: str
    message: str
    path: str | None = None
    blocking: bool = True

    @classmethod
    def error(cls, *, code: str, message: str, path: str | None = None) -> ValidationIssue:
        return cls(code=code, message=message, path=path, severity="error", blocking=True)


class ValidationResult(StrictModel):
    issues: list[ValidationIssue] = Field(default_factory=list)
    ready: bool = False

    @classmethod
    def from_issues(cls, issues: list[ValidationIssue]) -> ValidationResult:
        return cls(issues=issues, ready=not any(issue.blocking for issue in issues))


class AssistantTurn(StrictModel):
    reply: str
    patch: DraftPatch = Field(default_factory=DraftPatch)

    @field_validator("reply")
    @classmethod
    def _validate_reply(cls, value: str) -> str:
        return _require_non_empty(value, "assistant reply")


class SessionTurnResult(StrictModel):
    reply: str
    patch: DraftPatch
    draft: MachineDraft
    validation: ValidationResult
    ready_for_handoff: bool


class HandoffArtifact(StrictModel):
    module_name: str
    tla_source: str
    summary: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    validation: ValidationResult


BinaryExpr.model_rebuild()
AndExpr.model_rebuild()
OrExpr.model_rebuild()
NotExpr.model_rebuild()
