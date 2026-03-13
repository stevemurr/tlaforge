# Live Todo Handoff

## Problem Statement

Start from user-style requests, use a live local model to build a structured `MachineDraft`, then export a handoff bundle that a Pi coding agent can consume inside a separate todo-app repository.

This example keeps the repo boundary intact: TLAForge stops at the validated spec and handoff package. It does not generate or own the app implementation itself.

## What This Example Does

1. Creates a `TLAForgeSession` for a single-todo workflow.
2. Uses `OpenAICompatibleStructuredClient.from_live_env()` to talk to the same local model configuration used by the live tests.
3. Sends four fixed user messages that define:
   - the workflow states
   - the terminal state
   - the allowed transitions
   - the invariant
4. Exports a validated `HandoffArtifact`.
5. Writes a handoff bundle to disk containing:
   - `draft.json`
   - `artifact.json`
   - `spec.tla`
   - `agent-brief.md`
   - `pi-prompt.md`
   - `pi-command.txt`
6. Prints the exact Pi command to run in the target app repo.

## Environment

Set the same environment variables used by the live test harness:

- `TLAFORGE_LIVE_BASE_URL`
- `TLAFORGE_LIVE_MODEL`
- `TLAFORGE_LIVE_API_KEY`

This example assumes the Pi coding agent is already installed and configured. TLAForge does not manage Pi installation, model setup, or auth.

## Run Command

Assuming you already created and activated a virtual environment, then ran `python -m pip install -e .` from the repo root:

```bash
env TLAFORGE_LIVE_BASE_URL=http://192.168.1.237:4000 \
    TLAFORGE_LIVE_MODEL=nemotron3-nano \
    TLAFORGE_LIVE_API_KEY=sk-change-me \
    python examples/04-live-todo-handoff/run.py \
    --output-dir examples/04-live-todo-handoff/out/todo-handoff \
    --target-repo /path/to/todo-app
```

If you omit `--target-repo`, the bundle still gets written and `pi-command.txt` uses a `<TARGET_REPO>` placeholder.

## Downstream Flow

1. Run the example from the TLAForge repo to generate the handoff bundle.
2. Inspect the generated files in the output directory if you want to review the spec before implementation.
3. Move to the separate todo-app repository.
4. Run the command written to `pi-command.txt`.

The generated Pi prompt tells Pi to:

- read `agent-brief.md`, `spec.tla`, and `artifact.json`
- implement the todo app in the current repository
- treat the handoff bundle as read-only input
- stop and surface missing assumptions instead of guessing

## Expected Output Shape

The exact patch details and transition names may vary slightly by model, but the final exported handoff should describe a todo workflow with `pending`, `in_progress`, `complete`, and terminal `archived`.

The bundle is the real artifact of this example. The terminal output is only there to help you inspect what was produced.

## What To Change Next

Try changing the scripted requests to add a `cancelled` state or a second invariant, regenerate the bundle, and compare how the Pi prompt and agent brief shift before giving it to the coding agent.
