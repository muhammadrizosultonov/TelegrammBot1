from __future__ import annotations

import logging
import re

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from app.config import Settings
from app.db import Database
from app.keyboards.inline import subscription_keyboard
from app.keyboards.reply import ADMIN_PANEL_TEXTS, admin_main_keyboard
from app.services.content import send_content_by_record
from app.services.admins import is_admin_user
from app.services.subscription import build_subscription_message, check_user_subscriptions
from app.texts import DEFAULT_TEXTS, TEXT_PARSE_MODE


logger = logging.getLogger(__name__)
router = Router(name="user")
CODE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ADMIN_START_TEXT = (
    "🛠 <b>Admin panel tayyor</b>\n\n"
    "Kerakli bo'limni tanlang va bot boshqaruvini shu yerdan davom ettiring."
)


def _is_forwarded_channel_message(message: Message) -> bool:
    if message.forward_from_chat and message.forward_from_chat.type == "channel":
        return True
    if message.sender_chat and message.sender_chat.type == "channel":
        return True
    forward_origin = getattr(message, "forward_origin", None)
    origin_chat = getattr(forward_origin, "chat", None)
    return bool(origin_chat and getattr(origin_chat, "type", None) == "channel")


@router.message(CommandStart())
async def start_handler(message: Message, db: Database, settings: Settings) -> None:
    if message.from_user:
        await db.touch_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )
        if await is_admin_user(message.from_user.id, settings, db):
            await message.answer(
                ADMIN_START_TEXT,
                parse_mode="HTML",
                reply_markup=admin_main_keyboard(),
            )
            return

    text = await _get_text(db, "start")
    await message.answer(text, parse_mode=TEXT_PARSE_MODE.get("start"))


async def _get_text(db: Database, key: str) -> str:
    value = await db.get_text(key)
    if value is not None:
        return value
    return DEFAULT_TEXTS[key]


@router.message(F.text & ~F.text.startswith("/"))
async def code_handler(message: Message, bot: Bot, db: Database, settings: Settings) -> None:
    if not message.from_user:
        return
    await db.touch_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    if _is_forwarded_channel_message(message):
        # Kanal postlari admin tarafdagi kanal qo'shish oqimi uchun ishlatiladi.
        return
    if message.text and await is_admin_user(message.from_user.id, settings, db):
        if message.text.strip() in ADMIN_PANEL_TEXTS:
            return

    code = (message.text or "").strip()
    if not code:
        return
    if not CODE_RE.fullmatch(code):
        text = await _get_text(db, "invalid_code")
        await message.answer(text, parse_mode=TEXT_PARSE_MODE.get("invalid_code"))
        return

    check = await check_user_subscriptions(bot=bot, db=db, user_id=message.from_user.id)
    if not check.is_subscribed:
        template = await _get_text(db, "subscription_template")
        channels_for_keyboard = check.missing_channels + check.inaccessible_channels
        await message.answer(
            build_subscription_message(
                check.missing_channels,
                inaccessible_channels=check.inaccessible_channels,
                template=template,
            ),
            reply_markup=subscription_keyboard(channels_for_keyboard),
        )
        return

    content = await db.get_content(code)
    if not content:
        text = await _get_text(db, "code_not_found")
        await message.answer(text, parse_mode=TEXT_PARSE_MODE.get("code_not_found"))
        return

    sent = await send_content_by_record(message, content)
    if sent:
        logger.info("Kontent yuborildi | user_id=%s code=%s", message.from_user.id, code)


@router.callback_query(F.data == "check_sub")
async def recheck_subscription(callback: CallbackQuery, bot: Bot, db: Database) -> None:
    if not callback.from_user:
        await callback.answer()
        return
    # Callback query javobi qaytmasa Telegram UI'da "aylanib turish" davom etadi.
    # Shuning uchun tekshiruvdan oldin javob berib yuboramiz.
    try:
        await callback.answer("🔄 Tekshirilmoqda...")
    except TelegramBadRequest:
        # Callback "eskirgan" bo'lishi mumkin. Bu holatda ham tekshiruvni davom ettiramiz.
        pass

    await db.touch_user(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        full_name=callback.from_user.full_name,
    )

    check = await check_user_subscriptions(bot=bot, db=db, user_id=callback.from_user.id)
    if not check.is_subscribed:
        if not callback.message:
            await bot.send_message(callback.from_user.id, "Obuna oynasi topilmadi.")
            return
        template = await _get_text(db, "subscription_template")
        text = build_subscription_message(
            check.missing_channels,
            inaccessible_channels=check.inaccessible_channels,
            template=template,
        )
        channels_for_keyboard = check.missing_channels + check.inaccessible_channels
        markup = subscription_keyboard(channels_for_keyboard)
        try:
            await callback.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest as exc:
            # Text/markup o'zgarmagan bo'lsa Telegram "message is not modified" qaytaradi.
            # Bu tekshiruvni to'xtatmasligi kerak.
            if "message is not modified" not in str(exc):
                await callback.message.answer(
                    "⚠️ Obuna oynasini yangilab bo'lmadi. Bir ozdan so'ng qayta urinib ko'ring."
                )
        return

    text = "🎉 Ajoyib, obuna tasdiqlandi!\n\nEndi kodni qayta yuboring va kontentni oling."
    if callback.message:
        await callback.message.answer(text)
    else:
        await bot.send_message(callback.from_user.id, text)
