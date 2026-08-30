from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from core.gemini_client import GeminiClient
from core.local_client import LocalAIClient, LocalAIUnavailable

T = TypeVar("T", bound=BaseModel)


class AIRouter:
    def __init__(self, config: dict):
        gemini = config.get("gemini", {})
        self.gemini = GeminiClient(
            config.get("model", "gemini-3.7-flash"),
            max_retries=int(gemini.get("max_retries", 2)),
        )
        local = config.get("local_ai", {})
        self.local_enabled = bool(local.get("enabled", True))
        self.local = LocalAIClient(
            endpoint=str(local.get("endpoint", "http://127.0.0.1:11434")),
            model=str(local.get("model", "")),
            timeout=int(local.get("timeout_seconds", 90)),
        )

    def local_structured(self, system: str, prompt: str, schema: type[T]) -> T | None:
        if not self.local_enabled:
            return None
        try:
            return self.local.structured(system, prompt, schema)
        except LocalAIUnavailable as exc:
            print(f"Local helper skipped: {exc}")
            return None

    def gemini_structured(self, system: str, prompt: str, schema: type[T]) -> T:
        return self.gemini.structured(system, prompt, schema)

    def structured(self, system: str, prompt: str, schema: type[T], prefer_local: bool = False) -> tuple[T, str]:
        if prefer_local:
            result = self.local_structured(system, prompt, schema)
            if result is not None:
                return result, "local"
        return self.gemini_structured(system, prompt, schema), "gemini"
