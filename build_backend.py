"""Minimal local PEP 517 backend for offline wheel and editable installs."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
import zipfile


NAME = "tlaforge"
VERSION = "0.1.0"
SUMMARY = "Build TLA+ state machine specs with Python builders."
TAG = "py3-none-any"


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def _dist_info_dir() -> str:
    return f"{NAME}-{VERSION}.dist-info"


def _wheel_name() -> str:
    return f"{NAME}-{VERSION}-{TAG}.whl"


def _metadata_text() -> str:
    return (
        "Metadata-Version: 2.1\n"
        f"Name: {NAME}\n"
        f"Version: {VERSION}\n"
        f"Summary: {SUMMARY}\n"
    )


def _wheel_text() -> str:
    return (
        "Wheel-Version: 1.0\n"
        "Generator: tlaforge.build_backend\n"
        "Root-Is-Purelib: true\n"
        f"Tag: {TAG}\n"
    )


def _record_line(path: str, data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"{path},sha256={encoded},{len(data)}\n"


def _write_wheel_file(
    wheel_directory: str,
    package_files: list[tuple[str, bytes]],
    extra_files: list[tuple[str, bytes]],
) -> str:
    wheel_path = Path(wheel_directory) / _wheel_name()
    dist_info_dir = _dist_info_dir()
    record_lines: list[str] = []

    metadata_relpath = f"{dist_info_dir}/METADATA"
    metadata_bytes = _metadata_text().encode("utf-8")
    wheel_relpath = f"{dist_info_dir}/WHEEL"
    wheel_bytes = _wheel_text().encode("utf-8")

    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as wheel:
        for relpath, data in package_files + extra_files:
            wheel.writestr(relpath, data)
            record_lines.append(_record_line(relpath, data))

        wheel.writestr(metadata_relpath, metadata_bytes)
        record_lines.append(_record_line(metadata_relpath, metadata_bytes))

        wheel.writestr(wheel_relpath, wheel_bytes)
        record_lines.append(_record_line(wheel_relpath, wheel_bytes))

        record_relpath = f"{dist_info_dir}/RECORD"
        record_text = "".join(record_lines) + f"{record_relpath},,\n"
        wheel.writestr(record_relpath, record_text.encode("utf-8"))

    return wheel_path.name


def _package_sources() -> list[tuple[str, bytes]]:
    package_root = _project_root() / NAME
    files = []
    for path in sorted(package_root.rglob("*.py")):
        relpath = path.relative_to(_project_root()).as_posix()
        files.append((relpath, path.read_bytes()))
    return files


def get_requires_for_build_wheel(config_settings=None) -> list[str]:
    return []


def get_requires_for_build_editable(config_settings=None) -> list[str]:
    return []


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings=None,
    metadata_directory_suffix=None,
) -> str:
    dist_info_dir = Path(metadata_directory) / _dist_info_dir()
    dist_info_dir.mkdir(parents=True, exist_ok=True)
    (dist_info_dir / "METADATA").write_text(_metadata_text(), encoding="utf-8")
    (dist_info_dir / "WHEEL").write_text(_wheel_text(), encoding="utf-8")
    return dist_info_dir.name


def prepare_metadata_for_build_editable(
    metadata_directory: str,
    config_settings=None,
    metadata_directory_suffix=None,
) -> str:
    return prepare_metadata_for_build_wheel(
        metadata_directory=metadata_directory,
        config_settings=config_settings,
        metadata_directory_suffix=metadata_directory_suffix,
    )


def build_wheel(
    wheel_directory: str,
    config_settings=None,
    metadata_directory=None,
) -> str:
    return _write_wheel_file(
        wheel_directory=wheel_directory,
        package_files=_package_sources(),
        extra_files=[],
    )


def build_editable(
    wheel_directory: str,
    config_settings=None,
    metadata_directory=None,
) -> str:
    editable_pth = f"{NAME}.pth"
    extra_files = [
        (editable_pth, f"{_project_root()}\n".encode("utf-8")),
    ]
    return _write_wheel_file(
        wheel_directory=wheel_directory,
        package_files=[],
        extra_files=extra_files,
    )


def _supported_features() -> list[str]:
    return ["build_editable"]
