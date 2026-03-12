from tlaforge.draft import (
    AddOpenQuestionOp,
    AssistantTurn,
    BinaryExpr,
    DraftPatch,
    OpenQuestion,
    RefExpr,
    PutRuleOp,
    PutStateOp,
    PutTransitionOp,
    RuleDraft,
    SetInitialStateOp,
    SetModuleNameOp,
    StateDraft,
    TransitionDraft,
)
from tlaforge.errors import DraftNotReadyError
from tlaforge.session import TLAForgeSession


class RecordingStructuredClient:
    def __init__(self, *turns: AssistantTurn):
        self.turns = list(turns)
        self.calls = []

    def complete_turn(self, *, draft, transcript, user_message):
        self.calls.append(
            {
                "draft": draft.model_copy(deep=True),
                "transcript": list(transcript),
                "user_message": user_message,
            }
        )
        if not self.turns:
            raise AssertionError("No turn configured")
        return self.turns.pop(0)


def test_handle_user_message_applies_patch_and_updates_transcript() -> None:
    client = RecordingStructuredClient(
        AssistantTurn(
            reply="I added the initial traffic-light states and transitions.",
            patch=DraftPatch(
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
            ),
        )
    )
    session = TLAForgeSession.new()

    result = session.handle_user_message("Let's model a traffic light.", client)

    assert result.ready_for_handoff is True
    assert session.draft.module_name == "TrafficLight"
    assert len(session.transcript) == 2
    assert client.calls[0]["user_message"] == "Let's model a traffic light."


def test_handle_user_message_can_leave_required_open_question() -> None:
    client = RecordingStructuredClient(
        AssistantTurn(
            reply="Do archived todos have any outgoing transitions?",
            patch=DraftPatch(
                operations=[
                    AddOpenQuestionOp(
                        question=OpenQuestion(
                            id="q-archived-terminal",
                            text="Do archived todos have any outgoing transitions?",
                            required=True,
                            status="open",
                        )
                    )
                ]
            ),
        )
    )
    session = TLAForgeSession.new(module_name="Todo")

    result = session.handle_user_message("Add an archived state.", client)

    assert result.ready_for_handoff is False
    assert any(issue.code == "required_open_question" for issue in result.validation.issues)


def test_export_handoff_blocks_until_draft_is_ready() -> None:
    session = TLAForgeSession.new(module_name="Todo")
    session.draft.open_questions.append(
        OpenQuestion(id="q1", text="What is the initial state?", required=True, status="open")
    )

    try:
        session.export_handoff()
    except DraftNotReadyError as exc:
        assert any(issue.code == "required_open_question" for issue in exc.validation.issues)
    else:  # pragma: no cover - defensive
        raise AssertionError("export_handoff should fail while required questions remain open")


def test_export_handoff_returns_tla_and_metadata() -> None:
    session = TLAForgeSession.new(module_name="TodoWorkflow", summary="Todo workflow")
    session.apply_patch(
        DraftPatch(
            operations=[
                PutStateOp(state=StateDraft(name="pending")),
                PutStateOp(state=StateDraft(name="complete")),
                SetInitialStateOp(initial_state="pending"),
                PutTransitionOp(transition=TransitionDraft(name="CompleteTodo", from_state="pending", to_state="complete")),
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

    assert artifact.module_name == "TodoWorkflow"
    assert artifact.summary == "Todo workflow"
    assert "MODULE TodoWorkflow" in artifact.tla_source
    assert artifact.validation.ready is True
