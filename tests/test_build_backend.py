from pathlib import Path
import zipfile

import build_backend


def test_metadata_text_includes_test_extra_and_python_requirement() -> None:
    metadata = build_backend._metadata_text()

    assert "Name: tlaforge" in metadata
    assert "Version: 0.1.0" in metadata
    assert "Requires-Python: >=3.11" in metadata
    assert "Provides-Extra: test" in metadata
    assert 'Requires-Dist: pytest>=8,<9; extra == "test"' in metadata


def test_prepare_metadata_for_build_wheel_writes_dist_info(tmp_path: Path) -> None:
    dist_info_dir = build_backend.prepare_metadata_for_build_wheel(str(tmp_path))
    metadata_path = tmp_path / dist_info_dir / "METADATA"
    wheel_path = tmp_path / dist_info_dir / "WHEEL"

    assert dist_info_dir == "tlaforge-0.1.0.dist-info"
    assert metadata_path.read_text(encoding="utf-8").startswith("Metadata-Version: 2.1")
    assert "Tag: py3-none-any" in wheel_path.read_text(encoding="utf-8")


def test_prepare_metadata_for_build_editable_reuses_wheel_metadata(tmp_path: Path) -> None:
    dist_info_dir = build_backend.prepare_metadata_for_build_editable(str(tmp_path))

    assert (tmp_path / dist_info_dir / "METADATA").exists()
    assert (tmp_path / dist_info_dir / "WHEEL").exists()


def test_package_sources_include_python_modules() -> None:
    sources = dict(build_backend._package_sources())

    assert "tlaforge/__init__.py" in sources
    assert "tlaforge/cli.py" in sources
    assert sources["tlaforge/__init__.py"].startswith(b'"""Public package surface')


def test_build_wheel_contains_package_files_and_metadata(tmp_path: Path) -> None:
    wheel_name = build_backend.build_wheel(str(tmp_path))
    wheel_path = tmp_path / wheel_name

    with zipfile.ZipFile(wheel_path) as wheel:
        names = set(wheel.namelist())
        metadata = wheel.read("tlaforge-0.1.0.dist-info/METADATA").decode("utf-8")
        record = wheel.read("tlaforge-0.1.0.dist-info/RECORD").decode("utf-8")

    assert wheel_name == "tlaforge-0.1.0-py3-none-any.whl"
    assert "tlaforge/__init__.py" in names
    assert "tlaforge/agent.py" in names
    assert "tlaforge-0.1.0.dist-info/WHEEL" in names
    assert "Name: tlaforge" in metadata
    assert "tlaforge/__init__.py,sha256=" in record


def test_build_editable_contains_pth_file_and_metadata(tmp_path: Path) -> None:
    wheel_name = build_backend.build_editable(str(tmp_path))
    wheel_path = tmp_path / wheel_name

    with zipfile.ZipFile(wheel_path) as wheel:
        names = set(wheel.namelist())
        editable_path = wheel.read("tlaforge.pth").decode("utf-8").strip()

    assert "tlaforge.pth" in names
    assert "tlaforge-0.1.0.dist-info/METADATA" in names
    assert editable_path == str(build_backend._project_root())


def test_helper_functions_report_supported_features() -> None:
    record = build_backend._record_line("tlaforge.py", b"x")

    assert build_backend._wheel_name() == "tlaforge-0.1.0-py3-none-any.whl"
    assert build_backend._dist_info_dir() == "tlaforge-0.1.0.dist-info"
    assert build_backend.get_requires_for_build_wheel() == []
    assert build_backend.get_requires_for_build_editable() == []
    assert build_backend._supported_features() == ["build_editable"]
    assert record.startswith("tlaforge.py,sha256=")
    assert record.endswith(",1\n")
