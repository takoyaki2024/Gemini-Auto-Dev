from __future__ import annotations
from pathlib import Path
import subprocess

class GitManager:
    def __init__(self, workspace: Path):
        self.workspace = workspace

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args], cwd=self.workspace,
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )

    def ensure_repo(self) -> None:
        if self._run("rev-parse", "--is-inside-work-tree").returncode != 0:
            self._run("init")
            self._run("branch", "-M", "main")

    def checkpoint(self, message: str) -> None:
        self.ensure_repo()
        self._run("add", "-A")
        staged = self._run("diff", "--cached", "--quiet")
        if staged.returncode != 0:
            self._run("commit", "-m", message)

    def status(self) -> str:
        return self._run("status", "--short").stdout
