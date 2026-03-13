import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tlaforge import (
    BinaryExpr,
    DraftPatch,
    PutRuleOp,
    PutStateOp,
    PutTransitionOp,
    RefExpr,
    RuleDraft,
    SetInitialStateOp,
    SetModuleNameOp,
    StateDraft,
    TLAForgeSession,
    TransitionDraft,
)
from tlaforge.llm import LIVE_API_KEY_ENV, LIVE_BASE_URL_ENV, LIVE_MODEL_ENV


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_SCRIPT = REPO_ROOT / "examples" / "04-live-todo-handoff" / "run.py"


def _load_example_module():
    spec = importlib.util.spec_from_file_location("live_todo_handoff_example", EXAMPLE_SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load live todo handoff example module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _build_todo_session_and_artifact():
    session = TLAForgeSession.new(summary="Single-todo workflow for a todo app.")
    session.apply_patch(
        DraftPatch(
            operations=[
                SetModuleNameOp(module_name="TodoWorkflow"),
                PutStateOp(state=StateDraft(name="pending")),
                PutStateOp(state=StateDraft(name="in_progress")),
                PutStateOp(state=StateDraft(name="complete")),
                PutStateOp(state=StateDraft(name="archived", terminal=True)),
                SetInitialStateOp(initial_state="pending"),
                PutTransitionOp(
                    transition=TransitionDraft(
                        name="StartTodo",
                        from_state="pending",
                        to_state="in_progress",
                    )
                ),
                PutTransitionOp(
                    transition=TransitionDraft(
                        name="PauseTodo",
                        from_state="in_progress",
                        to_state="pending",
                    )
                ),
                PutTransitionOp(
                    transition=TransitionDraft(
                        name="CompleteTodo",
                        from_state="in_progress",
                        to_state="complete",
                    )
                ),
                PutTransitionOp(
                    transition=TransitionDraft(
                        name="ArchivePendingTodo",
                        from_state="pending",
                        to_state="archived",
                    )
                ),
                PutTransitionOp(
                    transition=TransitionDraft(
                        name="ArchiveCompletedTodo",
                        from_state="complete",
                        to_state="archived",
                    )
                ),
                PutRuleOp(
                    rule=RuleDraft(
                        name="ValidState",
                        kind="invariant",
                        expr=BinaryExpr(
                            op="in",
                            left=RefExpr(name="state"),
                            right=RefExpr(name="States"),
                        ),
                    )
                ),
            ]
        )
    )
    return session, session.export_handoff()


def test_write_handoff_bundle_creates_expected_files(tmp_path) -> None:
    module = _load_example_module()
    session, artifact = _build_todo_session_and_artifact()

    paths = module.write_handoff_bundle(
        output_dir=tmp_path / "handoff",
        session=session,
        artifact=artifact,
    )

    assert paths.draft_json.exists()
    assert paths.artifact_json.exists()
    assert paths.spec_tla.exists()
    assert paths.agent_brief_md.exists()
    assert paths.pi_prompt_md.exists()
    assert paths.pi_command_txt.exists()
    assert paths.spec_tla.read_text(encoding="utf-8") == artifact.tla_source

    pi_prompt = paths.pi_prompt_md.read_text(encoding="utf-8")
    assert "agent-brief.md" in pi_prompt
    assert "spec.tla" in pi_prompt
    assert "artifact.json" in pi_prompt
    assert "Implement the todo app in the current repository" in pi_prompt

    pi_command = paths.pi_command_txt.read_text(encoding="utf-8")
    assert 'cd "<TARGET_REPO>" && pi ' in pi_command
    assert str(paths.pi_prompt_md) in pi_command
    assert str(paths.agent_brief_md) in pi_command
    assert str(paths.spec_tla) in pi_command
    assert str(paths.artifact_json) in pi_command


def test_write_handoff_bundle_renders_target_repo_command(tmp_path) -> None:
    module = _load_example_module()
    session, artifact = _build_todo_session_and_artifact()
    target_repo = tmp_path / "todo app"

    paths = module.write_handoff_bundle(
        output_dir=tmp_path / "handoff",
        session=session,
        artifact=artifact,
        target_repo=target_repo,
    )

    pi_command = paths.pi_command_txt.read_text(encoding="utf-8")

    assert f"cd {module.shlex.quote(str(target_repo.resolve()))} && pi " in pi_command
    assert "Do not modify the handoff files." in pi_command


@pytest.mark.live_network
def test_live_todo_handoff_example_writes_bundle(tmp_path) -> None:
    missing = [
        name
        for name in (LIVE_BASE_URL_ENV, LIVE_MODEL_ENV, LIVE_API_KEY_ENV)
        if not os.environ.get(name)
    ]
    if missing:
        pytest.skip(f"live network test requires env vars: {', '.join(missing)}")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    target_repo = tmp_path / "todo-app"
    target_repo.mkdir()
    output_dir = tmp_path / "bundle"

    result = subprocess.run(
        [
            sys.executable,
            str(EXAMPLE_SCRIPT),
            "--output-dir",
            str(output_dir),
            "--target-repo",
            str(target_repo),
        ],
        check=True,
        capture_output=True,
        cwd=REPO_ROOT,
        env=env,
        text=True,
    )

    assert "=== Bundle Files ===" in result.stdout
    assert (output_dir / "draft.json").exists()
    assert (output_dir / "artifact.json").exists()
    assert (output_dir / "spec.tla").exists()
    assert (output_dir / "agent-brief.md").exists()
    assert (output_dir / "pi-prompt.md").exists()
    assert (output_dir / "pi-command.txt").exists()
