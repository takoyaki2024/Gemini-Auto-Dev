from __future__ import annotations

import os
import time
from typing import TypeVar

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class GeminiTemporaryUnavailable(RuntimeError):
    """Raised when Gemini remains temporarily unavailable after retries."""


class GeminiQuotaPaused(RuntimeError):
    """Raised when the API reports a quota/rate-limit condition."""


class GeminiClient:
    def __init__(self, model: str, max_retries: int = 8):
        if not os.getenv("GEMINI_API_KEY"):
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        self.model = model
        self.max_retries = max(1, max_retries)
        self.client = genai.Client()

    @staticmethod
    def _status_code(exc: Exception) -> int | None:
        value = getattr(exc, "status_code", None)
        if isinstance(value, int):
            return value
        value = getattr(exc, "code", None)
        return value if isinstance(value, int) else None

    @staticmethod
    def _retry_delay(attempt: int) -> int:
        delays = (5, 10, 20, 40, 60, 60, 60)
        return delays[min(attempt - 1, len(delays) - 1)]

    def structured(self, system: str, prompt: str, schema: type[T]) -> T:
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        response_mime_type="application/json",
                        response_schema=schema,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(
                            disable=True
                        ),
                    ),
                )
                if not response.text:
                    raise RuntimeError("Gemini returned an empty response.")
                return schema.model_validate_json(response.text)

            except errors.APIError as exc:
                last_error = exc
                code = self._status_code(exc)
                message = str(exc)

                if code == 429 or "RESOURCE_EXHAUSTED" in message.upper():
                    raise GeminiQuotaPaused(message) from exc

                temporary = (
                    code in {500, 502, 503, 504}
                    or "UNAVAILABLE" in message.upper()
                    or "HIGH DEMAND" in message.upper()
                )
                if not temporary:
                    raise

                if attempt < self.max_retries:
                    delay = self._retry_delay(attempt)
                    print(
                        f"Gemini is temporarily unavailable (attempt {attempt}/{self.max_retries}). "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    continue

        raise GeminiTemporaryUnavailable(str(last_error) if last_error else "Gemini unavailable")
