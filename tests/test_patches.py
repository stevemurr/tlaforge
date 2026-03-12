from tlaforge.draft import (
    AddAssumptionOp,
    BinaryExpr,
    DraftPatch,
    MachineDraft,
    PutStateOp,
    RefExpr,
    RemoveStateOp,
    RenameStateOp,
    RenameVariableOp,
    StateDraft,
    TransitionDraft,
    VariableDraft,
)
from tlaforge.patches import apply_patch_to_draft


def test_apply_patch_renames_state_and_updates_structural_references() -> None:
    draft = MachineDraft(
        module_name="Todo",
        states=[StateDraft(name="pending"), StateDraft(name="archived", terminal=True)],
        initial_state="pending",
        transitions=[
            TransitionDraft(name="Archive", from_state="pending", to_state="archived"),
        ],
    )
    patch = DraftPatch(
        operations=[
            RenameStateOp(old_name="pending", new_name="todo_pending"),
        ]
    )

    updated, issues = apply_patch_to_draft(draft, patch)

    assert issues == []
    assert updated.initial_state == "todo_pending"
    assert updated.states[0].name == "todo_pending"
    assert updated.transitions[0].from_state == "todo_pending"


def test_apply_patch_rejects_removing_state_referenced_by_transition() -> None:
    draft = MachineDraft(
        module_name="Todo",
        states=[StateDraft(name="pending"), StateDraft(name="archived")],
        transitions=[
            TransitionDraft(name="Archive", from_state="pending", to_state="archived"),
        ],
    )
    patch = DraftPatch(operations=[RemoveStateOp(name="pending")])

    updated, issues = apply_patch_to_draft(draft, patch)

    assert updated == draft
    assert issues[0].code == "state_in_use"


def test_apply_patch_renames_variable_and_updates_refs() -> None:
    draft = MachineDraft(
        module_name="Todo",
        states=[StateDraft(name="pending"), StateDraft(name="done")],
        variables=[VariableDraft(name="count", type="int", initial=0)],
        transitions=[
            TransitionDraft(
                name="Complete",
                from_state="pending",
                to_state="done",
                guards=[
                    BinaryExpr(
                        op=">",
                        left=RefExpr(name="count"),
                        right=RefExpr(name="count"),
                    )
                ],
            )
        ],
    )
    patch = DraftPatch(operations=[RenameVariableOp(old_name="count", new_name="todo_count")])

    updated, issues = apply_patch_to_draft(draft, patch)

    guard = updated.transitions[0].guards[0]
    assert issues == []
    assert updated.variables[0].name == "todo_count"
    assert isinstance(guard, BinaryExpr)
    assert isinstance(guard.left, RefExpr)
    assert guard.left.name == "todo_count"


def test_apply_patch_rejects_duplicate_assumptions() -> None:
    draft = MachineDraft(module_name="Todo", assumptions=["IDs are stable"])
    patch = DraftPatch(operations=[AddAssumptionOp(text="IDs are stable")])

    updated, issues = apply_patch_to_draft(draft, patch)

    assert updated == draft
    assert issues[0].code == "duplicate_assumption"
