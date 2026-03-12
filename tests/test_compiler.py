from tlaforge.compiler import DraftCompiler
from tlaforge.draft import (
    BinaryExpr,
    MachineDraft,
    OpenQuestion,
    RefExpr,
    RuleDraft,
    StateDraft,
    StringExpr,
    TransitionDraft,
    VariableDraft,
)
from tlaforge.errors import DraftNotReadyError
from tlaforge.validation import DraftValidator


def _traffic_light_draft() -> MachineDraft:
    return MachineDraft(
        module_name="TrafficLight",
        summary="Simple traffic light cycle",
        states=[
            StateDraft(name="red"),
            StateDraft(name="green"),
            StateDraft(name="yellow"),
        ],
        initial_state="red",
        transitions=[
            TransitionDraft(name="RedToGreen", from_state="red", to_state="green"),
            TransitionDraft(name="GreenToYellow", from_state="green", to_state="yellow"),
            TransitionDraft(name="YellowToRed", from_state="yellow", to_state="red"),
        ],
        rules=[
            RuleDraft(
                name="ValidState",
                kind="invariant",
                expr=BinaryExpr(
                    op="in",
                    left=RefExpr(name="state"),
                    right=RefExpr(name="States"),
                ),
            )
        ],
    )


def _todo_draft() -> MachineDraft:
    return MachineDraft(
        module_name="TodoWorkflow",
        summary="Todo workflow with archive terminal state",
        states=[
            StateDraft(name="pending"),
            StateDraft(name="in_progress"),
            StateDraft(name="complete"),
            StateDraft(name="archived", terminal=True),
        ],
        initial_state="pending",
        variables=[VariableDraft(name="attempts", type="int", initial=0)],
        transitions=[
            TransitionDraft(name="StartTodo", from_state="pending", to_state="in_progress"),
            TransitionDraft(name="CompleteTodo", from_state="in_progress", to_state="complete"),
            TransitionDraft(name="ArchiveTodo", from_state="complete", to_state="archived"),
        ],
        rules=[
            RuleDraft(
                name="ValidState",
                kind="invariant",
                expr=BinaryExpr(
                    op="in",
                    left=RefExpr(name="state"),
                    right=RefExpr(name="States"),
                ),
            ),
            RuleDraft(
                name="AttemptsNonNegative",
                kind="helper",
                expr=BinaryExpr(op=">=", left=RefExpr(name="attempts"), right=StringExpr(value="0")),
                description="Bad helper on purpose",
            ),
        ],
    )


def test_validator_blocks_required_open_questions() -> None:
    draft = _traffic_light_draft()
    draft.open_questions.append(
        OpenQuestion(id="q1", text="Should yellow be terminal?", required=True, status="open")
    )

    validation = DraftValidator.validate(draft)

    assert validation.ready is False
    assert any(issue.code == "required_open_question" for issue in validation.issues)


def test_validator_rejects_invalid_rule_expression_types() -> None:
    draft = _todo_draft()

    validation = DraftValidator.validate(draft)

    assert validation.ready is False
    assert any(issue.code == "unexpected_expression_type" for issue in validation.issues)


def test_compiler_emits_traffic_light_spec() -> None:
    tla = DraftCompiler().emit(_traffic_light_draft())

    assert "MODULE TrafficLight" in tla
    assert "RedToGreen ==" in tla
    assert "GreenToYellow ==" in tla
    assert "YellowToRed ==" in tla
    assert "ValidState ==" in tla


def test_compiler_rejects_invalid_draft() -> None:
    draft = _traffic_light_draft()
    draft.initial_state = "missing"

    try:
        DraftCompiler().compile(draft)
    except DraftNotReadyError as exc:
        assert any(issue.code == "unknown_initial_state" for issue in exc.validation.issues)
    else:  # pragma: no cover - defensive
        raise AssertionError("compile should reject invalid drafts")
