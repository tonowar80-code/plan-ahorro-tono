"""Memoria local del bot: personas autorizadas, solicitudes, carpetas de Drive y trabajos."""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    user_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    added_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS requests (
    user_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    asked_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS folders (
    user_id INTEGER PRIMARY KEY,
    folder_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    chat_id INTEGER NOT NULL,
    received_at TEXT NOT NULL,
    audio_path TEXT NOT NULL,
    mime TEXT NOT NULL,
    transcript TEXT,
    doc_link TEXT,
    drive_done INTEGER NOT NULL DEFAULT 0,
    mail_done INTEGER NOT NULL DEFAULT 0
);
"""


@dataclass(frozen=True)
class _Result:
    rows: list[tuple]
    rowcount: int
    lastrowid: int | None

    def fetchone(self) -> tuple | None:
        return self.rows[0] if self.rows else None

    def fetchall(self) -> list[tuple]:
        return self.rows


@dataclass(frozen=True)
class Job:
    id: int
    user_id: int
    name: str
    chat_id: int
    received_at: datetime
    audio_path: Path
    mime: str
    transcript: str | None
    doc_link: str | None
    drive_done: bool
    mail_done: bool


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        # El bot usa la base de datos desde varios hilos: un candado evita que se pisen.
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.executescript(SCHEMA)

    def _run(self, sql: str, params: tuple = ()) -> _Result:
        with self._lock, self._db:
            cursor = self._db.execute(sql, params)
            return _Result(cursor.fetchall(), cursor.rowcount, cursor.lastrowid)

    # Personas autorizadas
    def add_person(self, user_id: int, name: str) -> None:
        self._run(
            "INSERT OR REPLACE INTO people VALUES (?, ?, ?)",
            (user_id, name, datetime.now().isoformat()),
        )

    def remove_person(self, user_id: int) -> bool:
        return self._run("DELETE FROM people WHERE user_id = ?", (user_id,)).rowcount > 0

    def is_person(self, user_id: int) -> bool:
        row = self._run("SELECT 1 FROM people WHERE user_id = ?", (user_id,)).fetchone()
        return row is not None

    def list_people(self) -> list[tuple[int, str]]:
        return self._run("SELECT user_id, name FROM people ORDER BY name").fetchall()

    # Solicitudes de acceso (solo el último nombre visto)
    def remember_request(self, user_id: int, name: str) -> None:
        self._run(
            "INSERT OR REPLACE INTO requests VALUES (?, ?, ?)",
            (user_id, name, datetime.now().isoformat()),
        )

    def requested_name(self, user_id: int) -> str | None:
        row = self._run("SELECT name FROM requests WHERE user_id = ?", (user_id,)).fetchone()
        return row[0] if row else None

    # Carpetas de Drive por persona
    def folder_for(self, user_id: int) -> str | None:
        row = self._run("SELECT folder_id FROM folders WHERE user_id = ?", (user_id,)).fetchone()
        return row[0] if row else None

    def set_folder(self, user_id: int, folder_id: str) -> None:
        self._run("INSERT OR REPLACE INTO folders VALUES (?, ?)", (user_id, folder_id))

    # Trabajos (uno por nota de voz)
    def create_job(
        self,
        user_id: int,
        name: str,
        chat_id: int,
        received_at: datetime,
        audio_path: Path,
        mime: str,
    ) -> int:
        cursor = self._run(
            "INSERT INTO jobs (user_id, name, chat_id, received_at, audio_path, mime)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, name, chat_id, received_at.isoformat(), str(audio_path), mime),
        )
        return cursor.lastrowid

    def get_job(self, job_id: int) -> Job | None:
        row = self._run(
            "SELECT id, user_id, name, chat_id, received_at, audio_path, mime, transcript,"
            " doc_link, drive_done, mail_done FROM jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        return Job(
            id=row[0],
            user_id=row[1],
            name=row[2],
            chat_id=row[3],
            received_at=datetime.fromisoformat(row[4]),
            audio_path=Path(row[5]),
            mime=row[6],
            transcript=row[7],
            doc_link=row[8],
            drive_done=bool(row[9]),
            mail_done=bool(row[10]),
        )

    def set_transcript(self, job_id: int, text: str) -> None:
        self._run("UPDATE jobs SET transcript = ? WHERE id = ?", (text, job_id))

    def mark_drive_done(self, job_id: int, doc_link: str) -> None:
        self._run("UPDATE jobs SET drive_done = 1, doc_link = ? WHERE id = ?", (doc_link, job_id))

    def mark_mail_done(self, job_id: int) -> None:
        self._run("UPDATE jobs SET mail_done = 1 WHERE id = ?", (job_id,))

    def delete_job(self, job_id: int) -> None:
        self._run("DELETE FROM jobs WHERE id = ?", (job_id,))

    def unfinished_jobs(self) -> list[int]:
        rows = self._run("SELECT id FROM jobs WHERE transcript IS NULL ORDER BY id").fetchall()
        return [r[0] for r in rows]

    def pending_deliveries(self) -> list[int]:
        rows = self._run(
            "SELECT id FROM jobs WHERE transcript IS NOT NULL"
            " AND (drive_done = 0 OR mail_done = 0) ORDER BY id"
        ).fetchall()
        return [r[0] for r in rows]
