-------------------- MODULE RetryingJob --------------------
EXTENDS Integers, FiniteSets, Sequences

CONSTANTS
    MaxRetries
VARIABLES
    state,
    retries

\* --- States ---
States == {"queued", "running", "retry_wait", "succeeded", "failed"}

\* --- Helpers ---
\* The job still has retry budget remaining
CanRetry ==
    retries < MaxRetries

\* --- Initial State ---
Init ==
    /\ state = "queued"
    /\ retries = 0

\* --- Transitions ---
\* Start the queued job
StartJob ==
    /\ state = "queued"
    /\ state' = "running"
    /\ UNCHANGED retries

\* Move into a retry wait state and increment the retry count
RetryJob ==
    /\ state = "running"
    /\ retries < MaxRetries
    /\ state' = "retry_wait"
    /\ retries' = retries + 1

\* Retry the job after waiting
ResumeJob ==
    /\ state = "retry_wait"
    /\ state' = "running"
    /\ UNCHANGED retries

\* Finish successfully
SucceedJob ==
    /\ state = "running"
    /\ state' = "succeeded"
    /\ UNCHANGED retries

\* Stop retrying once the budget is exhausted
FailJob ==
    /\ state = "running"
    /\ retries = MaxRetries
    /\ state' = "failed"
    /\ UNCHANGED retries

\* --- Next State ---
Next ==
    \/ StartJob
    \/ RetryJob
    \/ ResumeJob
    \/ SucceedJob
    \/ FailJob

\* --- Invariants ---
\* Retry count stays within the configured budget
RetryBounds ==
    /\ retries >= 0
    /\ retries <= MaxRetries

\* --- Liveness ---
\* --- Spec ---
Spec ==
    /\ Init
    /\ [][Next]_<<state, retries>>
    /\ WF_<<state, retries>>(Next)

========================================
