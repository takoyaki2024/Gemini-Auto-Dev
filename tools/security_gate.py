from __future__ import annotations
from pathlib import Path
import re

class SecurityError(RuntimeError):
    pass

class SecurityGate:
    BLOCKED_PATTERNS = [
        r"\bformat\b",
        r"\bdiskpart\b",
        r"\bshutdown\b",
        r"\breboot\b",
        r"\breg\s+delete\b",
        r"\brm\s+-rf\s+[/\\]\b",
        r"\bdel\s+/[sq]\s+[a-zA-Z]:\\",
        r"\bRemove-Item\b.*\b-Recurse\b.*[A-Za-z]:\\(?:Windows|Users)\b",
    ]

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

    def resolve_path(self, raw: str) -> Path:
        candidate = (self.workspace / raw).resolve()
        try:
            candidate.relative_to(self.workspace)
        except ValueError as exc:
            raise SecurityError(f"workspace外へのアクセスを拒否: {raw}") from exc
        return candidate

    def check_command(self, command: str) -> None:
        for pat in self.BLOCKED_PATTERNS:
            if re.search(pat, command, re.IGNORECASE):
                raise SecurityError(f"危険なコマンドを拒否: {command}")
