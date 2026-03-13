# Live Todo Handoff

## Problem Statement

Start from user-style requests, use a live local model to build a structured `MachineDraft`, then export a handoff artifact that a coding agent could use to implement a todo app.

This example keeps the repo boundary intact: TLAForge stops at the validated spec and handoff package. It does not generate or own the app implementation itself.

## What This Example Does

1. Creates a `TLAForgeSession` for a single-todo workflow.
2. Uses `OpenAICompatibleStructuredClient.from_live_env()` to talk to the same local model configuration used by the live tests.
3. Sends four fixed user messages that define:
   - the workflow states
   - the terminal state
   - the allowed transitions
   - the invariant
4. Exports a `HandoffArtifact`.
5. Prints:
   - the structured draft
   - the handoff artifact as JSON
   - an agent-ready brief containing the emitted TLA+ spec

## Environment

Set the same environment variables used by the live test harness:

- `TLAFORGE_LIVE_BASE_URL`
- `TLAFORGE_LIVE_MODEL`
- `TLAFORGE_LIVE_API_KEY`

The local provider requires authentication, and this example uses the strict local-provider preset that disables provider "thinking" and requests JSON-schema output.

## Run Command

Assuming you already created and activated a virtual environment, then ran `python -m pip install -e .` from the repo root:

```bash
env TLAFORGE_LIVE_BASE_URL=http://192.168.1.237:4000 \
    TLAFORGE_LIVE_MODEL=nemotron3-nano \
    TLAFORGE_LIVE_API_KEY=sk-change-me \
    python examples/04-live-todo-handoff/run.py
```

## Expected Output Shape

The script prints four sections:

- the fixed user messages sent to the model
- the final structured draft JSON
- the final handoff artifact JSON
- an agent brief that includes the emitted TLA+ spec

The exact patch details and transition names may vary slightly by model, but the final exported handoff should describe a todo workflow with `pending`, `in_progress`, `complete`, and terminal `archived`.

## What To Change Next

Try changing the scripted requests to add a `cancelled` state or a second invariant, then inspect how the exported handoff artifact changes before giving it to a coding agent.
