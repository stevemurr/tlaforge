import argparse
from pathlib import Path

import pytest

from tlaforge import cli


class FakeAgent:
    def __init__(
        self,
        *,
        generate_result=("SPEC TLA", "spec = 'builder'"),
        refine_result=("UPDATED TLA", "spec = 'updated'"),
        generate_error=None,
        refine_error=None,
    ):
        self.generate_result = generate_result
        self.refine_result = refine_result
        self.generate_error = generate_error
        self.refine_error = refine_error
        self.generate_calls = []
        self.refine_calls = []

    def generate(self, description):
        self.generate_calls.append(description)
        if self.generate_error:
            raise self.generate_error
        return self.generate_result

    def refine(self, feedback):
        self.refine_calls.append(feedback)
        if self.refine_error:
            raise self.refine_error
        return self.refine_result


def install_fake_agent(monkeypatch, agent: FakeAgent) -> FakeAgent:
    monkeypatch.setattr(cli, "TLAForgeAgent", lambda: agent)
    return agent


@pytest.mark.parametrize(
    ("args", "expected_title", "expected_description"),
    [
        (
            argparse.Namespace(
                demo=True,
                traffic=False,
                from_file=None,
                description=None,
                output=None,
                interactive=False,
            ),
            "TLAForge Demo: Todo App",
            cli.DEMO_DESCRIPTION,
        ),
        (
            argparse.Namespace(
                demo=False,
                traffic=True,
                from_file=None,
                description=None,
                output=None,
                interactive=False,
            ),
            "TLAForge Demo: Traffic Light",
            cli.TRAFFIC_LIGHT_DESCRIPTION,
        ),
        (
            argparse.Namespace(
                demo=False,
                traffic=False,
                from_file=None,
                description="Inline text",
                output=None,
                interactive=False,
            ),
            "TLAForge: Generating spec",
            "Inline text",
        ),
    ],
)
def test_load_description_selects_demo_traffic_and_inline(args, expected_title, expected_description) -> None:
    assert cli._load_description(args) == (expected_title, expected_description)


def test_load_description_reads_from_file(tmp_path: Path) -> None:
    description_path = tmp_path / "description.txt"
    description_path.write_text("From file description", encoding="utf-8")
    args = argparse.Namespace(
        demo=False,
        traffic=False,
        from_file=str(description_path),
        description=None,
        output=None,
        interactive=False,
    )

    title, description = cli._load_description(args)

    assert title.endswith(str(description_path))
    assert description == "From file description"


def test_main_without_arguments_prints_help(capsys) -> None:
    assert cli.main([]) == 1

    output = capsys.readouterr().out
    assert "usage:" in output
    assert "--traffic" in output


def test_main_generates_from_inline_description(monkeypatch, capsys) -> None:
    fake_agent = install_fake_agent(monkeypatch, FakeAgent())

    assert cli.main(["An inline description"]) == 0

    output = capsys.readouterr().out
    assert fake_agent.generate_calls == ["An inline description"]
    assert "Generated TLA+" in output


def test_main_reads_file_and_writes_output(monkeypatch, tmp_path: Path, capsys) -> None:
    description_path = tmp_path / "description.txt"
    output_path = tmp_path / "spec.tla"
    description_path.write_text("Describe a file-backed system", encoding="utf-8")
    fake_agent = install_fake_agent(
        monkeypatch,
        FakeAgent(generate_result=("FILE TLA", "spec = 'from file'")),
    )

    assert cli.main(["--from-file", str(description_path), "--output", str(output_path)]) == 0

    output = capsys.readouterr().out
    assert fake_agent.generate_calls == ["Describe a file-backed system"]
    assert output_path.read_text(encoding="utf-8") == "FILE TLA"
    assert (tmp_path / "spec_builder.py").read_text(encoding="utf-8") == "spec = 'from file'"
    assert "TLA+ written to:" in output


def test_main_exits_when_generation_fails(monkeypatch, capsys) -> None:
    install_fake_agent(monkeypatch, FakeAgent(generate_error=RuntimeError("boom")))

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["Broken description"])

    assert excinfo.value.code == 1
    assert "Error: boom" in capsys.readouterr().err


def test_main_interactive_refine_updates_output(monkeypatch, tmp_path: Path, capsys) -> None:
    output_path = tmp_path / "spec.tla"
    fake_agent = install_fake_agent(
        monkeypatch,
        FakeAgent(
            generate_result=("INITIAL TLA", "spec = 'initial'"),
            refine_result=("UPDATED TLA", "spec = 'updated'"),
        ),
    )
    inputs = iter(["", "tighten the invariant", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    assert cli.main(["Inline", "--interactive", "--output", str(output_path)]) == 0

    output = capsys.readouterr().out
    assert fake_agent.generate_calls == ["Inline"]
    assert fake_agent.refine_calls == ["tighten the invariant"]
    assert output_path.read_text(encoding="utf-8") == "UPDATED TLA"
    assert "Entering refinement mode" in output
    assert "Updated TLA+" in output


def test_main_interactive_refine_failure_continues(monkeypatch, tmp_path: Path, capsys) -> None:
    output_path = tmp_path / "spec.tla"
    fake_agent = install_fake_agent(
        monkeypatch,
        FakeAgent(
            generate_result=("INITIAL TLA", "spec = 'initial'"),
            refine_error=RuntimeError("bad refine"),
        ),
    )
    inputs = iter(["retry this", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    assert cli.main(["Inline", "--interactive", "--output", str(output_path)]) == 0

    output = capsys.readouterr().out
    assert fake_agent.refine_calls == ["retry this"]
    assert output_path.read_text(encoding="utf-8") == "INITIAL TLA"
    assert "Error: bad refine" in output
