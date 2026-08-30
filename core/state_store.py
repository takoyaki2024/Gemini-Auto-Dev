from __future__ import annotations
from pathlib import Path
import sqlite3, json, time


class StateStore:
    def __init__(self, workspace: Path):
        state_dir = workspace / ".gemini-auto-dev"
        state_dir.mkdir(exist_ok=True)
        self.db = state_dir / "state.db"
        with sqlite3.connect(self.db) as con:
            con.execute("""CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                kind TEXT NOT NULL,
                payload TEXT NOT NULL
            )""")

    def add(self, kind: str, payload) -> None:
        with sqlite3.connect(self.db) as con:
            con.execute(
                "INSERT INTO events(ts, kind, payload) VALUES(?,?,?)",
                (time.time(), kind, json.dumps(payload, ensure_ascii=False, default=str)),
            )

    def latest(self, kind: str | None = None) -> dict | None:
        sql = "SELECT id, ts, kind, payload FROM events"
        params: tuple = ()
        if kind:
            sql += " WHERE kind=?"
            params = (kind,)
        sql += " ORDER BY id DESC LIMIT 1"
        with sqlite3.connect(self.db) as con:
            row = con.execute(sql, params).fetchone()
        if not row:
            return None
        try:
            payload = json.loads(row[3])
        except Exception:
            payload = row[3]
        return {"id": row[0], "ts": row[1], "kind": row[2], "payload": payload}

    def resumable_task(self) -> str | None:
        last_task = self.latest("task")
        if not last_task or not isinstance(last_task["payload"], dict):
            return None
        task = str(last_task["payload"].get("task", "")).strip()
        if not task:
            return None
        with sqlite3.connect(self.db) as con:
            row = con.execute(
                "SELECT kind FROM events WHERE id>? AND kind IN ('completed','stopped','task') ORDER BY id DESC LIMIT 1",
                (last_task["id"],),
            ).fetchone()
        if row and row[0] in {"completed", "stopped", "task"}:
            return None
        latest = self.latest()
        if latest and latest["kind"] == "paused":
            return task
        return None
