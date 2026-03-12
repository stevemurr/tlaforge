import pytest

from tlaforge.builder import (
    Always,
    And,
    BinOp,
    Definition,
    Eventually,
    Except,
    Exists,
    Forall,
    FunctionApp,
    Implies,
    IntLit,
    LeadsTo,
    Not,
    Or,
    PrimedVar,
    Raw,
    SetLit,
    SetOf,
    StateMachineSpec,
    StateTransition,
    StringLit,
    Unchanged,
    Var,
)


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        (Raw("TRUE"), "TRUE"),
        (Var("state"), "state"),
        (PrimedVar("state"), "state'"),
        (IntLit(3), "3"),
        (StringLit("ok"), '"ok"'),
        (SetLit(), "{}"),
        (SetLit(IntLit(1), IntLit(2)), "{1, 2}"),
        (SetOf("x", Var("States"), BinOp(Var("x"), "#", StringLit("bad"))), '{  x \\in States : x # "bad"  }'),
        (FunctionApp(Var("jobs"), StringLit("id-1")), 'jobs["id-1"]'),
        (Except(Var("jobs"), StringLit("id-1"), StringLit("done")), '[jobs EXCEPT !["id-1"] = "done"]'),
        (BinOp(Var("state"), "=", StringLit("ready")), 'state = "ready"'),
        (Not(Var("done")), "~done"),
        (Implies(Var("ready"), Var("done")), "ready => done"),
        (Unchanged("state"), "UNCHANGED state"),
        (Unchanged("state", "count"), "UNCHANGED <<state, count>>"),
        (Forall("x", Var("States"), BinOp(Var("x"), "\\in", Var("States"))), "\\A x \\in States : x \\in States"),
        (Exists("x", Var("States"), BinOp(Var("x"), "=", StringLit("ready"))), '\\E x \\in States : x = "ready"'),
        (Eventually(Var("done")), "<>(done)"),
        (Always(Var("ok")), "[](ok)"),
        (LeadsTo(Var("queued"), Var("done")), "queued ~> done"),
    ],
)
def test_expression_emitters(expr, expected) -> None:
    assert expr.emit() == expected


def test_and_add_and_emit_multiple_clauses() -> None:
    expr = And(Var("ready"))

    assert expr.add(Var("done")) is expr
    assert expr.emit() == "/\\ ready\n    /\\ done"


def test_or_emit_single_and_multiple_clauses() -> None:
    assert Or(Var("one")).emit() == "one"
    assert Or(Var("one"), Var("two")).emit() == "\\/ one\n    \\/ two"


def test_definition_emit_with_comment_and_params() -> None:
    definition = Definition(
        name="TypeInvariant",
        params=["job"],
        body=BinOp(Var("job"), "\\in", Var("Jobs")),
        comment="Every job stays in the job set",
    )

    assert definition.emit() == (
        "\\* Every job stays in the job set\n"
        "TypeInvariant(job) ==\n"
        "    job \\in Jobs"
    )


def test_definition_emit_defaults_to_true_body() -> None:
    assert Definition(name="Trivial").emit() == "Trivial ==\n    TRUE"


def test_state_transition_to_definition_includes_unchanged_clause() -> None:
    transition = StateTransition(
        name="CompleteJob",
        guards=[BinOp(Var("state"), "=", StringLit("running"))],
        updates=[BinOp(PrimedVar("state"), "=", StringLit("done"))],
        unchanged=["retries"],
        comment="Complete the running job",
    )

    emitted = transition.to_definition().emit()

    assert "\\* Complete the running job" in emitted
    assert "/\\ state = \"running\"" in emitted
    assert "/\\ state' = \"done\"" in emitted
    assert "/\\ UNCHANGED retries" in emitted


def test_state_transition_to_definition_uses_true_when_empty() -> None:
    emitted = StateTransition(name="Stutter").to_definition().emit()

    assert emitted == "Stutter ==\n    TRUE"


def test_state_machine_all_vars_and_empty_spec() -> None:
    spec = StateMachineSpec(module_name="Empty", aux_vars=["count"], aux_init={"count": IntLit(0)})

    assert spec.all_vars() == ["state", "count"]
    assert "Next == FALSE" in spec.emit()


def test_state_machine_emit_includes_all_sections() -> None:
    spec = StateMachineSpec(
        module_name="RetryingJob",
        extends=["Integers"],
        aux_vars=["retries"],
        aux_init={"retries": IntLit(0)},
        states=["queued", "running", "done"],
        initial_state="queued",
        constants=["MaxRetries"],
        transitions=[
            StateTransition(
                name="StartJob",
                guards=[BinOp(Var("state"), "=", StringLit("queued"))],
                updates=[BinOp(PrimedVar("state"), "=", StringLit("running"))],
                unchanged=["retries"],
            )
        ],
        invariants=[
            Definition(
                name="RetryBound",
                body=BinOp(Var("retries"), "<=", Var("MaxRetries")),
            )
        ],
        liveness=[
            Definition(
                name="EventuallyDone",
                body=Eventually(BinOp(Var("state"), "=", StringLit("done"))),
            )
        ],
        helpers=[
            Definition(
                name="CanRetry",
                body=BinOp(Var("retries"), "<", Var("MaxRetries")),
            )
        ],
    )

    emitted = spec.emit()

    assert "EXTENDS Integers" in emitted
    assert "CONSTANTS\n    MaxRetries" in emitted
    assert "VARIABLES\n    state,\n    retries" in emitted
    assert "States == {\"queued\", \"running\", \"done\"}" in emitted
    assert "CanRetry ==" in emitted
    assert "/\\ retries = 0" in emitted
    assert "StartJob ==" in emitted
    assert "Next ==\n    \\/ StartJob" in emitted
    assert "RetryBound ==" in emitted
    assert "EventuallyDone ==" in emitted
    assert "WF_<<state, retries>>(Next)" in emitted


def test_state_machine_emit_omits_extends_when_empty() -> None:
    spec = StateMachineSpec(
        module_name="Bare",
        extends=[],
        states=["idle"],
        initial_state="idle",
    )

    emitted = spec.emit()

    assert "MODULE Bare" in emitted
    assert "EXTENDS" not in emitted


def test_state_machine_emit_requires_all_aux_init_values() -> None:
    spec = StateMachineSpec(
        module_name="Counter",
        states=["idle"],
        initial_state="idle",
        aux_vars=["count"],
    )

    with pytest.raises(ValueError, match="count"):
        spec.emit()


def test_state_machine_emit_rejects_extra_aux_init_values() -> None:
    spec = StateMachineSpec(
        module_name="Counter",
        states=["idle"],
        initial_state="idle",
        aux_init={"count": IntLit(0)},
    )

    with pytest.raises(ValueError, match="count"):
        spec.emit()


def test_emit_valid_transitions_stub_is_covered_for_both_paths() -> None:
    empty_spec = StateMachineSpec(module_name="Empty")
    populated_spec = StateMachineSpec(
        module_name="Populated",
        transitions=[
            StateTransition(
                name="Step",
                guards=[BinOp(Var("state"), "=", StringLit("idle"))],
                updates=[BinOp(PrimedVar("state"), "=", StringLit("done"))],
            )
        ],
    )

    assert empty_spec._emit_valid_transitions() == ""
    assert populated_spec._emit_valid_transitions() == ""
