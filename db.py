"""Phase 4-3: 상담 내역·아젠다를 SQLite에 저장한다. logs/conversations.jsonl(Phase 1~2)을 대체."""

import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "mentor_chat.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS agendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                sources TEXT NOT NULL,
                web_sources TEXT NOT NULL,
                route TEXT NOT NULL,
                agenda_id INTEGER
            )"""
        )


def create_agenda(title: str, description: str) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO agendas (title, description, created_at) VALUES (?, ?, ?)",
            (title, description, datetime.now(timezone.utc).isoformat()),
        )
        return cursor.lastrowid


def list_agendas() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM agendas ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]


def get_agenda(agenda_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM agendas WHERE id = ?", (agenda_id,)
        ).fetchone()
        return dict(row) if row else None


def save_conversation(
    question: str,
    answer: str,
    sources: list[str],
    web_sources: list[str],
    route: str,
    agenda_id: int | None = None,
    timestamp: str | None = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            """INSERT INTO conversations
               (timestamp, question, answer, sources, web_sources, route, agenda_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                timestamp or datetime.now(timezone.utc).isoformat(),
                question,
                answer,
                json.dumps(sources, ensure_ascii=False),
                json.dumps(web_sources, ensure_ascii=False),
                route,
                agenda_id,
            ),
        )


def list_conversations(agenda_id: int | None = None) -> list[dict]:
    with _connect() as conn:
        if agenda_id is None:
            rows = conn.execute("SELECT * FROM conversations ORDER BY id ASC").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE agenda_id = ? ORDER BY id ASC",
                (agenda_id,),
            ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["sources"] = json.loads(d["sources"])
            d["web_sources"] = json.loads(d["web_sources"])
            results.append(d)
        return results


init_db()
