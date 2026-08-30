from __future__ import annotations
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ManagedTask:
    instruction: str
    kind: str
    priority: int


class DeterministicTaskManager:
    """Cheap task shaping that never consumes AI quota."""

    QUALITY_WORDS = ("品質", "quality", "改善", "refactor", "整理")
    TEST_WORDS = ("テスト", "test", "pytest", "build", "ビルド", "確認")
    FIX_WORDS = ("修正", "fix", "error", "エラー", "問題", "bug")

    @staticmethod
    def _has(text: str, words: tuple[str, ...]) -> bool:
        low = text.lower()
        return any(word.lower() in low for word in words)

    def decompose(self, task: str) -> list[ManagedTask]:
        task = re.sub(r"\s+", " ", task).strip()
        if not task:
            return []

        items: list[ManagedTask] = [ManagedTask(task, "implementation", 10)]
        if self._has(task, self.QUALITY_WORDS):
            items.append(ManagedTask("Preserve current behavior while improving code quality and maintainability.", "quality", 20))
        if self._has(task, self.TEST_WORDS):
            items.append(ManagedTask("Run the project's appropriate existing tests/build checks after changes.", "validation", 30))
        if self._has(task, self.FIX_WORDS):
            items.append(ManagedTask("If validation fails, diagnose the concrete failure and fix it without unrelated changes.", "repair", 40))
        return items

    def worker_instruction(self, task: str) -> tuple[str, list[ManagedTask]]:
        items = self.decompose(task)
        if len(items) <= 1:
            return task.strip(), items
        lines = ["ORIGINAL REQUEST:", task.strip(), "", "DETERMINISTIC WORK PLAN:"]
        for index, item in enumerate(items, 1):
            lines.append(f"{index}. [{item.kind}] {item.instruction}")
        lines.append("Complete the plan in dependency order and avoid unrelated work.")
        return "\n".join(lines), items
