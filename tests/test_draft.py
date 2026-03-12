import pytest
from pydantic import ValidationError

from tlaforge.draft import (
    AddOpenQuestionOp,
    AssistantTurn,
    OpenQuestion,
    StateDraft,
    ValidationResult,
    VariableDraft,
)
from tlaforge.session import TLAForgeSession


def test_assistant_turn_schema_generation_includes_patch_and_reply() -> None:
    schema = AssistantTurn.model_json_schema()

    assert "reply" in schema["properties"]
    assert "patch" in schema["properties"]


def test_variable_draft_rejects_mismatched_initial_type() -> None:
    with pytest.raises(ValidationError, match="initial value does not match variable type"):
        VariableDraft(name="count", type="int", initial="zero")


def test_machine_draft_round_trips_through_session_json() -> None:
    session = TLAForgeSession.new(module_name="TodoWorkflow", summary="Todo flow")
    session.draft.states.append(StateDraft(name="pending"))
    session.draft.open_questions.append(
        OpenQuestion(id="q1", text="Should archived be terminal?", required=True)
    )

    restored = TLAForgeSession.from_json(session.to_json())

    assert restored.draft.module_name == "TodoWorkflow"
    assert restored.draft.summary == "Todo flow"
    assert restored.draft.open_questions[0].id == "q1"


def test_assistant_turn_validates_strict_patch_shape() -> None:
    turn = AssistantTurn.model_validate(
        {
            "reply": "Need one more detail.",
            "patch": {
                "operations": [
                    {
                        "op": "add_open_question",
                        "question": {
                            "id": "q-terminal",
                            "text": "Is archived terminal?",
                            "required": True,
                            "status": "open",
                        },
                    }
                ]
            },
        }
    )

    assert isinstance(turn.patch.operations[0], AddOpenQuestionOp)


def test_validation_result_ready_tracks_blocking_issues() -> None:
    ready = ValidationResult.from_issues([])
    blocked = ValidationResult.model_validate(
        {
            "issues": [
                {
                    "severity": "error",
                    "code": "missing_module_name",
                    "message": "module_name is required before handoff",
                    "blocking": True,
                }
            ],
            "ready": False,
        }
    )

    assert ready.ready is True
    assert blocked.ready is False
