from __future__ import annotations

from dataclasses import dataclass
import logging

from aiogram import Bot
from aiogram.enums.chat_member_status import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.db import ChannelItem, Database

logger = logging.getLogger(__name__)

ALLOWED_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
    # Guruhlarda foydalanuvchi "restricted" bo'lsa ham a'zo hisoblanadi.
    # (Ko'pincha yangi a'zolar vaqtincha yozishdan cheklanadi.)
    ChatMemberStatus.RESTRICTED,
}


@dataclass(slots=True)
class SubscriptionCheckResult:
    is_subscribed: bool
    missing_channels: list[ChannelItem]


async def check_user_subscriptions(
    bot: Bot,
    db: Database,
    user_id: int,
) -> SubscriptionCheckResult:
    channels = await db.list_channels()
    if not channels:
        return SubscriptionCheckResult(is_subscribed=True, missing_channels=[])

    missing: list[ChannelItem] = []

    for channel in channels:
        try:
            member = await bot.get_chat_member(chat_id=channel.chat_id, user_id=user_id)
            if member.status not in ALLOWED_STATUSES:
                missing.append(channel)
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            # Chatga kira olmaslik holatida xavfsizlik uchun o'tkazmaymiz
            logger.warning(
                "get_chat_member xatosi | chat_id=%s user_id=%s error=%s",
                channel.chat_id,
                user_id,
                exc,
            )
            missing.append(channel)

    return SubscriptionCheckResult(
        is_subscribed=len(missing) == 0,
        missing_channels=missing,
    )



def build_subscription_message(channels: list[ChannelItem], template: str | None = None) -> str:
    if not channels:
        return "✅ Obuna tekshiruvi muvaffaqiyatli."

    lines: list[str] = []

    for index, channel in enumerate(channels, start=1):
        if channel.username:
            lines.append(f"✨ {index}. @{channel.username.lstrip('@')}")
        else:
            title = channel.title or "Yopiq kanal"
            lines.append(f"🔒 {index}. {title} (private kanal)")
    channels_text = "\n".join(lines)

    if template:
        if "{channels}" in template:
            return template.replace("{channels}", channels_text)
        return f"{template}\n\n{channels_text}"

    return (
        "🔐 Kontentni ochish uchun quyidagi kanallarga qo'shiling:\n\n"
        f"{channels_text}\n\n"
        "✅ A'zo bo'lgach, pastdagi tugma orqali tekshirib ko'ring."
    )
