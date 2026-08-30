from __future__ import annotations
from pathlib import Path
from core.models import FileAction
from tools.security_gate import SecurityGate

class FileManager:
    def __init__(self, workspace: Path, gate: SecurityGate):
        self.workspace = workspace
        self.gate = gate

    def apply(self, action: FileAction) -> None:
        path = self.gate.resolve_path(action.path)
        if action.type == "delete":
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                raise RuntimeError(f"ディレクトリ削除は拒否: {action.path}")
            return

        if action.content is None:
            raise RuntimeError(f"{action.type} には content が必要です: {action.path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(action.content, encoding="utf-8")
