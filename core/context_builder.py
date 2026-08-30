from __future__ import annotations
from pathlib import Path
import re

SECRET_NAMES = {".env", "id_rsa", "id_ed25519", "credentials.json"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "Library", "Temp", "obj", "bin"}
SECRET_SUFFIXES = {".key", ".pem", ".pfx"}
IMPORTANT_NAMES = {
    "readme.md", "pyproject.toml", "requirements.txt", "package.json", "package-lock.json",
    "pytest.ini", "setup.cfg", "setup.py", "cargo.toml", "go.mod", "pom.xml",
}
CODE_SUFFIXES = {".py", ".cs", ".js", ".ts", ".tsx", ".jsx", ".java", ".cpp", ".c", ".h", ".go", ".rs", ".json", ".yaml", ".yml"}


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
            if path.is_file() and self._is_safe_path(path):
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

    @staticmethod
    def _keywords(text: str) -> set[str]:
        words = re.findall(r"[A-Za-z0-9_]{3,}|[\u3040-\u30ff\u3400-\u9fff]{2,}", text.lower())
        stop = {"this", "that", "with", "from", "project", "code", "test", "tests", "file", "files", "してください", "プロジェクト", "コード", "必要", "確認"}
        return {word for word in words if word not in stop}

    @staticmethod
    def _stem_key(path: Path) -> str:
        stem = path.stem.lower()
        for prefix in ("test_", "tests_", "spec_"):
            if stem.startswith(prefix):
                stem = stem[len(prefix):]
        for suffix in ("_test", "_tests", ".test", ".spec"):
            if stem.endswith(suffix):
                stem = stem[:-len(suffix)]
        return stem

    def _adjacent_files(self, selected: list[str], candidates: list[Path]) -> list[str]:
        chosen = set(selected)
        selected_paths = [(self.workspace / rel).resolve() for rel in selected]
        selected_stems = {self._stem_key(path) for path in selected_paths}
        selected_names = {path.stem.lower() for path in selected_paths}

        for path in candidates:
            rel = path.relative_to(self.workspace).as_posix()
            if rel in chosen:
                continue
            low = rel.lower()
            stem_key = self._stem_key(path)
            # Pair source and test files with the same logical stem.
            if stem_key and stem_key in selected_stems and ("test" in low or any("test" in x.lower() for x in selected)):
                chosen.add(rel)
                continue
            # Cheap Python import adjacency: inspect only selected Python files.
            if path.suffix.lower() == ".py" and path.stem.lower() in selected_names:
                chosen.add(rel)

        imported: set[str] = set()
        for selected_path in selected_paths:
            if selected_path.suffix.lower() != ".py":
                continue
            try:
                text = selected_path.read_text(encoding="utf-8")[:20_000]
            except Exception:
                continue
            for module in re.findall(r"(?:from|import)\s+([A-Za-z_][A-Za-z0-9_\.]*)", text):
                imported.add(module.split(".")[-1].lower())
        for path in candidates:
            if path.suffix.lower() == ".py" and path.stem.lower() in imported:
                chosen.add(path.relative_to(self.workspace).as_posix())
        return list(chosen)

    def select_relevant(self, task: str, latest_failure: str = "", max_files: int = 12) -> list[str]:
        candidates = list(self._iter_safe_files())
        # Tiny projects are cheaper and more reliable when all safe files are supplied.
        if len(candidates) <= max_files:
            return [path.relative_to(self.workspace).as_posix() for path in candidates]

        keywords = self._keywords(task + "\n" + latest_failure)
        scored: list[tuple[int, float, str]] = []
        for path in candidates:
            try:
                rel = path.relative_to(self.workspace).as_posix()
                stat = path.stat()
            except Exception:
                continue
            low = rel.lower()
            score = 0
            if path.name.lower() in IMPORTANT_NAMES:
                score += 8
            if path.suffix.lower() in CODE_SUFFIXES:
                score += 3
            if "test" in low:
                score += 2
            for keyword in keywords:
                if keyword in low:
                    score += 10
            scored.append((score, stat.st_mtime, rel))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        seed_count = max(1, max_files // 2)
        selected = [rel for _, _, rel in scored[:seed_count]]
        adjacent = self._adjacent_files(selected, candidates)
        priority = selected + [rel for rel in adjacent if rel not in selected] + [rel for _, _, rel in scored if rel not in selected]
        return priority[:max_files]

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
            if path in seen or not path.is_file() or not self._is_safe_path(path):
                continue
            seen.add(path)
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            rel = path.relative_to(self.workspace)
            block = f"\n--- FILE: {rel} ---\n{text}\n"
            if total + len(block) > limit:
                continue
            chunks.append(block)
            total += len(block)
        return "".join(chunks)

    def build_relevant(self, task: str, latest_failure: str = "", max_files: int = 12) -> tuple[str, list[str]]:
        selected = self.select_relevant(task, latest_failure, max_files)
        context = self.build_selected(selected)
        if context:
            return context, selected
        return self.build(), selected

    def build(self) -> str:
        files = [str(path.relative_to(self.workspace)) for path in self._iter_safe_files()]
        return self.build_selected(files)
