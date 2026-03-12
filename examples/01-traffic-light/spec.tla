-------------------- MODULE TrafficLight --------------------
EXTENDS Integers, FiniteSets, Sequences


VARIABLES
    state

\* --- States ---
States == {"red", "green", "yellow"}

\* --- Helpers ---
\* --- Initial State ---
Init ==
    /\ state = "red"

\* --- Transitions ---
\* Timer expires while the light is red
RedToGreen ==
    /\ state = "red"
    /\ state' = "green"

\* Timer expires while the light is green
GreenToYellow ==
    /\ state = "green"
    /\ state' = "yellow"

\* Timer expires while the light is yellow
YellowToRed ==
    /\ state = "yellow"
    /\ state' = "red"

\* --- Next State ---
Next ==
    \/ RedToGreen
    \/ GreenToYellow
    \/ YellowToRed

\* --- Invariants ---
\* The controller is always in one of the named states
ValidState ==
    state \in States

\* --- Liveness ---
\* --- Spec ---
Spec ==
    /\ Init
    /\ [][Next]_<<state>>
    /\ WF_<<state>>(Next)

========================================
