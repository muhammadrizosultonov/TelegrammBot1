from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message

from app.db import ContentItem


async def send_content_by_record(message: Message, content: ContentItem) -> bool:
    try:
        if content.file_type == "video":
            await message.answer_video(video=content.file_id, caption=content.caption)
            return True

        if content.file_type == "document":
            await message.answer_document(document=content.file_id, caption=content.caption)
            return True

        await message.answer("⚠️ Saqlangan kontent turi qo'llab-quvvatlanmaydi.")
        return False
    except (TelegramBadRequest, TelegramForbiddenError):
        await message.answer(
            "🚫 Kontentni yuborib bo'lmadi. Bot ruxsatlari yoki fayl holatini tekshirib ko'ring."
        )
        return False
