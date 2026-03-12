from tlaforge import (
    BinOp,
    Definition,
    PrimedVar,
    StateMachineSpec,
    StateTransition,
    StringLit,
    Var,
)


def build_spec() -> StateMachineSpec:
    spec = StateMachineSpec(
        module_name="TodoWorkflow",
        states=["pending", "in_progress", "complete", "archived"],
        initial_state="pending",
        terminal_states=["archived"],
    )

    spec.transitions.extend(
        [
            StateTransition(
                name="StartTodo",
                comment="Begin working on a pending todo",
                guards=[BinOp(Var("state"), "=", StringLit("pending"))],
                updates=[BinOp(PrimedVar("state"), "=", StringLit("in_progress"))],
            ),
            StateTransition(
                name="PauseTodo",
                comment="Move a todo back to pending",
                guards=[BinOp(Var("state"), "=", StringLit("in_progress"))],
                updates=[BinOp(PrimedVar("state"), "=", StringLit("pending"))],
            ),
            StateTransition(
                name="CompleteTodo",
                comment="Finish the todo",
                guards=[BinOp(Var("state"), "=", StringLit("in_progress"))],
                updates=[BinOp(PrimedVar("state"), "=", StringLit("complete"))],
            ),
            StateTransition(
                name="ArchivePendingTodo",
                comment="Archive without starting work",
                guards=[BinOp(Var("state"), "=", StringLit("pending"))],
                updates=[BinOp(PrimedVar("state"), "=", StringLit("archived"))],
            ),
            StateTransition(
                name="ArchiveCompletedTodo",
                comment="Archive after completion",
                guards=[BinOp(Var("state"), "=", StringLit("complete"))],
                updates=[BinOp(PrimedVar("state"), "=", StringLit("archived"))],
            ),
        ]
    )

    spec.invariants.append(
        Definition(
            name="ValidState",
            comment="Every todo stays inside the declared workflow states",
            body=BinOp(Var("state"), "\\in", Var("States")),
        )
    )

    return spec


if __name__ == "__main__":
    print(build_spec().emit())
