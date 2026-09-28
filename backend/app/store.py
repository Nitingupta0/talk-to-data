"""SQLite persistence for datasets, chats and messages, plus an in-memory dataframe cache."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path

import pandas as pd

from . import config
from .data import read_file

_SCHEMA = """
CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    sheet TEXT,
    created_at REAL NOT NULL,
    profile TEXT NOT NULL,
    semantics TEXT NOT NULL,
    insights TEXT
);
CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    dataset_ids TEXT NOT NULL DEFAULT '[]',
    mode TEXT NOT NULL DEFAULT 'auto'
);
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    created_at REAL NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id, created_at);
"""


def new_id() -> str:
    return uuid.uuid4().hex[:12]


class Store:
    def __init__(self, db_path: Path):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._frames: OrderedDict[str, pd.DataFrame] = OrderedDict()

    def _exec(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            rows = cur.fetchall()
            self._conn.commit()
            return rows

    # -- datasets ---------------------------------------------------------

    def add_dataset(self, name: str, path: Path, sheet: str | None, profile: dict,
                    semantics: dict, frame: pd.DataFrame) -> dict:
        ds_id = new_id()
        self._exec(
            "INSERT INTO datasets (id, name, path, sheet, created_at, profile, semantics) VALUES (?,?,?,?,?,?,?)",
            (ds_id, name, str(path), sheet, time.time(), json.dumps(profile), json.dumps(semantics)),
        )
        self._cache(ds_id, frame)
        return self.get_dataset(ds_id)

    def set_insights(self, ds_id: str, insights: dict) -> None:
        self._exec("UPDATE datasets SET insights = ? WHERE id = ?", (json.dumps(insights), ds_id))

    def list_datasets(self) -> list[dict]:
        return [self._ds(r) for r in self._exec("SELECT * FROM datasets ORDER BY created_at DESC")]

    def get_dataset(self, ds_id: str) -> dict | None:
        rows = self._exec("SELECT * FROM datasets WHERE id = ?", (ds_id,))
        return self._ds(rows[0]) if rows else None

    def delete_dataset(self, ds_id: str) -> None:
        ds = self.get_dataset(ds_id)
        if not ds:
            return
        self._exec("DELETE FROM datasets WHERE id = ?", (ds_id,))
        self._frames.pop(ds_id, None)
        for chat in self.list_chats():
            if ds_id in chat["dataset_ids"]:
                self.update_chat(chat["id"], dataset_ids=[d for d in chat["dataset_ids"] if d != ds_id])
        still_used = self._exec("SELECT 1 FROM datasets WHERE path = ?", (ds["path"],))
        if not still_used:
            Path(ds["path"]).unlink(missing_ok=True)

    def frame(self, ds_id: str) -> pd.DataFrame:
        if ds_id in self._frames:
            self._frames.move_to_end(ds_id)
            return self._frames[ds_id]
        ds = self.get_dataset(ds_id)
        if not ds:
            raise KeyError(ds_id)
        for name, df in read_file(Path(ds["path"]), display_name=Path(ds["path"]).name):
            if ds["sheet"] is None or name.endswith(f"› {ds['sheet']}"):
                self._cache(ds_id, df)
                return df
        raise KeyError(f"Sheet {ds['sheet']} not found")

    def _cache(self, ds_id: str, df: pd.DataFrame) -> None:
        self._frames[ds_id] = df
        self._frames.move_to_end(ds_id)
        while len(self._frames) > 16:
            self._frames.popitem(last=False)

    @staticmethod
    def _ds(r: sqlite3.Row) -> dict:
        profile = json.loads(r["profile"])
        return {
            "id": r["id"], "name": r["name"], "path": r["path"], "sheet": r["sheet"],
            "created_at": r["created_at"], "rows": profile["rows"], "cols": profile["cols"],
            "profile": profile, "semantics": json.loads(r["semantics"]),
            "insights": json.loads(r["insights"]) if r["insights"] else None,
        }

    # -- chats ------------------------------------------------------------

    def create_chat(self, title: str = "New analysis", dataset_ids: list[str] | None = None) -> dict:
        chat_id, now = new_id(), time.time()
        self._exec(
            "INSERT INTO chats (id, title, created_at, updated_at, dataset_ids) VALUES (?,?,?,?,?)",
            (chat_id, title, now, now, json.dumps(dataset_ids or [])),
        )
        return self.get_chat(chat_id)

    def list_chats(self) -> list[dict]:
        return [self._chat(r) for r in self._exec("SELECT * FROM chats ORDER BY updated_at DESC")]

    def get_chat(self, chat_id: str) -> dict | None:
        rows = self._exec("SELECT * FROM chats WHERE id = ?", (chat_id,))
        return self._chat(rows[0]) if rows else None

    def update_chat(self, chat_id: str, *, title: str | None = None, dataset_ids: list[str] | None = None,
                    mode: str | None = None, touch: bool = True) -> dict | None:
        sets, params = [], []
        if title is not None:
            sets.append("title = ?"); params.append(title)
        if dataset_ids is not None:
            sets.append("dataset_ids = ?"); params.append(json.dumps(dataset_ids))
        if mode is not None:
            sets.append("mode = ?"); params.append(mode)
        if touch:
            sets.append("updated_at = ?"); params.append(time.time())
        if sets:
            self._exec(f"UPDATE chats SET {', '.join(sets)} WHERE id = ?", (*params, chat_id))
        return self.get_chat(chat_id)

    def delete_chat(self, chat_id: str) -> None:
        self._exec("DELETE FROM chats WHERE id = ?", (chat_id,))

    @staticmethod
    def _chat(r: sqlite3.Row) -> dict:
        return {
            "id": r["id"], "title": r["title"], "created_at": r["created_at"],
            "updated_at": r["updated_at"], "dataset_ids": json.loads(r["dataset_ids"]), "mode": r["mode"],
        }

    # -- messages ---------------------------------------------------------

    def add_message(self, chat_id: str, role: str, payload: dict) -> dict:
        msg_id, now = new_id(), time.time()
        self._exec(
            "INSERT INTO messages (id, chat_id, role, created_at, payload) VALUES (?,?,?,?,?)",
            (msg_id, chat_id, role, now, json.dumps(payload, default=str)),
        )
        self.update_chat(chat_id)
        return {"id": msg_id, "chat_id": chat_id, "role": role, "created_at": now, **payload}

    def list_messages(self, chat_id: str) -> list[dict]:
        rows = self._exec("SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at", (chat_id,))
        return [{"id": r["id"], "chat_id": r["chat_id"], "role": r["role"], "created_at": r["created_at"],
                 **json.loads(r["payload"])} for r in rows]


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store(config.DB_PATH)
    return _store


def set_store(store: Store) -> None:
    global _store
    _store = store
