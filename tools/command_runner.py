from __future__ import annotations
from pathlib import Path
import subprocess
from tools.security_gate import SecurityGate

class CommandResult:
    def __init__(self, command: str, code: int, stdout: str, stderr: str):
        self.command = command
        self.code = code
        self.stdout = stdout
        self.stderr = stderr

    @property
    def ok(self) -> bool:
        return self.code == 0

    def text(self) -> str:
        return f"$ {self.command}\nexit={self.code}\nSTDOUT:\n{self.stdout}\nSTDERR:\n{self.stderr}"

class CommandRunner:
    def __init__(self, workspace: Path, gate: SecurityGate, timeout: int = 300):
        self.workspace = workspace
        self.gate = gate
        self.timeout = timeout

    def run(self, command: str) -> CommandResult:
        self.gate.check_command(command)
        try:
            p = subprocess.run(
                command,
                cwd=self.workspace,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
            )
            return CommandResult(command, p.returncode, p.stdout, p.stderr)
        except subprocess.TimeoutExpired as exc:
            return CommandResult(command, 124, exc.stdout or "", f"TIMEOUT: {exc}")
