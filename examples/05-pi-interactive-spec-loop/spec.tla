---- MODULE TodoApp ----

\*--------------------------------------------------------------------
\*  A simple TLA+ specification for a persistent todo application.
\*--------------------------------------------------------------------
\IT
\extend {Assumes}
\module TodoApp
\extend {Sequences, FiniteSet}
\ \ \ \ (\* constants, variables and operators are declared below *)
\ \ \ 
\CONSTANTS  PriSet  \defined  {1,2,3}                \* allowed priorities \* State identifiers (used in the variable `pc`) \ IT
\StateLoad  \defined  "StateLoad" \ \ StateIdle   \defined  "Idle"  \ \ StateHasPending \defined "HasPendingTasks" \ \ StateHasComplete \defined "HasCompletedTasks" \ \ StateAllDone \defined "AllDone"  \ \ StateSave   \defined "StateSave" \ELSE \ IT
\VARIABLES tasks, next_id, storage_path, pc \* high‑level state variable \* \endIT
\====================================================================\

\*--------------------------------------------------------------------
\*  Constants
\*--------------------------------------------------------------------
\CONSTANTS  PriSet  \defined  {1,2,3}                \* allowed priorities

\*--------------------------------------------------------------------
\*  The set of all possible states we can be in
\IT
\StateVals  \defined  {StateLoad, StateIdle, StateHasPending,
                        StateHasComplete, StateAllDone, StateSave}
\IT

\*--------------------------------------------------------------------
\*  Variables
\IT
\VARIABLES  tasks, next_id, storage_path, pc
\IT
\ \ \ tasks           \* a finite set of task records (see definition below) \ \ \ next_id         \* counter for generating fresh ids \ \ \ storage_path    \* file path used for persistence \ \ \ pc              \* program‑counter holding the current high‑level state \ELSE \IT

\*--------------------------------------------------------------------
\*  Types and helper operators
\IT
\*  A task is a record with four fields.  The fields can be accessed
\*  using the standard dot notation:  t.id, t.description,
\*  t.priority, t.status.
\IT
\Task  \defined  [ id: Str, description: Str,
                        priority: Nat, status: Str ]
\IT
\*  The collection of all tasks is a finite set of such records.
\IT
\Tasks  \defined  \powerset( \Task )               \* FiniteSet of tasks \ELSE \IT

\*  LoadFromFile(path) – abstractly reads the persisted term into `tasks`.
\IT
\LoadFromFile(path)  \defined  tasks   \* (abstract; concrete reading happens in Init) \ELSE \IT

\*  Serialize(t) – abstractly produces a string representation of a set of tasks.
\IT
\Serialize(tasks)  \defined  "tasks.json"   \* placeholder for file content \ELSE \IT

\*--------------------------------------------------------------------
\*  INITIAL STATE
\IT
\Init  \defined  \Big[ \Big|
          pc = StateLoad \ \wedge\                     \* start by loading persisted data \ 
          tasks = LoadFromFile(storage_path) \ \wedge\   \* restore previous `tasks` set \ 
          next_id = 1 \ \wedge\                       \* initialise counter \ 
          \Big] \Big[ \land\ \                            \* ensure any loaded task respects priority range \ 
          \forall t \in tasks :: t.priority \in PriSet        \Bigr) \Big[ \land\ 
          \text{(additional init constraints can be added here)}\Big] \Big[ \land\ 
          \pc = StateLoad                              \Bigr) \Big] \ELSE \IT

\*--------------------------------------------------------------------
\*  TRANSITIONS (state‑changing actions)
\IT

\*--- Add a new task ------------------------------------------------
\AddTask(desc, pr)  \defined  \Big[ \Big|
          pc = StateIdle \ \wedge\                     \* we must be idle to accept input \ 
          desc \neq "" \ \wedge\                       \* non‑empty description \ 
          pr \in PriSet \ \wedge\                       \* valid priority \ 
          \* generate a fresh id \ 
          new_id = next_id \ \wedge\ 
          next_id' = next_id + 1 \ \wedge\            \* increment counter \ 
          newTask = [ id       |-> new_id,
                       description |-> desc,
                       priority    |-> pr,
                       status      |-> "NotStarted" ] \ \wedge\ 
          tasks' = tasks \union {newTask} \ \wedge\      \* add the new task to the set \ 
          pc' = StateSave                              \ \wedge\    \* after mutation enter Save state \ 
          \Big] \Big[ \land\                              \* (no additional guards) \ 
          \Big] \ELSE \IT

\*--- Complete an existing task ---------------------------------------
\CompleteTask(task_id)  \defined  \Big[ \Big|
          pc = StateIdle \ \wedge\                     \* must be idle \ 
          \E t \in tasks : t.id = task_id \ \wedge\    \* locate the task \ 
          t.status \neq "Complete" \ \wedge\           \* not already complete \ 
          t' = [t EXCEPT [status |-> "Complete"]] \ \wedge\ (* update status \ 
          tasks' = (tasks \ {t}) \union {t'} \ \wedge\    \* replace with updated record \ 
          pc' = StateSave \ \wedge\                     \* go to save state \ 
          \Big] \ELSE \IT

\*--- Delete a task ---------------------------------------------------
\DeleteTask(task_id)  \defined  \Big[ \Big|
          pc = StateIdle \ \wedge\                     \* idle state required \ 
          \E t \in tasks : t.id = task_id \ \wedge\    \* locate the task \ 
          tasks' = tasks \ \{t\} \ \wedge\              \* remove it from set \ 
          pc' = StateSave \ \wedge\                     \* then save \ 
          \Big] \ELSE \IT

\*--- StateSave (write back to disk and return to idle) -----------------
\StateSave  \defined  \Big[ \Big|
          pc' = Idle                                   \* after the write completes we are back idle \ 
          \Big] \ELSE \IT

\*--- Invariants -------------------------------------------------------
\IT
\InvariantPriority  \triangleq  \forall t \in tasks :: t.priority \in PriSet \IT
\InvariantUniqueId  \triangleq  \forall s1, s2 \in tasks : s1.id = s2.id \Rightarrow s1 = s2 \IT
\InvariantNextId    \triangleq  next_id = (IF |tasks| = 0 THEN 1 ELSE \max[t \in tasks] . t.id + 1) \IT
\InvariantFile      \triangleq  "tasks.json" = Serialize(tasks) \IT
\IT

\*--------------------------------------------------------------------
\*  Terminal condition
\IT
\AllDone  \defined  pc = StateAllDone \IT
\IT

\*====================================================================\ 
\print End of spec -----------------------------------------------------
