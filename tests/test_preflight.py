from pathlib import Path

from core.preflight import PreflightDetector


def test_detects_python_tests(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    check = PreflightDetector(tmp_path).detect()
    assert check.project_type == "python"
    assert check.command == "python -m pytest -q"


def test_detects_node_build_when_no_real_test(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"scripts":{"build":"vite build"}}', encoding="utf-8")
    check = PreflightDetector(tmp_path).detect()
    assert check.project_type == "node"
    assert check.command == "npm run build"


def test_unknown_project_has_no_command(tmp_path: Path):
    check = PreflightDetector(tmp_path).detect()
    assert check.project_type == "unknown"
    assert check.command is None
