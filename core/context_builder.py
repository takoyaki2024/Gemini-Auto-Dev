from __future__ import annotations
from pathlib import Path

SECRET_NAMES = {".env", "id_rsa", "id_ed25519", "credentials.json"}

class ContextBuilder:
    def __init__(self, workspace: Path, max_chars: int = 120_000):
        self.workspace = workspace.resolve()
        self.max_chars = max_chars

    def build(self) -> str:
        chunks: list[str] = []
        total = 0
        skip_dirs = {".git", ".venv", "venv", "node_modules", "Library", "Temp", "obj", "bin"}
        for path in self.workspace.rglob("*"):
            if not path.is_file():
                continue
            if any(part in skip_dirs for part in path.parts):
                continue
            if path.name in SECRET_NAMES or path.suffix.lower() in {".key", ".pem", ".pfx"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            rel = path.relative_to(self.workspace)
            block = f"\n--- FILE: {rel} ---\n{text}\n"
            if total + len(block) > self.max_chars:
                break
            chunks.append(block)
            total += len(block)
        return "".join(chunks)
