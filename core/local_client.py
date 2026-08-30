from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LocalAIUnavailable(RuntimeError):
    """Raised when the local AI server/model cannot be used."""


class LocalAIClient:
    def __init__(self, endpoint: str = "http://127.0.0.1:11434", model: str = "", timeout: int = 180):
        self.endpoint = endpoint.rstrip("/")
        self.model = model.strip()
        self.timeout = max(5, int(timeout))
        self._resolved_model: str | None = None

    @staticmethod
    def choose_model(names: list[str], requested: str = "") -> str:
        if requested:
            for name in names:
                if name == requested or name.startswith(requested + ":"):
                    return name
            raise LocalAIUnavailable(f"Configured local model is not installed: {requested}")

        if not names:
            raise LocalAIUnavailable("No local Ollama models are installed.")

        priorities = ("qwen", "coder", "codestral", "deepseek", "llama", "mistral")
        lowered = [(name, name.lower()) for name in names]
        for keyword in priorities:
            for name, low in lowered:
                if keyword in low:
                    return name
        return names[0]

    def _request_json(self, path: str, payload: dict | None = None) -> dict:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="GET" if payload is None else "POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise LocalAIUnavailable(str(exc)) from exc

    def resolve_model(self) -> str:
        if self._resolved_model:
            return self._resolved_model
        response = self._request_json("/api/tags")
        names = [item.get("name", "") for item in response.get("models", []) if item.get("name")]
        self._resolved_model = self.choose_model(names, self.model)
        return self._resolved_model

    def structured(self, system: str, prompt: str, schema: type[T]) -> T:
        model = self.resolve_model()
        payload = {
            "model": model,
            "stream": False,
            "format": schema.model_json_schema(),
            "messages": [
                {"role": "system", "content": system + "\nReturn valid JSON matching the supplied schema."},
                {"role": "user", "content": prompt},
            ],
            "options": {"temperature": 0.1},
        }
        response = self._request_json("/api/chat", payload)
        content = response.get("message", {}).get("content", "")
        if not content:
            raise LocalAIUnavailable("Local AI returned an empty response.")
        try:
            return schema.model_validate_json(content)
        except Exception as exc:
            raise LocalAIUnavailable(f"Local AI returned invalid structured output: {exc}") from exc
