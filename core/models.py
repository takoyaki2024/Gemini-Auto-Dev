from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

class FileAction(BaseModel):
    type: Literal["create", "modify", "delete"]
    path: str
    content: str | None = None

class DevPlan(BaseModel):
    summary: str
    actions: list[FileAction] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    done: bool = False
    notes: str = ""

class ReviewResult(BaseModel):
    approved: bool
    issues: list[str] = Field(default_factory=list)
    next_instruction: str = ""
