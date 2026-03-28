from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.db import ChannelItem


def _trim_label(value: str, limit: int = 24) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1]}…"


def subscription_keyboard(channels: list[ChannelItem]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for index, channel in enumerate(channels, start=1):
        if channel.username:
            username = channel.username.lstrip("@")
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"✨ {index}. @{_trim_label(username)}",
                        url=f"https://t.me/{username}",
                    )
                ]
            )
        elif channel.invite_link:
            title = channel.title or "Kanal"
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"🔗 {index}. {_trim_label(title)}",
                        url=channel.invite_link,
                    )
                ]
            )

    rows.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
