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
