from __future__ import annotations
from pathlib import Path

SECRET_NAMES = {".env", "id_rsa", "id_ed25519", "credentials.json"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "Library", "Temp", "obj", "bin"}
SECRET_SUFFIXES = {".key", ".pem", ".pfx"}


class ContextBuilder:
    def __init__(self, workspace: Path, max_chars: int = 120_000):
        self.workspace = workspace.resolve()
        self.max_chars = max_chars

    def _relative_parts(self, path: Path) -> tuple[str, ...]:
        try:
            return path.relative_to(self.workspace).parts
        except ValueError:
            return ()

    def _is_safe_path(self, path: Path) -> bool:
        relative_parts = self._relative_parts(path)
        if not relative_parts:
            return False
        if any(part in SKIP_DIRS for part in relative_parts[:-1]):
            return False
        if path.name in SECRET_NAMES or path.suffix.lower() in SECRET_SUFFIXES:
            return False
        return True

    def _iter_safe_files(self):
        for path in self.workspace.rglob("*"):
            if not path.is_file():
                continue
            if not self._is_safe_path(path):
                continue
            yield path

    def manifest(self, max_files: int = 500) -> str:
        rows: list[str] = []
        for index, path in enumerate(self._iter_safe_files()):
            if index >= max_files:
                rows.append("... manifest truncated ...")
                break
            try:
                rel = path.relative_to(self.workspace)
                size = path.stat().st_size
            except Exception:
                continue
            rows.append(f"{rel} | {size} bytes")
        return "\n".join(rows)

    def build_selected(self, relative_paths: list[str], max_chars: int | None = None) -> str:
        limit = self.max_chars if max_chars is None else max_chars
        chunks: list[str] = []
        total = 0
        seen: set[Path] = set()

        for raw in relative_paths:
            try:
                path = (self.workspace / raw).resolve()
                path.relative_to(self.workspace)
            except Exception:
                continue
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            if not self._is_safe_path(path):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            rel = path.relative_to(self.workspace)
            block = f"\n--- FILE: {rel} ---\n{text}\n"
            if total + len(block) > limit:
                break
            chunks.append(block)
            total += len(block)

        return "".join(chunks)

    def build(self) -> str:
        files = [str(path.relative_to(self.workspace)) for path in self._iter_safe_files()]
        return self.build_selected(files)
