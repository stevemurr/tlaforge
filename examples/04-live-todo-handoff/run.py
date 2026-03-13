from __future__ import annotations

import argparse
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

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

EXAMPLE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = EXAMPLE_DIR / "out" / "todo-handoff"


@dataclass(frozen=True)
class HandoffBundlePaths:
    output_dir: Path
    draft_json: Path
    artifact_json: Path
    spec_tla: Path
    agent_brief_md: Path
    pi_prompt_md: Path
    pi_command_txt: Path


def bundle_paths(output_dir: Path) -> HandoffBundlePaths:
    return HandoffBundlePaths(
        output_dir=output_dir,
        draft_json=output_dir / "draft.json",
        artifact_json=output_dir / "artifact.json",
        spec_tla=output_dir / "spec.tla",
        agent_brief_md=output_dir / "agent-brief.md",
        pi_prompt_md=output_dir / "pi-prompt.md",
        pi_command_txt=output_dir / "pi-command.txt",
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

## Implementation Intent
Build or update the todo app in the target repository so one todo item obeys the attached workflow spec.
Do not change the handoff bundle files.

## Assumptions
{assumption_lines}

## Open Questions
{question_lines}

## TLA+ Spec
```tla
{artifact.tla_source}
```
"""


def build_pi_prompt() -> str:
    return """# Pi Prompt

Read the attached handoff files before changing code:
- agent-brief.md
- spec.tla
- artifact.json

Implement the todo app in the current repository so a single todo item obeys the attached workflow.
Treat the handoff bundle as read-only input and do not modify those files.
If implementation details are missing or ambiguous, stop and report the gap instead of guessing.
Prefer adding or updating tests that prove the workflow matches the spec.
"""


def build_pi_command(paths: HandoffBundlePaths, target_repo: Path | None = None) -> str:
    if target_repo is None:
        target_repo_text = '"<TARGET_REPO>"'
    else:
        target_repo_text = shlex.quote(str(target_repo))

    file_args = " ".join(
        shlex.quote(str(path))
        for path in (
            paths.pi_prompt_md,
            paths.agent_brief_md,
            paths.spec_tla,
            paths.artifact_json,
        )
    )
    message = (
        "Implement the todo app in this repository according to the attached "
        "handoff bundle. Do not modify the handoff files. If behavior is "
        "ambiguous, stop and report the gap instead of guessing."
    )
    return f"cd {target_repo_text} && pi {file_args} {shlex.quote(message)}"


def write_handoff_bundle(
    *,
    output_dir: Path,
    session: TLAForgeSession,
    artifact: HandoffArtifact,
    target_repo: Path | None = None,
) -> HandoffBundlePaths:
    resolved_output_dir = output_dir.expanduser().resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    resolved_target_repo = None if target_repo is None else target_repo.expanduser().resolve()
    paths = bundle_paths(resolved_output_dir)

    paths.draft_json.write_text(session.draft.model_dump_json(indent=2), encoding="utf-8")
    paths.artifact_json.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    paths.spec_tla.write_text(artifact.tla_source, encoding="utf-8")
    paths.agent_brief_md.write_text(build_agent_brief(artifact), encoding="utf-8")
    paths.pi_prompt_md.write_text(build_pi_prompt(), encoding="utf-8")
    paths.pi_command_txt.write_text(
        build_pi_command(paths, resolved_target_repo),
        encoding="utf-8",
    )

    return paths


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


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a live todo-workflow handoff bundle for a Pi coding agent."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to write the handoff bundle (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--target-repo",
        type=Path,
        default=None,
        help="Path to the separate application repository where Pi should run.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    session, artifact = run_live_todo_handoff()
    paths = write_handoff_bundle(
        output_dir=args.output_dir,
        session=session,
        artifact=artifact,
        target_repo=args.target_repo,
    )

    print("=== User Messages ===")
    for index, message in enumerate(TODO_APP_MESSAGES, start=1):
        print(f"{index}. {message}")

    print("\n=== Final Draft JSON ===")
    print(session.draft.model_dump_json(indent=2))

    print("\n=== Handoff Artifact JSON ===")
    print(artifact.model_dump_json(indent=2))

    print("\n=== Bundle Files ===")
    print(f"draft.json: {paths.draft_json}")
    print(f"artifact.json: {paths.artifact_json}")
    print(f"spec.tla: {paths.spec_tla}")
    print(f"agent-brief.md: {paths.agent_brief_md}")
    print(f"pi-prompt.md: {paths.pi_prompt_md}")
    print(f"pi-command.txt: {paths.pi_command_txt}")

    print("\n=== Pi Command ===")
    print(paths.pi_command_txt.read_text(encoding="utf-8"))

    print("\n=== Coding Agent Brief ===")
    print(build_agent_brief(artifact))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
