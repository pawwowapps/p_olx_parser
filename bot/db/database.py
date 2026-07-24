from __future__ import annotations

from pathlib import Path
from typing import Optional

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    label TEXT NOT NULL,
    url TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(chat_id, url)
);

CREATE TABLE IF NOT EXISTS seen_ads (
    subscription_id INTEGER NOT NULL,
    ad_id TEXT NOT NULL,
    PRIMARY KEY (subscription_id, ad_id),
    FOREIGN KEY (subscription_id) REFERENCES subscriptions (id) ON DELETE CASCADE
);
"""


class Database:
    def __init__(self, db_path: str):
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def init(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.executescript(SCHEMA)
            await db.commit()

    async def add_subscription(self, chat_id: int, label: str, url: str) -> Optional[int]:
        async with aiosqlite.connect(self._db_path) as db:
            try:
                cursor = await db.execute(
                    "INSERT INTO subscriptions (chat_id, label, url) VALUES (?, ?, ?)",
                    (chat_id, label, url),
                )
                await db.commit()
                return cursor.lastrowid
            except aiosqlite.IntegrityError:
                return None

    async def remove_subscription(self, chat_id: int, subscription_id: int) -> bool:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "DELETE FROM subscriptions WHERE id = ? AND chat_id = ?",
                (subscription_id, chat_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def list_subscriptions(self, chat_id: int) -> list[aiosqlite.Row]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, label, url FROM subscriptions WHERE chat_id = ? ORDER BY id",
                (chat_id,),
            )
            return list(await cursor.fetchall())

    async def all_subscriptions(self) -> list[aiosqlite.Row]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id, chat_id, label, url FROM subscriptions")
            return list(await cursor.fetchall())

    async def get_seen_ad_ids(self, subscription_id: int) -> set[str]:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT ad_id FROM seen_ads WHERE subscription_id = ?",
                (subscription_id,),
            )
            rows = await cursor.fetchall()
            return {row[0] for row in rows}

    async def mark_ads_seen(self, subscription_id: int, ad_ids: list[str]) -> None:
        if not ad_ids:
            return
        async with aiosqlite.connect(self._db_path) as db:
            await db.executemany(
                "INSERT OR IGNORE INTO seen_ads (subscription_id, ad_id) VALUES (?, ?)",
                [(subscription_id, ad_id) for ad_id in ad_ids],
            )
            await db.commit()
