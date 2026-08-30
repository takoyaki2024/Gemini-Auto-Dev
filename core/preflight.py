from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(frozen=True)
class PreflightCheck:
    project_type: str
    command: str | None


class PreflightDetector:
    """Detect one cheap, existing validation command without using AI."""

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

    def detect(self) -> PreflightCheck:
        if (self.workspace / "pytest.ini").exists() or (self.workspace / "pyproject.toml").exists() or list(self.workspace.glob("test*.py")) or (self.workspace / "tests").is_dir():
            return PreflightCheck("python", "python -m pytest -q")

        package = self.workspace / "package.json"
        if package.exists():
            try:
                data = json.loads(package.read_text(encoding="utf-8"))
                scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
            except Exception:
                scripts = {}
            if "test" in scripts and "no test specified" not in str(scripts.get("test", "")).lower():
                return PreflightCheck("node", "npm test -- --runInBand")
            if "build" in scripts:
                return PreflightCheck("node", "npm run build")

        solutions = list(self.workspace.glob("*.sln"))
        projects = list(self.workspace.glob("*.csproj"))
        if solutions or projects:
            return PreflightCheck("dotnet", "dotnet test")

        if (self.workspace / "Cargo.toml").exists():
            return PreflightCheck("rust", "cargo test")
        if (self.workspace / "go.mod").exists():
            return PreflightCheck("go", "go test ./...")
        return PreflightCheck("unknown", None)
