from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import aiosqlite


@dataclass(slots=True)
class ContentItem:
    code: str
    file_id: str
    file_type: str
    caption: str | None


@dataclass(slots=True)
class ContentListItem:
    code: str
    file_type: str
    caption: str | None
    created_at: str


@dataclass(slots=True)
class ChannelItem:
    chat_id: int
    title: str | None
    username: str | None
    invite_link: str | None


@dataclass(slots=True)
class AdminItem:
    user_id: int
    username: str | None
    full_name: str | None


@dataclass(slots=True)
class UserItem:
    user_id: int
    username: str | None
    full_name: str | None


class Database:
    def __init__(self, path: str) -> None:
        self.path = path

    def _ensure_parent_dir(self) -> None:
        if self.path == ":memory:":
            return
        Path(self.path).expanduser().parent.mkdir(parents=True, exist_ok=True)

    async def _apply_pragmas(self, db: aiosqlite.Connection) -> None:
        # SQLite uchun productionga yaqin xavfsiz/performance balans.
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.execute("PRAGMA busy_timeout=5000;")

    async def _ensure_column(
        self,
        db: aiosqlite.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(f"PRAGMA table_info({table})")
        rows = await cursor.fetchall()
        columns = {row["name"] for row in rows}
        if column not in columns:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    async def init(self) -> None:
        self._ensure_parent_dir()
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS contents (
                    code TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    file_type TEXT NOT NULL CHECK(file_type IN ('video', 'document')),
                    caption TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS channels (
                    chat_id INTEGER PRIMARY KEY,
                    title TEXT,
                    username TEXT,
                    invite_link TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    first_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS texts (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS join_requests (
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (chat_id, user_id)
                )
                """
            )
            await self._ensure_column(db, "channels", "invite_link", "TEXT")
            await self._ensure_column(db, "users", "pending_code", "TEXT")
            await db.commit()

    async def upsert_content(
        self, code: str, file_id: str, file_type: str, caption: str | None
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            await db.execute(
                """
                INSERT INTO contents (code, file_id, file_type, caption)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    file_id=excluded.file_id,
                    file_type=excluded.file_type,
                    caption=excluded.caption
                """,
                (code, file_id, file_type, caption),
            )
            await db.commit()

    async def delete_content(self, code: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            cursor = await db.execute("DELETE FROM contents WHERE code = ?", (code,))
            await db.commit()
            return cursor.rowcount > 0

    async def get_content(self, code: str) -> ContentItem | None:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT code, file_id, file_type, caption FROM contents WHERE code = ?",
                (code,),
            )
            row = await cursor.fetchone()

        if row is None:
            return None

        return ContentItem(
            code=row["code"],
            file_id=row["file_id"],
            file_type=row["file_type"],
            caption=row["caption"],
        )

    async def add_channel(
        self,
        chat_id: int,
        title: str | None,
        username: str | None,
        invite_link: str | None = None,
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            await db.execute(
                """
                INSERT INTO channels (chat_id, title, username, invite_link)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    title=excluded.title,
                    username=excluded.username,
                    invite_link=excluded.invite_link
                """,
                (chat_id, title, username, invite_link),
            )
            await db.commit()

    async def remove_channel(self, chat_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            cursor = await db.execute("DELETE FROM channels WHERE chat_id = ?", (chat_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def list_channels(self) -> list[ChannelItem]:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT chat_id, title, username, invite_link FROM channels ORDER BY created_at ASC"
            )
            rows = await cursor.fetchall()

        return [
            ChannelItem(
                chat_id=row["chat_id"],
                title=row["title"],
                username=row["username"],
                invite_link=row["invite_link"],
            )
            for row in rows
        ]

    async def has_channel(self, chat_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            cursor = await db.execute("SELECT 1 FROM channels WHERE chat_id = ? LIMIT 1", (chat_id,))
            row = await cursor.fetchone()
        return row is not None

    async def upsert_join_request(self, chat_id: int, user_id: int, requested_at: str | None = None) -> None:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            await db.execute(
                """
                INSERT INTO join_requests (chat_id, user_id, requested_at)
                VALUES (?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                ON CONFLICT(chat_id, user_id) DO UPDATE SET
                    requested_at=excluded.requested_at
                """,
                (chat_id, user_id, requested_at),
            )
            await db.commit()

    async def list_join_request_chat_ids(self, user_id: int) -> set[int]:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            cursor = await db.execute("SELECT chat_id FROM join_requests WHERE user_id = ?", (user_id,))
            rows = await cursor.fetchall()
        return {int(row[0]) for row in rows}

    async def touch_user(self, user_id: int, username: str | None, full_name: str | None) -> None:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            await db.execute(
                """
                INSERT INTO users (user_id, username, full_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    full_name=excluded.full_name,
                    last_seen=CURRENT_TIMESTAMP
                """,
                (user_id, username, full_name),
            )
            await db.commit()

    async def set_pending_code(self, user_id: int, code: str | None) -> None:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            await db.execute(
                """
                INSERT INTO users (user_id, pending_code)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    pending_code=excluded.pending_code,
                    last_seen=CURRENT_TIMESTAMP
                """,
                (user_id, code),
            )
            await db.commit()

    async def get_pending_code(self, user_id: int) -> str | None:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            cursor = await db.execute("SELECT pending_code FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
        if not row:
            return None
        value = row[0]
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    async def list_user_ids(self) -> list[int]:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            cursor = await db.execute("SELECT user_id FROM users")
            rows = await cursor.fetchall()
        return [row[0] for row in rows]

    async def count_users(self) -> int:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def get_user(self, user_id: int) -> UserItem | None:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT user_id, username, full_name FROM users WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()

        if row is None:
            return None

        return UserItem(
            user_id=row["user_id"],
            username=row["username"],
            full_name=row["full_name"],
        )

    async def count_active_users(self, hours: int = 24) -> int:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            cursor = await db.execute(
                "SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now', ?)",
                (f"-{hours} hours",),
            )
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def count_contents(self) -> int:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            cursor = await db.execute("SELECT COUNT(*) FROM contents")
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def count_contents_by_type(self, file_type: str) -> int:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            cursor = await db.execute(
                "SELECT COUNT(*) FROM contents WHERE file_type = ?",
                (file_type,),
            )
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def count_channels(self) -> int:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            cursor = await db.execute("SELECT COUNT(*) FROM channels")
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def count_public_channels(self) -> int:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            cursor = await db.execute(
                "SELECT COUNT(*) FROM channels WHERE username IS NOT NULL AND username != ''"
            )
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def count_private_channels(self) -> int:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            cursor = await db.execute(
                "SELECT COUNT(*) FROM channels WHERE username IS NULL OR username = ''"
            )
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def list_contents(self, limit: int = 20) -> list[ContentListItem]:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT code, file_type, caption, created_at
                FROM contents
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()

        return [
            ContentListItem(
                code=row["code"],
                file_type=row["file_type"],
                caption=row["caption"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def add_admin(
        self,
        user_id: int,
        username: str | None,
        full_name: str | None,
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            await db.execute(
                """
                INSERT INTO admins (user_id, username, full_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    full_name=excluded.full_name
                """,
                (user_id, username, full_name),
            )
            await db.commit()

    async def remove_admin(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            cursor = await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def list_admins(self) -> list[AdminItem]:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT user_id, username, full_name FROM admins ORDER BY created_at DESC"
            )
            rows = await cursor.fetchall()

        return [
            AdminItem(
                user_id=row["user_id"],
                username=row["username"],
                full_name=row["full_name"],
            )
            for row in rows
        ]

    async def is_admin(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            cursor = await db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
        return row is not None

    async def set_text(self, key: str, value: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            await db.execute(
                """
                INSERT INTO texts (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (key, value),
            )
            await db.commit()

    async def get_text(self, key: str) -> str | None:
        async with aiosqlite.connect(self.path) as db:
            await self._apply_pragmas(db)
            cursor = await db.execute("SELECT value FROM texts WHERE key = ?", (key,))
            row = await cursor.fetchone()
        return str(row[0]) if row else None
