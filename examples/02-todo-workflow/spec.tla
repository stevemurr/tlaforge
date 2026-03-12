-------------------- MODULE TodoWorkflow --------------------
EXTENDS Integers, FiniteSets, Sequences


VARIABLES
    state

\* --- States ---
States == {"pending", "in_progress", "complete", "archived"}

\* --- Helpers ---
\* --- Initial State ---
Init ==
    /\ state = "pending"

\* --- Transitions ---
\* Begin working on a pending todo
StartTodo ==
    /\ state = "pending"
    /\ state' = "in_progress"

\* Move a todo back to pending
PauseTodo ==
    /\ state = "in_progress"
    /\ state' = "pending"

\* Finish the todo
CompleteTodo ==
    /\ state = "in_progress"
    /\ state' = "complete"

\* Archive without starting work
ArchivePendingTodo ==
    /\ state = "pending"
    /\ state' = "archived"

\* Archive after completion
ArchiveCompletedTodo ==
    /\ state = "complete"
    /\ state' = "archived"

\* --- Next State ---
Next ==
    \/ StartTodo
    \/ PauseTodo
    \/ CompleteTodo
    \/ ArchivePendingTodo
    \/ ArchiveCompletedTodo

\* --- Invariants ---
\* Every todo stays inside the declared workflow states
ValidState ==
    state \in States

\* --- Liveness ---
\* --- Spec ---
Spec ==
    /\ Init
    /\ [][Next]_<<state>>
    /\ WF_<<state>>(Next)

========================================
