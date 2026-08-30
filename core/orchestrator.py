from __future__ import annotations
from pathlib import Path
import hashlib

from core.context_builder import ContextBuilder
from core.gemini_client import GeminiClient
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
        self.client = GeminiClient(config.get("model", "gemini-3.7-flash"))
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
            plan = self.client.structured(system, prompt, DevPlan)
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
                            "\n\nSTUCK WARNING: Previous fixes repeated the same failure. "
                            "Abandon the prior approach and use a materially different solution."
                        )
                        repeated = 0
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
            review = self.client.structured(REVIEW_SYSTEM, review_prompt, ReviewResult)
            self.state.add("review", review.model_dump())

            if review.approved and plan.done:
                if self.config.get("auto_commit", True):
                    self.git.checkpoint(f"auto-dev: {task[:72]}")
                return "COMPLETED: task implemented, reviewed, and checkpointed."

            latest_failure = (
                "REVIEW_NOT_APPROVED:\n" +
                (review.next_instruction or "\n".join(review.issues) or "Continue implementing the task.")
            )
