from pathlib import Path

from core.context_builder import ContextBuilder


def test_manifest_and_selected_context_exclude_secrets(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')", encoding="utf-8")
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=value", encoding="utf-8")

    builder = ContextBuilder(tmp_path, max_chars=10_000)

    manifest = builder.manifest()
    assert "src/app.py" in manifest.replace("\\", "/")
    assert ".env" not in manifest

    selected = builder.build_selected(["src/app.py", ".env"])
    assert "print('ok')" in selected
    assert "SECRET=value" not in selected


def test_build_selected_ignores_paths_outside_workspace(tmp_path: Path):
    builder = ContextBuilder(tmp_path, max_chars=10_000)
    assert builder.build_selected(["../outside.txt"]) == ""


def test_tiny_project_selects_all_safe_files(tmp_path: Path):
    (tmp_path / "app.py").write_text("print('ok')", encoding="utf-8")
    (tmp_path / "test_app.py").write_text("def test_ok(): pass", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=x", encoding="utf-8")
    builder = ContextBuilder(tmp_path)

    selected = builder.select_relevant("change app", max_files=12)
    assert set(selected) == {"app.py", "test_app.py"}


def test_source_and_test_are_paired(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "calculator.py").write_text("def add(a,b): return a+b", encoding="utf-8")
    (tmp_path / "tests" / "test_calculator.py").write_text("def test_add(): pass", encoding="utf-8")
    for i in range(8):
        (tmp_path / f"other_{i}.py").write_text("x=1", encoding="utf-8")
    builder = ContextBuilder(tmp_path)

    selected = builder.select_relevant("fix calculator", max_files=4)
    assert "src/calculator.py" in selected
    assert "tests/test_calculator.py" in selected


def test_python_import_dependency_is_added(tmp_path: Path):
    (tmp_path / "feature.py").write_text("from helper import value\nprint(value)", encoding="utf-8")
    (tmp_path / "helper.py").write_text("value = 1", encoding="utf-8")
    for i in range(8):
        (tmp_path / f"other_{i}.py").write_text("x=1", encoding="utf-8")
    builder = ContextBuilder(tmp_path)

    selected = builder.select_relevant("change feature", max_files=4)
    assert "feature.py" in selected
    assert "helper.py" in selected


def test_oversized_file_does_not_block_smaller_later_file(tmp_path: Path):
    (tmp_path / "huge.py").write_text("x" * 5000, encoding="utf-8")
    (tmp_path / "small.py").write_text("small = True", encoding="utf-8")
    builder = ContextBuilder(tmp_path, max_chars=500)

    context = builder.build_selected(["huge.py", "small.py"])
    assert "small = True" in context
