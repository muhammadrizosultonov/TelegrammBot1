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
    inaccessible_channels: list[ChannelItem]


async def check_user_subscriptions(
    bot: Bot,
    db: Database,
    user_id: int,
) -> SubscriptionCheckResult:
    channels = await db.list_channels()
    if not channels:
        return SubscriptionCheckResult(
            is_subscribed=True,
            missing_channels=[],
            inaccessible_channels=[],
        )

    missing: list[ChannelItem] = []
    inaccessible: list[ChannelItem] = []

    for channel in channels:
        try:
            member = await bot.get_chat_member(chat_id=channel.chat_id, user_id=user_id)
            if member.status not in ALLOWED_STATUSES:
                missing.append(channel)
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            # Bot chatga kira olmasa (ko'pincha bot admin emas / chat topilmaydi),
            # tekshiruvni ishonchli yakunlab bo'lmaydi.
            logger.warning(
                "get_chat_member xatosi | chat_id=%s user_id=%s error=%s",
                channel.chat_id,
                user_id,
                exc,
            )
            inaccessible.append(channel)

    return SubscriptionCheckResult(
        is_subscribed=len(missing) == 0 and len(inaccessible) == 0,
        missing_channels=missing,
        inaccessible_channels=inaccessible,
    )



def build_subscription_message(
    channels: list[ChannelItem],
    *,
    inaccessible_channels: list[ChannelItem] | None = None,
    template: str | None = None,
) -> str:
    inaccessible_channels = inaccessible_channels or []

    if not channels and not inaccessible_channels:
        return "✅ Obuna tekshiruvi muvaffaqiyatli."

    lines: list[str] = []

    for index, channel in enumerate(channels, start=1):
        if channel.username:
            lines.append(f"✨ {index}. @{channel.username.lstrip('@')}")
        else:
            title = channel.title or "Yopiq kanal"
            lines.append(f"🔒 {index}. {title} (private kanal)")
    channels_text = "\n".join(lines)

    inaccessible_text = ""
    if inaccessible_channels:
        warn_lines: list[str] = []
        for index, channel in enumerate(inaccessible_channels, start=1):
            if channel.username:
                warn_lines.append(f"⚠️ {index}. @{channel.username.lstrip('@')}")
            else:
                title = channel.title or "Yopiq kanal"
                warn_lines.append(f"⚠️ {index}. {title} (private kanal)")
        inaccessible_text = "\n".join(warn_lines)

    if inaccessible_text and not channels_text:
        return (
            "⚠️ Obuna tekshiruvini yakunlab bo'lmadi.\n\n"
            "Bot quyidagi kanal/guruhlarda admin emas (yoki ruxsat yetarli emas), "
            "shuning uchun obunani tekshirolmayapti:\n\n"
            f"{inaccessible_text}\n\n"
            "Admin botni shu chat(lar)ga admin qilib qo'ysin, keyin yana \"✅ Tekshirish\" ni bosing."
        )

    if template:
        if "{channels}" in template:
            text = template.replace("{channels}", channels_text)
        else:
            text = f"{template}\n\n{channels_text}"

        if inaccessible_text:
            text += (
                "\n\n"
                "⚠️ Eslatma: bot ayrim kanallar/guruhlarda admin emas (yoki ruxsat yetarli emas).\n"
                "Shu sabab obunani tekshirib bo'lmadi. Admin botni o'sha chatga admin qilib qo'ysin:\n\n"
                f"{inaccessible_text}"
            )
        return text

    return (
        "🔐 Kontentni ochish uchun quyidagi kanallarga qo'shiling:\n\n"
        f"{channels_text}\n\n"
        "✅ A'zo bo'lgach, pastdagi tugma orqali tekshirib ko'ring."
        + (
            (
                "\n\n"
                "⚠️ Obuna tekshiruvi muammosi: bot ayrim kanallar/guruhlarda admin emas.\n"
                "Admin botni o'sha chatga admin qilib qo'ysin:\n\n"
                f"{inaccessible_text}"
            )
            if inaccessible_text
            else ""
        )
    )
