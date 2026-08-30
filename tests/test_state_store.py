from pathlib import Path

from core.state_store import StateStore


def test_resume_snapshot_round_trip(tmp_path: Path):
    state = StateStore(tmp_path)
    state.add("task", {"task": "build feature"})
    state.save_resume({"task": "build feature", "phase": "review", "evidence": "tests passed"})

    snapshot = state.resumable_snapshot()
    assert snapshot is not None
    assert snapshot["task"] == "build feature"
    assert snapshot["phase"] == "review"
    assert state.resumable_task() == "build feature"


def test_completed_task_clears_resume_snapshot(tmp_path: Path):
    state = StateStore(tmp_path)
    state.add("task", {"task": "build feature"})
    state.save_resume({"task": "build feature", "phase": "review"})
    state.add("completed", {"task": "build feature"})

    assert state.resumable_snapshot() is None
    assert state.resumable_task() is None


def test_stopped_task_clears_resume_snapshot(tmp_path: Path):
    state = StateStore(tmp_path)
    state.add("task", {"task": "build feature"})
    state.save_resume({"task": "build feature", "phase": "fixing"})
    state.add("stopped", {"reason": "STUCK_DETECTED"})

    assert state.resumable_snapshot() is None
    assert state.resumable_task() is None


def test_new_task_invalidates_old_snapshot(tmp_path: Path):
    state = StateStore(tmp_path)
    state.add("task", {"task": "old task"})
    state.save_resume({"task": "old task", "phase": "review"})
    state.add("task", {"task": "new task"})

    assert state.resumable_snapshot() is None
