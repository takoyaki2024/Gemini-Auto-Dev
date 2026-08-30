from pathlib import Path
import pytest
from tools.security_gate import SecurityGate, SecurityError

def test_blocks_outside_workspace(tmp_path: Path):
    gate = SecurityGate(tmp_path)
    with pytest.raises(SecurityError):
        gate.resolve_path("../outside.txt")

def test_allows_inside_workspace(tmp_path: Path):
    gate = SecurityGate(tmp_path)
    assert gate.resolve_path("src/app.py") == (tmp_path / "src/app.py").resolve()

def test_blocks_dangerous_command(tmp_path: Path):
    gate = SecurityGate(tmp_path)
    with pytest.raises(SecurityError):
        gate.check_command("diskpart")
