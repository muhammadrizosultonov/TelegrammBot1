from __future__ import annotations

from app.config import Settings
from app.db import Database


async def is_admin_user(user_id: int, settings: Settings, db: Database) -> bool:
    if user_id in settings.admins:
        return True
    return await db.is_admin(user_id)
