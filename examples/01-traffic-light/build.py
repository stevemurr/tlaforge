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
        module_name="TrafficLight",
        states=["red", "green", "yellow"],
        initial_state="red",
    )

    spec.transitions.extend(
        [
            StateTransition(
                name="RedToGreen",
                comment="Timer expires while the light is red",
                guards=[BinOp(Var("state"), "=", StringLit("red"))],
                updates=[BinOp(PrimedVar("state"), "=", StringLit("green"))],
            ),
            StateTransition(
                name="GreenToYellow",
                comment="Timer expires while the light is green",
                guards=[BinOp(Var("state"), "=", StringLit("green"))],
                updates=[BinOp(PrimedVar("state"), "=", StringLit("yellow"))],
            ),
            StateTransition(
                name="YellowToRed",
                comment="Timer expires while the light is yellow",
                guards=[BinOp(Var("state"), "=", StringLit("yellow"))],
                updates=[BinOp(PrimedVar("state"), "=", StringLit("red"))],
            ),
        ]
    )

    spec.invariants.append(
        Definition(
            name="ValidState",
            comment="The controller is always in one of the named states",
            body=BinOp(Var("state"), "\\in", Var("States")),
        )
    )

    return spec


if __name__ == "__main__":
    print(build_spec().emit())
