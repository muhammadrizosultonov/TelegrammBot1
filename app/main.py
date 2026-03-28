from __future__ import annotations
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ErrorEvent
from app.config import Settings, get_settings
from app.db import Database
from app.handlers import admin, user
from app.middlewares.rate_limit import RateLimitMiddleware


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )


async def on_error(event: ErrorEvent) -> bool:
    logger = logging.getLogger("app.errors")
    update = event.update
    exception = event.exception
    update_id = getattr(update, "update_id", "unknown")

    if isinstance(exception, (TelegramBadRequest, TelegramForbiddenError)):
        logger.warning("Telegram xatosi | update_id=%s error=%s", update_id, exception)
        return True

    logger.exception("Kutilmagan xato | update_id=%s", update_id)
    return True


async def main() -> None:
    setup_logging()

    settings: Settings = get_settings()
    if not settings.admins:
        logging.getLogger(__name__).warning(
            "ADMINS ro'yxati bo'sh. Admin buyruqlari ishlamaydi."
        )
    db = Database(settings.db_path)
    await db.init()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    rate_mw = RateLimitMiddleware(limit_seconds=settings.rate_limit_seconds)
    dp.message.middleware(rate_mw)
    dp.callback_query.middleware(rate_mw)

    dp.include_router(admin.router)
    dp.include_router(user.router)

    dp["db"] = db
    dp["settings"] = settings
    dp.errors.register(on_error)

    logging.getLogger(__name__).info("Bot ishga tushdi")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
