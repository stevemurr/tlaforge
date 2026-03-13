from __future__ import annotations

from tlaforge import HandoffArtifact, OpenAICompatibleStructuredClient, TLAForgeSession


TODO_APP_MESSAGES = (
    (
        "Create a module named TodoWorkflow with states pending, in_progress, "
        "complete, and archived. Set the initial state to pending. Mark archived "
        "as terminal."
    ),
    "Update the archived state so terminal is true.",
    (
        "Add transitions StartTodo pending to in_progress, PauseTodo in_progress "
        "to pending, CompleteTodo in_progress to complete, ArchivePendingTodo "
        "pending to archived, and ArchiveCompletedTodo complete to archived."
    ),
    (
        "Add an invariant named ValidState using a binary in expression with left "
        "ref state and right ref States."
    ),
)


def build_agent_brief(artifact: HandoffArtifact) -> str:
    assumptions = artifact.assumptions or ["None recorded."]
    open_questions = artifact.open_questions or []

    assumption_lines = "\n".join(f"- {item}" for item in assumptions)
    if open_questions:
        question_lines = "\n".join(
            f"- {question.id}: {question.text} ({question.status})"
            for question in open_questions
        )
    else:
        question_lines = "- None."

    summary = artifact.summary or "Single-todo workflow for a todo app."

    return f"""# Coding Agent Brief

Implement the app behavior so a single todo item follows this validated workflow.

## Module
{artifact.module_name}

## Summary
{summary}

## Assumptions
{assumption_lines}

## Open Questions
{question_lines}

## TLA+ Spec
```tla
{artifact.tla_source}
```
"""


def run_live_todo_handoff() -> tuple[TLAForgeSession, HandoffArtifact]:
    client = OpenAICompatibleStructuredClient.from_live_env(max_tokens=4096)
    session = TLAForgeSession.new(summary="Single-todo workflow for a todo app.")

    for index, message in enumerate(TODO_APP_MESSAGES, start=1):
        result = session.handle_user_message(message, client)
        if result.validation.issues:
            issue_lines = "\n".join(
                f"- {issue.code}: {issue.message} ({issue.path})"
                for issue in result.validation.issues
            )
            raise RuntimeError(
                f"live turn {index} produced blocking validation issues:\n{issue_lines}"
            )

    return session, session.export_handoff()


def main() -> int:
    session, artifact = run_live_todo_handoff()

    print("=== User Messages ===")
    for index, message in enumerate(TODO_APP_MESSAGES, start=1):
        print(f"{index}. {message}")

    print("\n=== Final Draft JSON ===")
    print(session.draft.model_dump_json(indent=2))

    print("\n=== Handoff Artifact JSON ===")
    print(artifact.model_dump_json(indent=2))

    print("\n=== Coding Agent Brief ===")
    print(build_agent_brief(artifact))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
