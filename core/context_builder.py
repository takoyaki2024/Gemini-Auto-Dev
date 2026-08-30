from __future__ import annotations
from pathlib import Path

SECRET_NAMES = {".env", "id_rsa", "id_ed25519", "credentials.json"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "Library", "Temp", "obj", "bin"}
SECRET_SUFFIXES = {".key", ".pem", ".pfx"}


class ContextBuilder:
    def __init__(self, workspace: Path, max_chars: int = 120_000):
        self.workspace = workspace.resolve()
        self.max_chars = max_chars

    def _iter_safe_files(self):
        for path in self.workspace.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.name in SECRET_NAMES or path.suffix.lower() in SECRET_SUFFIXES:
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
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.name in SECRET_NAMES or path.suffix.lower() in SECRET_SUFFIXES:
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
