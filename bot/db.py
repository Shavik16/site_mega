"""Слой доступа к SQLite: ученики, лекции, брони."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import aiosqlite

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    full_name  TEXT NOT NULL,
    grade      TEXT NOT NULL,
    username   TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lectures (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT    NOT NULL,
    description   TEXT,
    speaker       TEXT,
    place         TEXT,
    starts_at     TEXT    NOT NULL,
    capacity      INTEGER NOT NULL,
    photo_file_id TEXT,
    created_by    INTEGER NOT NULL,
    is_cancelled  INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bookings (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    lecture_id INTEGER NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (lecture_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_lectures_starts_at ON lectures(starts_at);
CREATE INDEX IF NOT EXISTS idx_bookings_lecture ON bookings(lecture_id);
"""

# Поля лекции, которые разрешено править из админки.
EDITABLE_FIELDS = ("title", "description", "speaker", "place", "starts_at", "capacity", "photo_file_id")


class Database:
    """Одно соединение на весь процесс — бот однопоточный, этого достаточно."""

    def __init__(self, path: Path | str) -> None:
        self._path = str(path)
        self._conn: aiosqlite.Connection | None = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("База не подключена: сначала await db.connect()")
        return self._conn

    async def connect(self) -> None:
        # isolation_level=None — управляем транзакциями явно (см. book()).
        self._conn = await aiosqlite.connect(self._path, isolation_level=None)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    # ---------------------------------------------------------------- ученики

    async def get_user(self, user_id: int) -> aiosqlite.Row | None:
        async with self.conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            return await cur.fetchone()

    async def save_user(self, user_id: int, full_name: str, grade: str, username: str | None) -> None:
        await self.conn.execute(
            """
            INSERT INTO users (user_id, full_name, grade, username)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                full_name = excluded.full_name,
                grade     = excluded.grade,
                username  = excluded.username
            """,
            (user_id, full_name, grade, username),
        )
        await self.conn.commit()

    async def all_user_ids(self) -> list[int]:
        async with self.conn.execute("SELECT user_id FROM users") as cur:
            return [row["user_id"] for row in await cur.fetchall()]

    async def users_count(self) -> int:
        async with self.conn.execute("SELECT COUNT(*) AS n FROM users") as cur:
            return (await cur.fetchone())["n"]

    # ---------------------------------------------------------------- лекции

    async def create_lecture(
        self,
        *,
        title: str,
        description: str | None,
        speaker: str | None,
        place: str | None,
        starts_at: str,
        capacity: int,
        photo_file_id: str | None,
        created_by: int,
    ) -> int:
        cur = await self.conn.execute(
            """
            INSERT INTO lectures
                (title, description, speaker, place, starts_at, capacity, photo_file_id, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, description, speaker, place, starts_at, capacity, photo_file_id, created_by),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def get_lecture(self, lecture_id: int) -> aiosqlite.Row | None:
        async with self.conn.execute(
            """
            SELECT l.*, (SELECT COUNT(*) FROM bookings b WHERE b.lecture_id = l.id) AS booked
            FROM lectures l WHERE l.id = ?
            """,
            (lecture_id,),
        ) as cur:
            return await cur.fetchone()

    async def list_lectures(
        self, *, only_upcoming: bool = True, include_cancelled: bool = False, limit: int = 50
    ) -> list[aiosqlite.Row]:
        where = []
        params: list = []
        if only_upcoming:
            where.append("l.starts_at >= ?")
            params.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        if not include_cancelled:
            where.append("l.is_cancelled = 0")
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        params.append(limit)
        async with self.conn.execute(
            f"""
            SELECT l.*, (SELECT COUNT(*) FROM bookings b WHERE b.lecture_id = l.id) AS booked
            FROM lectures l {clause}
            ORDER BY l.starts_at
            LIMIT ?
            """,
            params,
        ) as cur:
            return list(await cur.fetchall())

    async def update_lecture(self, lecture_id: int, field: str, value) -> None:
        if field not in EDITABLE_FIELDS:
            raise ValueError(f"Поле {field!r} нельзя редактировать")
        await self.conn.execute(
            f"UPDATE lectures SET {field} = ? WHERE id = ?", (value, lecture_id)
        )
        await self.conn.commit()

    async def set_cancelled(self, lecture_id: int, cancelled: bool) -> None:
        await self.conn.execute(
            "UPDATE lectures SET is_cancelled = ? WHERE id = ?", (int(cancelled), lecture_id)
        )
        await self.conn.commit()

    async def delete_lecture(self, lecture_id: int) -> None:
        await self.conn.execute("DELETE FROM lectures WHERE id = ?", (lecture_id,))
        await self.conn.commit()

    # ---------------------------------------------------------------- брони

    async def is_booked(self, lecture_id: int, user_id: int) -> bool:
        async with self.conn.execute(
            "SELECT 1 FROM bookings WHERE lecture_id = ? AND user_id = ?", (lecture_id, user_id)
        ) as cur:
            return await cur.fetchone() is not None

    async def book(self, lecture_id: int, user_id: int) -> str:
        """Пытается забронировать место.

        Возвращает: 'ok' | 'already' | 'full' | 'cancelled' | 'past' | 'missing'.
        """
        await self.conn.execute("BEGIN IMMEDIATE")
        try:
            async with self.conn.execute(
                """
                SELECT l.capacity, l.is_cancelled, l.starts_at,
                       (SELECT COUNT(*) FROM bookings b WHERE b.lecture_id = l.id) AS booked,
                       (SELECT COUNT(*) FROM bookings b WHERE b.lecture_id = l.id AND b.user_id = ?) AS mine
                FROM lectures l WHERE l.id = ?
                """,
                (user_id, lecture_id),
            ) as cur:
                row = await cur.fetchone()

            if row is None:
                return "missing"
            if row["mine"]:
                return "already"
            if row["is_cancelled"]:
                return "cancelled"
            if row["starts_at"] < datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
                return "past"
            if row["booked"] >= row["capacity"]:
                return "full"

            await self.conn.execute(
                "INSERT INTO bookings (lecture_id, user_id) VALUES (?, ?)", (lecture_id, user_id)
            )
            return "ok"
        finally:
            await self.conn.commit()

    async def unbook(self, lecture_id: int, user_id: int) -> bool:
        cur = await self.conn.execute(
            "DELETE FROM bookings WHERE lecture_id = ? AND user_id = ?", (lecture_id, user_id)
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def lecture_bookings(self, lecture_id: int) -> list[aiosqlite.Row]:
        async with self.conn.execute(
            """
            SELECT u.full_name, u.grade, u.username, u.user_id, b.created_at
            FROM bookings b JOIN users u ON u.user_id = b.user_id
            WHERE b.lecture_id = ?
            ORDER BY u.grade, u.full_name
            """,
            (lecture_id,),
        ) as cur:
            return list(await cur.fetchall())

    async def booked_user_ids(self, lecture_id: int) -> list[int]:
        async with self.conn.execute(
            "SELECT user_id FROM bookings WHERE lecture_id = ?", (lecture_id,)
        ) as cur:
            return [row["user_id"] for row in await cur.fetchall()]

    async def user_bookings(self, user_id: int) -> list[aiosqlite.Row]:
        async with self.conn.execute(
            """
            SELECT l.*, (SELECT COUNT(*) FROM bookings b2 WHERE b2.lecture_id = l.id) AS booked
            FROM bookings b JOIN lectures l ON l.id = b.lecture_id
            WHERE b.user_id = ? AND l.starts_at >= ?
            ORDER BY l.starts_at
            """,
            (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ) as cur:
            return list(await cur.fetchall())
