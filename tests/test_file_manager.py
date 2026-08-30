from pathlib import Path
from core.models import FileAction
from tools.file_manager import FileManager
from tools.security_gate import SecurityGate

def test_create_and_modify(tmp_path: Path):
    fm = FileManager(tmp_path, SecurityGate(tmp_path))
    fm.apply(FileAction(type="create", path="a.txt", content="hello"))
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "hello"
    fm.apply(FileAction(type="modify", path="a.txt", content="world"))
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "world"
