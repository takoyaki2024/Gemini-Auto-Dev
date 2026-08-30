from __future__ import annotations
from pathlib import Path
import hashlib

from core.ai_router import AIRouter
from core.context_builder import ContextBuilder
from core.gemini_client import GeminiQuotaPaused, GeminiTemporaryUnavailable
from core.models import DevPlan, ReviewResult
from core.state_store import StateStore
from core.task_manager import DeterministicTaskManager
from tools.security_gate import SecurityGate
from tools.file_manager import FileManager
from tools.command_runner import CommandRunner
from tools.git_manager import GitManager

MANAGER_SYSTEM = """You are the coding worker in an autonomous development system.
Implement the requested task using only the supplied project context.
Return only actions inside the requested workspace.
Prefer small, testable changes. Never request secrets.
Use commands needed to build/test/install project dependencies.
Do not change OS-wide settings.
When the task is fully complete, set done=true."""

FIXER_SYSTEM = """You are fixing a failed autonomous software-development attempt.
Analyze the supplied relevant project files and latest failure.
Choose a materially different fix if the same error is repeating.
Return only safe workspace file actions and build/test commands."""

REVIEW_SYSTEM = """You are the final reviewer.
Approve only when the requested task is implemented and available execution evidence shows no major problem.
If not approved, give one concrete next_instruction."""


class Orchestrator:
    def __init__(self, workspace: Path, config: dict):
        self.workspace = workspace.resolve()
        self.config = config
        self.ai = AIRouter(config)
        self.manager = DeterministicTaskManager()
        self.context = ContextBuilder(self.workspace, int(config.get("context", {}).get("max_chars", 80_000)))
        self.gate = SecurityGate(self.workspace)
        self.files = FileManager(self.workspace, self.gate)
        self.runner = CommandRunner(self.workspace, self.gate, int(config.get("command_timeout_seconds", 300)))
        self.git = GitManager(self.workspace)
        self.state = StateStore(self.workspace)
        stuck = config.get("stuck", {})
        self.identical_limit = int(stuck.get("identical_error_limit", 3))
        self.escape_attempts = int(stuck.get("escape_attempts", 1))
        self.max_context_files = int(config.get("context", {}).get("max_files", 12))

    @staticmethod
    def _sig(text: str) -> str:
        normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return hashlib.sha256(normalized[-12000:].encode("utf-8", "ignore")).hexdigest()

    def _gemini_call(self, system: str, prompt: str, schema, reason: str):
        print(f"AI backend: gemini | reason: {reason}")
        try:
            result = self.ai.gemini_structured(system, prompt, schema)
            self.state.add("ai_call", {"backend": "gemini", "schema": schema.__name__, "reason": reason})
            return result
        except GeminiQuotaPaused as exc:
            self.state.add("paused", {"reason": "QUOTA_PAUSED", "error": str(exc)})
            return "QUOTA_PAUSED"
        except GeminiTemporaryUnavailable as exc:
            self.state.add("paused", {"reason": "TEMPORARILY_UNAVAILABLE", "error": str(exc)})
            return "TEMPORARILY_UNAVAILABLE"

    def _select_context(self, task: str, latest_failure: str = "") -> str:
        project, files = self.context.build_relevant(task, latest_failure, self.max_context_files)
        print(f"Context selector: deterministic | files: {len(files)}")
        self.state.add("context_selection", {"backend": "deterministic", "files": files})
        return project

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

    @staticmethod
    def _pause_message(code: str) -> str:
        if code == "QUOTA_PAUSED":
            return "PAUSED: QUOTA_PAUSED. Free-tier/API quota was reached. State was saved; development stopped."
        return "PAUSED: TEMPORARILY_UNAVAILABLE. Gemini stayed busy after fast retries. State was saved; retry later."

    def run(self, task: str) -> str:
        self.git.ensure_repo()
        self.git.checkpoint("checkpoint: before autonomous task")
        self.state.add("task", {"task": task})
        worker_task, managed = self.manager.worker_instruction(task)
        self.state.add("manager_plan", {"backend": "deterministic", "items": [item.__dict__ for item in managed]})
        print(f"Manager: deterministic | steps: {len(managed)}")
        latest_failure = ""
        repeated = 0
        last_sig = ""
        escape_used = 0

        while True:
            project = self._select_context(worker_task, latest_failure)
            prompt = f"""USER TASK AND WORK PLAN:
{worker_task}

RELEVANT PROJECT CONTEXT:
{project}

LATEST FAILURE:
{latest_failure or "(none)"}
"""
            system = FIXER_SYSTEM if latest_failure else MANAGER_SYSTEM
            reason = "fixing failure" if latest_failure else "implementation"
            plan = self._gemini_call(system, prompt, DevPlan, reason)
            if isinstance(plan, str):
                return self._pause_message(plan)
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
                        latest_failure += "\n\nSTUCK WARNING: The same failure repeated. Abandon the prior approach and choose a materially different solution."
                        repeated = 0
                        continue
                    self.state.add("stopped", {"reason": "STUCK_DETECTED", "failure": latest_failure})
                    return "STOPPED: STUCK_DETECTED\n" + latest_failure
                continue

            if not plan.done:
                latest_failure = "CONTINUE_IMPLEMENTATION: Previous plan completed without command failure but task is not done."
                continue

            review_context = self._select_context(worker_task)
            review_prompt = f"""TASK:
{worker_task}

RELEVANT PROJECT CONTEXT:
{review_context}

LATEST EXECUTION EVIDENCE:
{evidence or "(no commands were run)"}
"""
            review = self._gemini_call(REVIEW_SYSTEM, review_prompt, ReviewResult, "final review")
            if isinstance(review, str):
                return self._pause_message(review)
            self.state.add("review", review.model_dump())
            if review.approved:
                if self.config.get("auto_commit", True):
                    self.git.checkpoint(f"auto-dev: {task[:72]}")
                self.state.add("completed", {"task": task})
                return "COMPLETED: task implemented, reviewed, and checkpointed."
            latest_failure = "REVIEW_NOT_APPROVED:\n" + (review.next_instruction or "\n".join(review.issues) or "Continue implementing the task.")
