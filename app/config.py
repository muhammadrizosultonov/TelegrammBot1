from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(slots=True)
class Settings:
    bot_token: str
    admins: set[int]
    db_path: str
    rate_limit_seconds: float


def _resolve_db_path(raw_path: str) -> str:
    path = Path(raw_path or "bot.db").expanduser()
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path)



def _parse_admins(raw: str) -> set[int]:
    admins: set[int] = set()
    for item in raw.split(","):
        value = item.strip()
        if not value:
            continue
        if value.isdigit():
            admins.add(int(value))
    return admins



def get_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    admins_raw = os.getenv("ADMINS", "")
    db_path = _resolve_db_path(os.getenv("DB_PATH", "bot.db").strip())
    rate_limit_seconds = float(os.getenv("RATE_LIMIT_SECONDS", "2"))

    if not token:
        raise ValueError("BOT_TOKEN topilmadi. .env faylni tekshiring.")

    return Settings(
        bot_token=token,
        admins=_parse_admins(admins_raw),
        db_path=db_path,
        rate_limit_seconds=rate_limit_seconds,
    )
