from __future__ import annotations
from pathlib import Path
import hashlib

from core.ai_router import AIRouter
from core.context_builder import ContextBuilder
from core.gemini_client import GeminiQuotaPaused, GeminiTemporaryUnavailable
from core.models import DevPlan, ReviewResult
from core.state_store import StateStore
from tools.security_gate import SecurityGate
from tools.file_manager import FileManager
from tools.command_runner import CommandRunner
from tools.git_manager import GitManager

MANAGER_SYSTEM = """You are the sole coding agent in an autonomous development system.
Return only actions inside the requested workspace.
Prefer small, testable changes. Never request secrets.
Use commands needed to build/test/install dependencies.
Do not change OS-wide settings unless absolutely required.
When the task is fully complete, set done=true."""

FIXER_SYSTEM = """You are fixing a failed autonomous software-development attempt.
Analyze the current project and latest command output.
Choose a materially different fix if the same error is repeating.
Return only safe workspace file actions and build/test/install commands."""

REVIEW_SYSTEM = """You are the final reviewer.
Approve only when the requested task is implemented and available evidence shows no major problem.
If not approved, give one concrete next_instruction."""

class Orchestrator:
    def __init__(self, workspace: Path, config: dict):
        self.workspace = workspace.resolve()
        self.config = config
        self.ai = AIRouter(config)
        self.context = ContextBuilder(self.workspace)
        self.gate = SecurityGate(self.workspace)
        self.files = FileManager(self.workspace, self.gate)
        self.runner = CommandRunner(
            self.workspace, self.gate, int(config.get("command_timeout_seconds", 300))
        )
        self.git = GitManager(self.workspace)
        self.state = StateStore(self.workspace)
        stuck = config.get("stuck", {})
        self.identical_limit = int(stuck.get("identical_error_limit", 3))
        self.escape_attempts = int(stuck.get("escape_attempts", 1))

    @staticmethod
    def _sig(text: str) -> str:
        normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return hashlib.sha256(normalized[-12000:].encode("utf-8", "ignore")).hexdigest()

    def _call_structured(self, system: str, prompt: str, schema, prefer_local: bool = True):
        try:
            result, backend = self.ai.structured(system, prompt, schema, prefer_local=prefer_local)
            self.state.add("ai_call", {"backend": backend, "schema": schema.__name__})
            print(f"AI backend: {backend}")
            return result
        except GeminiQuotaPaused as exc:
            self.state.add("paused", {"reason": "QUOTA_PAUSED", "error": str(exc)})
            return "QUOTA_PAUSED"
        except GeminiTemporaryUnavailable as exc:
            self.state.add("paused", {"reason": "TEMPORARILY_UNAVAILABLE", "error": str(exc)})
            return "TEMPORARILY_UNAVAILABLE"

    def _apply_plan(self, plan: DevPlan) -> list[str]:
        logs: list[str] = []
        for action in plan.actions:
            self.files.apply(action)
            logs.append(f"{action.type}: {action.path}")
        for command in plan.commands:
            result = self.runner.run(command)
            text = result.text()
            logs.append(text)
            self.state.add("command", {"command": command, "code": result.code, "output": text[-20000:]})
            if not result.ok:
                break
        return logs

    def run(self, task: str) -> str:
        self.git.ensure_repo()
        self.git.checkpoint("checkpoint: before autonomous task")
        self.state.add("task", {"task": task})

        latest_failure = ""
        repeated = 0
        last_sig = ""
        escape_used = 0
        force_gemini_next = False

        while True:
            project = self.context.build()
            prompt = f"""USER TASK:
{task}

CURRENT PROJECT:
{project}

LATEST FAILURE:
{latest_failure or "(none)"}
"""
            system = FIXER_SYSTEM if latest_failure else MANAGER_SYSTEM
            plan = self._call_structured(system, prompt, DevPlan, prefer_local=not force_gemini_next)
            force_gemini_next = False
            if plan == "QUOTA_PAUSED":
                return "PAUSED: QUOTA_PAUSED. Free-tier/API quota was reached. State was saved; retry later."
            if plan == "TEMPORARILY_UNAVAILABLE":
                return "PAUSED: TEMPORARILY_UNAVAILABLE. Gemini stayed busy after automatic retries. State was saved; retry later."
            self.state.add("plan", plan.model_dump())

            logs = self._apply_plan(plan)
            evidence = "\n\n".join(logs)
            failed_logs = [x for x in logs if "\nexit=" in x and "\nexit=0\n" not in x]

            if failed_logs:
                latest_failure = failed_logs[-1][-20000:]
                sig = self._sig(latest_failure)
                repeated = repeated + 1 if sig == last_sig else 1
                last_sig = sig

                if repeated >= self.identical_limit:
                    if escape_used < self.escape_attempts:
                        escape_used += 1
                        latest_failure += (
                            "\n\nSTUCK WARNING: Local-first fixes repeated the same failure. "
                            "Escalate to Gemini and abandon the prior approach for a materially different solution."
                        )
                        repeated = 0
                        force_gemini_next = True
                        continue
                    self.state.add("stopped", {"reason": "STUCK_DETECTED", "failure": latest_failure})
                    return "STOPPED: STUCK_DETECTED\n" + latest_failure
                continue

            review_prompt = f"""TASK:
{task}

PROJECT:
{self.context.build()}

LATEST EXECUTION EVIDENCE:
{evidence or "(no commands were run)"}
"""
            review = self._call_structured(REVIEW_SYSTEM, review_prompt, ReviewResult, prefer_local=True)
            if review == "QUOTA_PAUSED":
                return "PAUSED: QUOTA_PAUSED. Free-tier/API quota was reached. State was saved; retry later."
            if review == "TEMPORARILY_UNAVAILABLE":
                return "PAUSED: TEMPORARILY_UNAVAILABLE. Gemini stayed busy after automatic retries. State was saved; retry later."
            self.state.add("review", review.model_dump())

            if review.approved and plan.done:
                if self.config.get("auto_commit", True):
                    self.git.checkpoint(f"auto-dev: {task[:72]}")
                return "COMPLETED: task implemented, reviewed, and checkpointed."

            latest_failure = (
                "REVIEW_NOT_APPROVED:\n" +
                (review.next_instruction or "\n".join(review.issues) or "Continue implementing the task.")
            )
