from __future__ import annotations
import argparse
from pathlib import Path
import yaml

from core.orchestrator import Orchestrator
from core.state_store import StateStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Gemini Auto Dev")
    parser.add_argument("workspace", nargs="?", help="Target project directory")
    parser.add_argument("--task", help="Development task")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--no-resume", action="store_true", help="Do not resume a paused task")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    workspace = Path(args.workspace or config.get("workspace", "./workspace")).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    state = StateStore(workspace)
    task = (args.task or "").strip()
    resume = None
    if not task and not args.no_resume:
        resume = state.resumable_snapshot()
        if resume:
            task = str(resume.get("task", "")).strip()
            print(f"RESUME: phase={resume.get('phase', 'implementation')} | task: {task}")
        else:
            task = state.resumable_task() or ""
            if task:
                print(f"RESUME: legacy paused task restored: {task}")

    if not task:
        task = input("開発依頼> ").strip()
    if not task:
        print("依頼が空です。")
        return 2

    orchestrator = Orchestrator(workspace=workspace, config=config)
    result = orchestrator.run(task, resume=resume)
    print(result)
    return 0 if result.startswith("COMPLETED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
