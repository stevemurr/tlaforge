# Pi Interactive Spec Loop

## Problem Statement

Use Pi as the front-end agent from the first turn, not only as a downstream implementation handoff.

The goal is to let Pi interview the user, surface missing requirements, and iteratively shape a `MachineDraft` for a todo app before anyone exports a final spec bundle.

This example is the complement to [examples/04-live-todo-handoff/README.md](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/04-live-todo-handoff/README.md):

- Example `04` starts from fixed scripted requests and ends with a Pi handoff.
- Example `05` starts with Pi itself guiding the requirements conversation.

## What This Example Demonstrates

1. Pi can act as the outer agent loop while TLAForge remains the structured spec layer.
2. The conversation can stay in TLAForge terms: module name, states, initial state, transitions, rules, assumptions, and open questions.
3. Pi should ask direct follow-up questions instead of guessing when a required behavior is unclear.
4. Once the draft is coherent, Pi can translate the settled requirements into the same `TLAForgeSession` flow used elsewhere in this repo.

## Start Pi

Run Pi from the repo root and pass the bootstrap prompt as context:

```bash
cd /Users/murr/Code/github.com/stevemurr/tlaforge
pi --model nemotron3-nano --interactive \
  examples/05-pi-interactive-spec-loop/pi-bootstrap-prompt.md \
  "Let's build a spec using TLAForge for a todo app."
```

If your Pi installation uses slightly different CLI flags, keep the same shape:

- open an interactive session
- attach [examples/05-pi-interactive-spec-loop/pi-bootstrap-prompt.md](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/05-pi-interactive-spec-loop/pi-bootstrap-prompt.md)
- start with a plain user request for the app you want to model

## Example Conversation

This is the intended style of loop:

```text
User: Let's build a spec using TLAForge for a todo app.
Agent: I'll keep this in TLAForge terms and drive the missing questions. Are we modeling the lifecycle of one todo item or the whole list, and what module name should we use?

User: One todo item. Use TodoWorkflow.
Agent: Good. What are the user-visible states, and which one is the initial state?

User: pending, in_progress, complete, archived. Initial is pending.
Agent: Should archived be terminal, or can a todo leave archived?

User: archived is terminal.
Agent: What transitions are allowed between those states? List them explicitly so I do not infer unsupported paths.

User: pending to in_progress, in_progress to pending, in_progress to complete, pending to archived, and complete to archived.
Agent: Do you want any auxiliary variables in the state machine itself, or is lifecycle state enough for the first cut?

User: Lifecycle state only.
Agent: Then the minimal invariant is that state is always in States. Do you want any stronger rule, such as forbidding direct pending-to-complete transitions, or is the transition graph enough?

User: The transition graph is enough. Keep only ValidState for now.
Agent: The draft is now specific enough to materialize as a TLAForge session:

- module_name: TodoWorkflow
- states: pending, in_progress, complete, archived (terminal)
- initial_state: pending
- transitions: StartTodo, PauseTodo, CompleteTodo, ArchivePendingTodo, ArchiveCompletedTodo
- rules: ValidState
- open questions: none

Next I should write or update a small TLAForge session driver, validate the draft, and export the spec or handoff bundle.
```

## How Pi Should Behave

The bootstrap prompt asks Pi to stay disciplined:

- ask one or two direct requirements questions at a time
- summarize the current draft after each meaningful answer
- treat ambiguity as an open question instead of guessing
- avoid jumping to app implementation before the spec is stable
- switch to export or handoff only after the requirements are settled

That matters because `TLAForgeSession` is designed to keep incomplete drafts explicit. If a key detail is missing, the right next step is another question, not speculative TLA+.

## Transition To Export Or Handoff

Once the requirements are settled, Pi has two clean next moves:

1. Translate the agreed conversation into the same `session.handle_user_message(...)` pattern shown in [examples/04-live-todo-handoff/run.py](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/04-live-todo-handoff/run.py).
2. Export the validated handoff bundle and continue with the downstream implementation flow from [examples/04-live-todo-handoff/README.md](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/04-live-todo-handoff/README.md).

The important difference is ownership of the discovery loop: here Pi helps define the state machine before the bundle exists.
