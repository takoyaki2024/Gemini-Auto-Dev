from __future__ import annotations
import os
from google import genai
from google.genai import types
from pydantic import BaseModel

class GeminiClient:
    def __init__(self, model: str):
        if not os.getenv("GEMINI_API_KEY"):
            raise RuntimeError("GEMINI_API_KEY が設定されていません。")
        self.model = model
        self.client = genai.Client()

    def structured(self, system: str, prompt: str, schema: type[BaseModel]) -> BaseModel:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        if not response.text:
            raise RuntimeError("Geminiから空の応答が返りました。")
        return schema.model_validate_json(response.text)
