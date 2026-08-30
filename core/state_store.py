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
