# TodoApp Specification

## Module name & summary
- **module_name**: `TodoApp`
- **summary**: A personal todo‑list that lets a user add, complete, and delete tasks. Each task has a priority (1‑3) and the complete state is stored persistently on disk.

---

## States
| State        | Meaning |
|--------------|----------|
| `StateLoad`  | The system has just read the persisted task list from `storage_path` into `tasks`. |
| `Idle`       | Tasks are loaded and the system is ready to accept user commands (`AddTask`, `CompleteTask`, `DeleteTask`). |
| `HasPendingTasks` | At least one task exists whose `status` is not `Complete`. |
| `HasCompletedTasks` | At least one task exists whose `status` is `Complete` (tasks may also be pending). |
| `AllDone`    | No pending tasks remain; the system can terminate. |
| `StateSave`  | After a mutation, the system writes the updated `tasks` back to `storage_path` and then returns to `Idle`. |

---

## Variables
| Variable | Type / Description |
|----------|----------------------|
| `tasks` | **Set** (or map) of task records. Each record contains:<br>• `id` (unique string)<br>• `description` (string)<br>• `priority` ∈ `{1,2,3}`<br>• `status` ∈ `{"NotStarted","InProgress","Complete"}` |
| `next_id` | Counter used to generate fresh `id`s (initialized to *max existing id* + 1 after loading). |
| `storage_path` | File path where the task list is persisted. |
| `pc` | Program‑counter representing the current state (`StateLoad`, `Idle`, …). |

---

## Transitions (behaviour)

### AddTask
- **Guard**: User supplies non‑empty `description` and a `priority` ∈ `{1,2,3}`.  
- **Effect**: Create a new task `t` with a fresh `id` (`next_id`), `status = "NotStarted"`, add `t` to `tasks`, increment `next_id`.  
- **Next state**: `StateSave`.

### CompleteTask
- **Guard**: Select an existing task `task` where `task.status ≠ "Complete"`.  
- **Effect**: Set `task.status = "Complete"` (within `tasks`).  
- **Next state**: `StateSave`.

### DeleteTask
- **Guard**: Select an existing task `task`.  
- **Effect**: Remove `task` from `tasks`.  
- **Next state**: `StateSave`.

### StateSave
- **Effect**: Overwrite the file at `storage_path` with the serialized representation of the current `tasks`.  
- **Next state**: `Idle` (return to idle for further commands).

---

## Invariants
1. **Priority invariant**: `∀ task ∈ tasks :: task.priority ∈ {1,2,3}`.
2. **Unique‑id invariant**: `∀ t1, t2 ∈ tasks :: t1.id = t2.id → t1 = t2`.
3. **File invariant** (holds after exiting `StateSave`): `FileContent(storage_path) = Serialized(tasks)`.
4. **Id initialization invariant**: `next_id = max{ t.id | t ∈ tasks } + 1` immediately after `StateLoad`.

---

## Assumptions
- The user can only issue commands that satisfy the guards described above.
- The file at `storage_path` is writable and readable by the process.
- No concurrent sessions modify the same `storage_path` (serialization is single‑process).

---

## Open Questions (still unresolved)
1. Should `StateSave` be split into `StateSave_Success` and `StateSave_Failure` to model possible I/O errors?  
2. Should the system automatically trigger a `StateLoad` when the process starts, or should `StateLoad` be entered explicitly by a user command (e.g., “restore”)?

---

*The spec above captures the decisions we have agreed on. Let me know if any section needs adjustment before we move to formalising the TLA+ predicates and the `Init` formula.*