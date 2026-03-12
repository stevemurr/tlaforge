from tlaforge import (
    And,
    BinOp,
    Definition,
    IntLit,
    PrimedVar,
    StateMachineSpec,
    StateTransition,
    StringLit,
    Var,
)


def build_spec() -> StateMachineSpec:
    spec = StateMachineSpec(
        module_name="RetryingJob",
        states=["queued", "running", "retry_wait", "succeeded", "failed"],
        initial_state="queued",
        terminal_states=["succeeded", "failed"],
        constants=["MaxRetries"],
        aux_vars=["retries"],
        aux_init={"retries": IntLit(0)},
    )

    spec.helpers.append(
        Definition(
            name="CanRetry",
            comment="The job still has retry budget remaining",
            body=BinOp(Var("retries"), "<", Var("MaxRetries")),
        )
    )

    spec.transitions.extend(
        [
            StateTransition(
                name="StartJob",
                comment="Start the queued job",
                guards=[BinOp(Var("state"), "=", StringLit("queued"))],
                updates=[BinOp(PrimedVar("state"), "=", StringLit("running"))],
                unchanged=["retries"],
            ),
            StateTransition(
                name="RetryJob",
                comment="Move into a retry wait state and increment the retry count",
                guards=[
                    BinOp(Var("state"), "=", StringLit("running")),
                    BinOp(Var("retries"), "<", Var("MaxRetries")),
                ],
                updates=[
                    BinOp(PrimedVar("state"), "=", StringLit("retry_wait")),
                    BinOp(
                        PrimedVar("retries"),
                        "=",
                        BinOp(Var("retries"), "+", IntLit(1)),
                    ),
                ],
            ),
            StateTransition(
                name="ResumeJob",
                comment="Retry the job after waiting",
                guards=[BinOp(Var("state"), "=", StringLit("retry_wait"))],
                updates=[BinOp(PrimedVar("state"), "=", StringLit("running"))],
                unchanged=["retries"],
            ),
            StateTransition(
                name="SucceedJob",
                comment="Finish successfully",
                guards=[BinOp(Var("state"), "=", StringLit("running"))],
                updates=[BinOp(PrimedVar("state"), "=", StringLit("succeeded"))],
                unchanged=["retries"],
            ),
            StateTransition(
                name="FailJob",
                comment="Stop retrying once the budget is exhausted",
                guards=[
                    BinOp(Var("state"), "=", StringLit("running")),
                    BinOp(Var("retries"), "=", Var("MaxRetries")),
                ],
                updates=[BinOp(PrimedVar("state"), "=", StringLit("failed"))],
                unchanged=["retries"],
            ),
        ]
    )

    spec.invariants.append(
        Definition(
            name="RetryBounds",
            comment="Retry count stays within the configured budget",
            body=And(
                BinOp(Var("retries"), ">=", IntLit(0)),
                BinOp(Var("retries"), "<=", Var("MaxRetries")),
            ),
        )
    )

    return spec


if __name__ == "__main__":
    print(build_spec().emit())
