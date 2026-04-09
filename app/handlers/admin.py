from __future__ import annotations

import asyncio
from html import escape
import logging
import re

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.config import Settings
from app.db import Database
from app.keyboards.reply import (
    ADMIN_PANEL_TEXTS,
    ADM_ADD,
    ADM_ADD_ALIASES,
    ADM_DEL,
    ADM_DEL_ALIASES,
    ADM_LIST,
    ADM_LIST_ALIASES,
    BTN_ADMINS,
    BTN_ADMINS_ALIASES,
    BTN_ADD_CONTENT,
    BTN_ADD_CONTENT_ALIASES,
    BTN_BACK,
    BTN_BACK_ALIASES,
    BTN_BROADCAST,
    BTN_BROADCAST_ALIASES,
    BTN_STATS,
    BTN_STATS_ALIASES,
    BTN_SUBSCRIPTION,
    BTN_SUBSCRIPTION_ALIASES,
    BTN_TEXTS,
    BTN_TEXTS_ALIASES,
    SUB_ADD,
    SUB_ADD_ALIASES,
    SUB_DEL,
    SUB_DEL_ALIASES,
    SUB_LIST,
    SUB_LIST_ALIASES,
    CONTENT_ADD,
    CONTENT_ADD_ALIASES,
    CONTENT_DEL,
    CONTENT_DEL_ALIASES,
    CONTENT_LIST,
    CONTENT_LIST_ALIASES,
    TEXT_INVALID_CODE,
    TEXT_INVALID_CODE_ALIASES,
    TEXT_NOT_FOUND,
    TEXT_NOT_FOUND_ALIASES,
    TEXT_START,
    TEXT_START_ALIASES,
    TEXT_SUBSCRIPTION,
    TEXT_SUBSCRIPTION_ALIASES,
    admin_main_keyboard,
    admins_menu_keyboard,
    content_menu_keyboard,
    subscription_menu_keyboard,
    texts_menu_keyboard,
)
from app.services.admins import is_admin_user
from app.texts import DEFAULT_TEXTS, TEXT_PARSE_MODE


logger = logging.getLogger(__name__)
router = Router(name="admin")
CODE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ADMIN_PANEL_MESSAGE = (
    "🛠 <b>Boshqaruv paneli</b>\n\n"
    "Kerakli bo'limni tanlang. Kontent, obuna va bot sozlamalari shu yerdan boshqariladi."
)
ADMIN_ONLY_MESSAGE = "🔒 Bu bo'lim faqat adminlar uchun."
ADMIN_ONLY_CALLBACK_MESSAGE = "🔒 Bu amal faqat adminlar uchun."
CANCELLED_MESSAGE = "❎ Amal bekor qilindi.\n\nSiz yana boshqaruv panelidasiz."


class AddContentState(StatesGroup):
    waiting_code = State()
    waiting_media = State()


class AddChannelState(StatesGroup):
    waiting_channel_id = State()
    waiting_invite_link = State()


class RemoveChannelState(StatesGroup):
    waiting_channel_id = State()


class RemoveContentState(StatesGroup):
    waiting_code = State()


class AdminManageState(StatesGroup):
    waiting_add_admin = State()
    waiting_remove_admin = State()


class BroadcastState(StatesGroup):
    waiting_message = State()


class TextEditState(StatesGroup):
    waiting_text = State()


async def _require_admin_message(
    message: Message,
    settings: Settings,
    db: Database,
    text: str | None = ADMIN_ONLY_MESSAGE,
) -> bool:
    if not message.from_user:
        return False
    if not await is_admin_user(message.from_user.id, settings, db):
        if text:
            await message.answer(text)
        return False
    return True


async def _require_admin_callback(
    callback: CallbackQuery,
    settings: Settings,
    db: Database,
    text: str | None = ADMIN_ONLY_CALLBACK_MESSAGE,
) -> bool:
    if not callback.from_user:
        return False
    if not await is_admin_user(callback.from_user.id, settings, db):
        if text:
            await callback.answer(text, show_alert=True)
        return False
    return True


async def _handle_cancel(message: Message, state: FSMContext) -> bool:
    if not message.text:
        return False
    text = message.text.strip()
    if text == BTN_BACK or text in ADMIN_PANEL_TEXTS:
        await state.clear()
        await message.answer(
            ADMIN_PANEL_MESSAGE,
            parse_mode="HTML",
            reply_markup=admin_main_keyboard(),
        )
        return True
    return False


def _is_valid_code(code: str) -> bool:
    return bool(CODE_RE.fullmatch(code))


def _safe(value: object | None, fallback: str = "-") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return escape(text or fallback, quote=False)


def _channel_ref(
    username: str | None,
    invite_link: str | None = None,
    chat_id: int | None = None,
) -> str:
    if username:
        return f"@{_safe(username.lstrip('@'))}"
    if invite_link:
        return _safe(invite_link)
    if chat_id is not None:
        return f"<code>{chat_id}</code>"
    return "private/no-username"


def _channel_card(
    chat_id: int,
    title: str | None,
    username: str | None,
    invite_link: str | None = None,
    index: int | None = None,
) -> str:
    prefix = f"{index}. " if index is not None else ""
    return "\n".join(
        [
            f"{prefix}📣 <b>{_safe(title, 'Nomsiz kanal')}</b>",
            f"🔗 {_channel_ref(username, invite_link=invite_link, chat_id=chat_id)}",
            f"🆔 <code>{chat_id}</code>",
        ]
    )


def _admin_card(user_id: int, username: str | None, full_name: str | None) -> str:
    lines: list[str] = []
    if full_name:
        lines.append(f"👤 <b>{_safe(full_name)}</b>")
        if username:
            lines.append(f"🔗 @{_safe(username.lstrip('@'))}")
    elif username:
        lines.append(f"👤 <b>@{_safe(username.lstrip('@'))}</b>")
    else:
        lines.append(f"👤 <code>{user_id}</code>")
    lines.append(f"🆔 <code>{user_id}</code>")
    return "\n".join(lines)


def _content_card(
    code: str,
    file_type: str,
    caption: str | None,
    created_at: str,
    index: int | None = None,
) -> str:
    prefix = f"{index}. " if index is not None else ""
    preview = (caption or "Caption yo'q").strip()
    if len(preview) > 60:
        preview = f"{preview[:57]}..."
    return "\n".join(
        [
            f"{prefix}🎬 <b>{_safe(code)}</b>",
            f"📦 Turi: <b>{_safe(file_type)}</b>",
            f"📝 {_safe(preview)}",
            f"🕒 {_safe(created_at)}",
        ]
    )


def _channel_confirm_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✨ Qo'shish",
                    callback_data=f"admin_ch_add:ok:{chat_id}",
                ),
                InlineKeyboardButton(
                    text="✖️ Bekor qilish",
                    callback_data=f"admin_ch_add:cancel:{chat_id}",
                ),
            ]
        ]
    )


async def _resolve_channel(
    message: Message,
    bot: Bot | None,
    arg: str | None = None,
) -> tuple[int, str | None, str | None]:
    if message.forward_from_chat and message.forward_from_chat.type == "channel":
        chat = message.forward_from_chat
        return chat.id, chat.title, (chat.username or "").lstrip("@") or None

    if message.sender_chat and message.sender_chat.type == "channel":
        chat = message.sender_chat
        return chat.id, chat.title, (chat.username or "").lstrip("@") or None

    forward_origin = getattr(message, "forward_origin", None)
    origin_chat = getattr(forward_origin, "chat", None)
    if origin_chat and getattr(origin_chat, "type", None) == "channel":
        return origin_chat.id, origin_chat.title, (origin_chat.username or "").lstrip("@") or None

    if arg:
        if bot is None:
            raise ValueError("bot_required_for_arg")
        value = arg.strip()
        if not value:
            raise ValueError("channel_arg_empty")
        if value.startswith("@"):
            chat = await bot.get_chat(value)
            return chat.id, chat.title, (chat.username or "").lstrip("@") or None
        chat_id = int(value)
        chat = await bot.get_chat(chat_id)
        return chat.id, chat.title, (chat.username or "").lstrip("@") or None

    raise ValueError("channel_source_not_found")


def _normalize_invite_link(raw: str) -> str | None:
    value = raw.strip()
    if not value:
        return None
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("t.me/") or value.startswith("telegram.me/"):
        return f"https://{value}"
    return None


TEXT_KEY_MAP: dict[str, str] = {
    **{label: "start" for label in TEXT_START_ALIASES},
    **{label: "invalid_code" for label in TEXT_INVALID_CODE_ALIASES},
    **{label: "code_not_found" for label in TEXT_NOT_FOUND_ALIASES},
    **{label: "subscription_template" for label in TEXT_SUBSCRIPTION_ALIASES},
}


@router.message(F.text.in_(BTN_BACK_ALIASES))
async def admin_back(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db, None):
        return
    await state.clear()
    await message.answer(
        ADMIN_PANEL_MESSAGE,
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )


@router.message(F.text.in_(BTN_SUBSCRIPTION_ALIASES))
async def open_subscription_menu(message: Message, settings: Settings, db: Database) -> None:
    if not await _require_admin_message(message, settings, db):
        return
    await message.answer(
        "🔔 <b>Obuna sozlamalari</b>\n\n"
        "Kanallarni ulash, olib tashlash yoki ro'yxatni shu bo'limdan boshqarasiz.",
        parse_mode="HTML",
        reply_markup=subscription_menu_keyboard(),
    )


@router.message(F.text.in_(SUB_ADD_ALIASES))
async def menu_add_channel(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db):
        return
    await state.set_state(AddChannelState.waiting_channel_id)
    await message.answer(
        "➕ <b>Yangi kanal ulash</b>\n\n"
        "Kanal postini forward qiling yoki <code>chat_id</code> yuboring.\n"
        "Private kanal odatda <code>-100</code> bilan boshlanadi.\n\n"
        "Ortga qaytish uchun <b>🏠 Asosiy panel</b> tugmasidan foydalaning.",
        parse_mode="HTML",
        reply_markup=subscription_menu_keyboard(),
    )


@router.message(AddChannelState.waiting_channel_id)
async def menu_add_channel_id(
    message: Message,
    state: FSMContext,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if not await _require_admin_message(message, settings, db, ADMIN_ONLY_CALLBACK_MESSAGE):
        await state.clear()
        return
    if await _handle_cancel(message, state):
        return

    arg = (message.text or "").strip() if message.text else None
    try:
        chat_id, title, username = await _resolve_channel(message=message, bot=bot, arg=arg)
    except ValueError:
        await message.answer("⚠️ chat_id noto'g'ri. Namuna: <code>-1001234567890</code>", parse_mode="HTML")
        return
    except Exception as exc:
        logger.warning("Kanalni qo'shishda xato: %s", exc)
        await message.answer(
            "🚫 Kanalni tekshirib bo'lmadi.\n\nBot shu kanalda admin ekanini tekshirib ko'ring."
        )
        return

    if username:
        await db.add_channel(chat_id=chat_id, title=title, username=username, invite_link=None)
        await state.clear()
        await message.answer(
            "✅ <b>Kanal muvaffaqiyatli ulandi</b>\n\n"
            f"{_channel_card(chat_id, title, username)}",
            parse_mode="HTML",
            reply_markup=subscription_menu_keyboard(),
        )
        return

    await state.update_data(chat_id=chat_id, title=title, username=username)
    await state.set_state(AddChannelState.waiting_invite_link)
    await message.answer(
        "🔗 <b>Taklif havolasini yuboring</b>\n\n"
        "Namuna: <code>https://t.me/+AbCdEf...</code>",
        parse_mode="HTML",
    )


@router.message(AddChannelState.waiting_invite_link)
async def menu_add_channel_invite(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db, ADMIN_ONLY_CALLBACK_MESSAGE):
        await state.clear()
        return
    if await _handle_cancel(message, state):
        return

    if not message.text:
        await message.answer(
            "⚠️ Faqat taklif havolasini yuboring.\n\nNamuna: <code>https://t.me/+AbCdEf...</code>",
            parse_mode="HTML",
        )
        return
    invite_link = _normalize_invite_link(message.text)
    if not invite_link:
        await message.answer(
            "⚠️ Havola formati noto'g'ri.\n\nNamuna: <code>https://t.me/+AbCdEf...</code>",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    chat_id = data.get("chat_id")
    title = data.get("title")
    username = data.get("username")
    if not chat_id:
        await state.clear()
        await message.answer("⚠️ Sessiya topilmadi. Kanalni qaytadan ulab ko'ring.")
        return

    await db.add_channel(
        chat_id=int(chat_id),
        title=title,
        username=username,
        invite_link=invite_link,
    )
    await state.clear()
    await message.answer(
        "✅ <b>Private kanal muvaffaqiyatli ulandi</b>\n\n"
        f"{_channel_card(int(chat_id), title, username, invite_link=invite_link)}",
        parse_mode="HTML",
        reply_markup=subscription_menu_keyboard(),
    )


@router.message(F.text.in_(SUB_DEL_ALIASES))
async def menu_delete_channel(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db):
        return
    await state.set_state(RemoveChannelState.waiting_channel_id)
    await message.answer(
        "🗑 <b>Kanalni olib tashlash</b>\n\n"
        "O'chirish uchun kanalning <code>chat_id</code> sini yuboring.",
        parse_mode="HTML",
        reply_markup=subscription_menu_keyboard(),
    )


@router.message(RemoveChannelState.waiting_channel_id)
async def menu_delete_channel_id(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db, ADMIN_ONLY_CALLBACK_MESSAGE):
        await state.clear()
        return
    if await _handle_cancel(message, state):
        return

    if not message.text or not message.text.strip().lstrip("-").isdigit():
        await message.answer("⚠️ chat_id raqam bo'lishi kerak.")
        return

    chat_id = int(message.text.strip())
    deleted = await db.remove_channel(chat_id)
    await state.clear()
    if deleted:
        await message.answer(
            f"🗑 Kanal ro'yxatdan olib tashlandi.\n🆔 <code>{chat_id}</code>",
            parse_mode="HTML",
            reply_markup=subscription_menu_keyboard(),
        )
    else:
        await message.answer(
            "❌ Bu <code>chat_id</code> bo'yicha kanal topilmadi.",
            parse_mode="HTML",
            reply_markup=subscription_menu_keyboard(),
        )


@router.message(F.text.in_(SUB_LIST_ALIASES))
async def menu_list_channels(message: Message, settings: Settings, db: Database) -> None:
    if not await _require_admin_message(message, settings, db):
        return
    channels = await db.list_channels()
    if not channels:
        await message.answer(
            "📭 Hozircha majburiy obuna uchun ulangan kanallar yo'q.",
            reply_markup=subscription_menu_keyboard(),
        )
        return

    lines = ["🔔 <b>Ulangan kanallar ro'yxati</b>", ""]
    for i, channel in enumerate(channels, start=1):
        lines.append(
            _channel_card(
                channel.chat_id,
                channel.title,
                channel.username,
                invite_link=channel.invite_link,
                index=i,
            )
        )
        lines.append("")

    await message.answer(
        "\n".join(lines).strip(),
        parse_mode="HTML",
        reply_markup=subscription_menu_keyboard(),
    )


@router.message(F.text.in_(BTN_ADD_CONTENT_ALIASES))
async def open_content_menu(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db):
        return
    await state.clear()
    await message.answer(
        "🎞 <b>Kontentlar bo'limi</b>\n\n"
        "Kontentlarni qo'shing, ro'yxatini ko'ring yoki kerak bo'lsa o'chiring.",
        parse_mode="HTML",
        reply_markup=content_menu_keyboard(),
    )


@router.message(F.text.in_(CONTENT_ADD_ALIASES))
async def menu_add_content(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db):
        return
    await state.set_state(AddContentState.waiting_code)
    await message.answer(
        "➕ <b>Kontent qo'shish</b>\n\n"
        "Avval kontent kodini yuboring.\n"
        "Namuna: <code>1024</code>",
        parse_mode="HTML",
        reply_markup=content_menu_keyboard(),
    )


@router.message(F.text.in_(CONTENT_LIST_ALIASES))
async def menu_list_contents(message: Message, settings: Settings, db: Database) -> None:
    if not await _require_admin_message(message, settings, db):
        return

    total_contents = await db.count_contents()
    contents = await db.list_contents(limit=20)
    if not contents:
        await message.answer(
            "📭 Hozircha bazada kontent yo'q.",
            reply_markup=content_menu_keyboard(),
        )
        return

    lines = [
        "📚 <b>Kontentlar ro'yxati</b>",
        "",
        f"Jami kontent: <b>{total_contents}</b>",
        "Oxirgi 20 ta yozuv:",
        "",
    ]
    for index, content in enumerate(contents, start=1):
        lines.append(
            _content_card(
                content.code,
                content.file_type,
                content.caption,
                content.created_at,
                index=index,
            )
        )
        lines.append("")

    await message.answer(
        "\n".join(lines).strip(),
        parse_mode="HTML",
        reply_markup=content_menu_keyboard(),
    )


@router.message(F.text.in_(CONTENT_DEL_ALIASES))
async def menu_delete_content(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db):
        return
    await state.set_state(RemoveContentState.waiting_code)
    await message.answer(
        "🗑 <b>Kontentni o'chirish</b>\n\n"
        "O'chirish uchun kontent kodini yuboring.",
        parse_mode="HTML",
        reply_markup=content_menu_keyboard(),
    )


@router.message(AddContentState.waiting_code)
async def menu_add_content_code(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db, ADMIN_ONLY_CALLBACK_MESSAGE):
        await state.clear()
        return
    if await _handle_cancel(message, state):
        return
    code = (message.text or "").strip()
    if not code:
        await message.answer("⚠️ Kod bo'sh bo'lmasin.")
        return
    if not _is_valid_code(code):
        await message.answer(
            "⚠️ Kod formati noto'g'ri.\n\n"
            "1-64 belgi ishlating: harf, raqam, <code>-</code> yoki <code>_</code>.",
            parse_mode="HTML",
        )
        return
    await state.update_data(code=code)
    await state.set_state(AddContentState.waiting_media)
    await message.answer(
        f"🧩 <b>Kod qabul qilindi:</b> <code>{code}</code>\n\n"
        "Endi video yoki document yuboring.",
        parse_mode="HTML",
        reply_markup=content_menu_keyboard(),
    )


@router.message(F.text.in_(BTN_ADMINS_ALIASES))
async def menu_admins(message: Message, settings: Settings, db: Database) -> None:
    if not await _require_admin_message(message, settings, db):
        return
    await message.answer(
        "🛡 <b>Adminlar bo'limi</b>\n\n"
        "Yangi admin qo'shing, o'chiring yoki joriy ro'yxatni ko'ring.",
        parse_mode="HTML",
        reply_markup=admins_menu_keyboard(),
    )


@router.message(F.text.in_(ADM_ADD_ALIASES))
async def menu_add_admin(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db):
        return
    await state.set_state(AdminManageState.waiting_add_admin)
    await message.answer(
        "➕ <b>Yangi admin qo'shish</b>\n\n"
        "Admin qilinadigan foydalanuvchining <code>user_id</code> sini yuboring\n"
        "yoki uning xabarini forward qiling.",
        parse_mode="HTML",
        reply_markup=admins_menu_keyboard(),
    )


@router.message(AdminManageState.waiting_add_admin)
async def menu_add_admin_id(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db, ADMIN_ONLY_CALLBACK_MESSAGE):
        await state.clear()
        return
    if await _handle_cancel(message, state):
        return

    user_id: int | None = None
    username: str | None = None
    full_name: str | None = None

    if message.forward_from:
        user_id = message.forward_from.id
        username = message.forward_from.username
        full_name = message.forward_from.full_name
    elif message.text and message.text.strip().isdigit():
        user_id = int(message.text.strip())
    else:
        await message.answer(
            "⚠️ Foydalanuvchi aniqlanmadi.\n\n"
            "<code>user_id</code> yuboring yoki uning xabarini forward qiling.",
            parse_mode="HTML",
        )
        return

    if user_id in settings.admins:
        await state.clear()
        await message.answer(
            "⭐ Bu foydalanuvchi allaqachon superadmin ro'yxatida.",
            reply_markup=admins_menu_keyboard(),
        )
        return

    await db.add_admin(user_id=user_id, username=username, full_name=full_name)
    await state.clear()
    await message.answer(
        "✅ <b>Admin muvaffaqiyatli qo'shildi</b>\n\n"
        f"{_admin_card(user_id, username, full_name)}",
        parse_mode="HTML",
        reply_markup=admins_menu_keyboard(),
    )


@router.message(F.text.in_(ADM_DEL_ALIASES))
async def menu_remove_admin(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db):
        return
    await state.set_state(AdminManageState.waiting_remove_admin)
    await message.answer(
        "➖ <b>Adminni o'chirish</b>\n\n"
        "Olib tashlash uchun adminning <code>user_id</code> sini yuboring.",
        parse_mode="HTML",
        reply_markup=admins_menu_keyboard(),
    )


@router.message(AdminManageState.waiting_remove_admin)
async def menu_remove_admin_id(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db, ADMIN_ONLY_CALLBACK_MESSAGE):
        await state.clear()
        return
    if await _handle_cancel(message, state):
        return
    if not message.text or not message.text.strip().isdigit():
        await message.answer("⚠️ user_id raqam bo'lishi kerak.")
        return

    user_id = int(message.text.strip())
    if user_id in settings.admins:
        await state.clear()
        await message.answer(
            "🚫 Superadminni o'chirib bo'lmaydi.",
            reply_markup=admins_menu_keyboard(),
        )
        return

    removed = await db.remove_admin(user_id)
    await state.clear()
    if removed:
        await message.answer(
            f"✅ Admin olib tashlandi.\n👤 <code>{user_id}</code>",
            parse_mode="HTML",
            reply_markup=admins_menu_keyboard(),
        )
    else:
        await message.answer(
            "❌ Bu <code>user_id</code> bo'yicha admin topilmadi.",
            parse_mode="HTML",
            reply_markup=admins_menu_keyboard(),
        )


@router.message(F.text.in_(ADM_LIST_ALIASES))
async def menu_list_admins(message: Message, settings: Settings, db: Database) -> None:
    if not await _require_admin_message(message, settings, db):
        return

    lines = ["🛡 <b>Adminlar ro'yxati</b>", ""]
    if settings.admins:
        lines.append("⭐ <b>Superadminlar</b>")
        for admin_id in sorted(settings.admins):
            user = await db.get_user(admin_id)
            lines.append(
                _admin_card(
                    admin_id,
                    user.username if user else None,
                    user.full_name if user else None,
                ).replace("👤", "👑", 1)
            )
        lines.append("")

    db_admins = await db.list_admins()
    if db_admins:
        lines.append("🧾 <b>Qo'shilgan adminlar</b>")
        for admin in db_admins:
            if admin.user_id in settings.admins:
                continue
            lines.append(_admin_card(admin.user_id, admin.username, admin.full_name))
            lines.append("")
    elif not settings.admins:
        lines.append("📭 Hozircha adminlar ro'yxati bo'sh.")

    await message.answer("\n".join(lines).strip(), parse_mode="HTML", reply_markup=admins_menu_keyboard())


@router.message(F.text.in_(BTN_STATS_ALIASES))
async def menu_stats(message: Message, settings: Settings, db: Database) -> None:
    if not await _require_admin_message(message, settings, db):
        return
    total_users = await db.count_users()
    active_users_24h = await db.count_active_users(24)
    active_users_7d = await db.count_active_users(24 * 7)
    contents = await db.count_contents()
    videos = await db.count_contents_by_type("video")
    documents = await db.count_contents_by_type("document")
    recent_contents = await db.list_contents(limit=1)
    channels = await db.count_channels()
    public_channels = await db.count_public_channels()
    private_channels = await db.count_private_channels()
    db_admins = await db.list_admins()
    admin_ids = {admin.user_id for admin in db_admins}
    admin_ids.update(settings.admins)
    admins_count = len(admin_ids)
    last_content_code = recent_contents[0].code if recent_contents else "yo'q"

    await message.answer(
        "\n".join(
            [
                "📈 <b>Bot statistikasi</b>",
                "",
                "👥 <b>Foydalanuvchilar</b>",
                f"• Jami: <b>{total_users}</b>",
                f"• Oxirgi 24 soat: <b>{active_users_24h}</b>",
                f"• Oxirgi 7 kun: <b>{active_users_7d}</b>",
                "",
                "🎞 <b>Kontentlar</b>",
                f"• Jami: <b>{contents}</b>",
                f"• Videolar: <b>{videos}</b>",
                f"• Dokumentlar: <b>{documents}</b>",
                f"• Oxirgi kod: <code>{last_content_code}</code>",
                "",
                "🔔 <b>Kanallar</b>",
                f"• Jami: <b>{channels}</b>",
                f"• Public: <b>{public_channels}</b>",
                f"• Private: <b>{private_channels}</b>",
                "",
                "🛡 <b>Boshqaruv</b>",
                f"🛡 Adminlar: <b>{admins_count}</b>",
            ]
        ),
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )


@router.message(F.text.in_(BTN_BROADCAST_ALIASES))
async def menu_broadcast(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db):
        return
    await state.set_state(BroadcastState.waiting_message)
    await message.answer(
        "📣 <b>Xabar tarqatish</b>\n\n"
        "Obunachilarga yuboriladigan xabarni yuboring.\n\n"
        "Ortga qaytish uchun <b>🏠 Asosiy panel</b> tugmasidan foydalaning.",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )


@router.message(BroadcastState.waiting_message)
async def menu_broadcast_message(
    message: Message,
    state: FSMContext,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if not await _require_admin_message(message, settings, db, ADMIN_ONLY_CALLBACK_MESSAGE):
        await state.clear()
        return
    if await _handle_cancel(message, state):
        return

    user_ids = await db.list_user_ids()
    if not user_ids:
        await state.clear()
        await message.answer("📭 Tarqatish uchun foydalanuvchilar topilmadi.")
        return

    await message.answer(
        f"🚀 Tarqatish boshlandi.\n\nJami foydalanuvchi: <b>{len(user_ids)}</b>",
        parse_mode="HTML",
    )
    success = 0
    failed = 0

    for user_id in user_ids:
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            success += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        await asyncio.sleep(0.03)

    await state.clear()
    await message.answer(
        "📬 <b>Tarqatish yakunlandi</b>\n\n"
        f"✅ Yuborildi: <b>{success}</b>\n"
        f"❌ Yetmadi: <b>{failed}</b>",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )


@router.message(F.text.in_(BTN_TEXTS_ALIASES))
async def menu_texts(message: Message, settings: Settings, db: Database) -> None:
    if not await _require_admin_message(message, settings, db):
        return
    await message.answer(
        "🎨 <b>Matn dizayni</b>\n\n"
        "Botdagi asosiy matnlarni shu yerdan chiroyli tarzda tahrirlaysiz.",
        parse_mode="HTML",
        reply_markup=texts_menu_keyboard(),
    )


@router.message(F.text.in_(TEXT_KEY_MAP.keys()))
async def menu_texts_choose(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db):
        return

    key = TEXT_KEY_MAP[message.text]
    current = await db.get_text(key) or DEFAULT_TEXTS[key]
    await state.set_state(TextEditState.waiting_text)
    await state.update_data(text_key=key)

    await message.answer("🧾 <b>Hozirgi matn</b>", parse_mode="HTML")
    await message.answer(current, parse_mode=TEXT_PARSE_MODE.get(key))
    hint = "✍️ Yangi matnni yuboring."
    if key == "subscription_template":
        hint += " {channels} joyida kanallar ro'yxati chiqadi."
    await message.answer(hint, reply_markup=texts_menu_keyboard())


@router.message(TextEditState.waiting_text)
async def menu_texts_update(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db, ADMIN_ONLY_CALLBACK_MESSAGE):
        await state.clear()
        return
    if await _handle_cancel(message, state):
        return
    if not message.text:
        await message.answer("⚠️ Iltimos, faqat matn yuboring.")
        return

    data = await state.get_data()
    key = data.get("text_key")
    if not key:
        await state.clear()
        await message.answer("⚠️ Sessiya topilmadi. Qaytadan urinib ko'ring.")
        return

    await db.set_text(key, message.text)
    await state.clear()
    if key == "subscription_template" and "{channels}" not in message.text:
        await message.answer(
            "⚠️ <code>{channels}</code> topilmadi. Kanal ro'yxati avtomatik oxiriga qo'shiladi.",
            parse_mode="HTML",
        )
    await message.answer("✅ Matn muvaffaqiyatli saqlandi.", reply_markup=texts_menu_keyboard())


@router.message(AddContentState.waiting_media)
async def process_media_for_code(
    message: Message,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    if not await _require_admin_message(message, settings, db, ADMIN_ONLY_CALLBACK_MESSAGE):
        await state.clear()
        return
    if await _handle_cancel(message, state):
        return

    data = await state.get_data()
    code = str(data.get("code", "")).strip()
    if not code:
        await state.clear()
        await message.answer(
            "⚠️ Sessiya topilmadi.\n\nKontent bo'limidan qaytadan kod kiriting.",
            parse_mode="HTML",
            reply_markup=content_menu_keyboard(),
        )
        return

    file_id: str | None = None
    file_type: str | None = None

    if message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"

    if not file_id or not file_type:
        await message.answer(
            "⚠️ Faqat video yoki document yuboring.",
            reply_markup=content_menu_keyboard(),
        )
        return

    caption = message.caption
    await db.upsert_content(code=code, file_id=file_id, file_type=file_type, caption=caption)
    await state.clear()

    await message.answer(
        "✅ <b>Kontent muvaffaqiyatli saqlandi</b>\n\n"
        f"🔑 Kod: <code>{code}</code>\n"
        f"📦 Turi: <b>{file_type}</b>",
        parse_mode="HTML",
        reply_markup=content_menu_keyboard(),
    )

@router.message(RemoveContentState.waiting_code)
async def menu_delete_content_code(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db):
        return
    if await _handle_cancel(message, state):
        return

    code = (message.text or "").strip()
    if not code:
        await message.answer(
            "⚠️ Kontent kodi bo'sh bo'lmasin.",
            reply_markup=content_menu_keyboard(),
        )
        return
    if not _is_valid_code(code):
        await message.answer(
            "⚠️ Kod formati noto'g'ri.\n\n"
            "1-64 belgi ishlating: harf, raqam, <code>-</code> yoki <code>_</code>.",
            parse_mode="HTML",
            reply_markup=content_menu_keyboard(),
        )
        return

    deleted = await db.delete_content(code)
    await state.clear()
    if deleted:
        await message.answer(
            f"🗑 Kontent olib tashlandi.\n🔑 <code>{code}</code>",
            parse_mode="HTML",
            reply_markup=content_menu_keyboard(),
        )
    else:
        await message.answer(
            "❌ Bu kod bo'yicha kontent topilmadi.",
            reply_markup=content_menu_keyboard(),
        )


@router.message(F.forward_from_chat | F.sender_chat | F.forward_origin)
async def suggest_channel_add_from_forward(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await _require_admin_message(message, settings, db, None):
        return
    if await state.get_state():
        return

    try:
        chat_id, title, username = await _resolve_channel(message=message, bot=None, arg=None)
    except Exception:
        return

    channel_ref = _channel_ref(username, chat_id=chat_id)
    await message.answer(
        "✨ <b>Kanal aniqlandi</b>\n\n"
        f"📛 Nomi: <b>{_safe(title, 'Nomsiz kanal')}</b>\n"
        f"🔗 Manzil: {channel_ref}\n\n"
        "Majburiy obuna ro'yxatiga qo'shaymi?",
        parse_mode="HTML",
        reply_markup=_channel_confirm_keyboard(chat_id),
    )


@router.callback_query(F.data.startswith("admin_ch_add:"))
async def confirm_channel_add(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if not await _require_admin_callback(callback, settings, db):
        return
    if not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":", maxsplit=2)
    if len(parts) != 3:
        await callback.answer("Noto'g'ri amal.", show_alert=True)
        return
    action, chat_id_raw = parts[1], parts[2]

    try:
        chat_id = int(chat_id_raw)
    except ValueError:
        await callback.answer("chat_id noto'g'ri.", show_alert=True)
        return

    if action == "cancel":
        if callback.message:
            await callback.message.edit_text("❎ Kanal qo'shish bekor qilindi.", reply_markup=None)
        await callback.answer("Bekor qilindi")
        return

    if action != "ok":
        await callback.answer("Noto'g'ri amal.", show_alert=True)
        return

    try:
        chat = await bot.get_chat(chat_id)
        title = chat.title
        username = (chat.username or "").lstrip("@") or None
    except Exception as exc:
        logger.warning("Kanalni callback orqali qo'shishda xato: %s", exc)
        await callback.answer("Kanalni qo'shib bo'lmadi.", show_alert=True)
        return

    if callback.message:
        channel_ref = _channel_ref(username, chat_id=chat_id)
        if username:
            await db.add_channel(chat_id=chat_id, title=title, username=username, invite_link=None)
            await callback.message.edit_text(
                "✅ <b>Kanal ro'yxatga qo'shildi</b>\n\n"
                f"📛 Nomi: <b>{_safe(title, 'Nomsiz kanal')}</b>\n"
                f"🔗 Manzil: {channel_ref}",
                parse_mode="HTML",
                reply_markup=None,
            )
            await callback.answer("Qo'shildi")
            return

        await state.update_data(chat_id=chat_id, title=title, username=username)
        await state.set_state(AddChannelState.waiting_invite_link)
        await callback.message.edit_text(
            "🔒 <b>Private kanal aniqlandi</b>\n\n"
            f"{_channel_card(chat_id, title, username)}\n\n"
            "🔗 <b>Taklif havolasini yuboring</b>\n"
            "Namuna: <code>https://t.me/+AbCdEf...</code>",
            parse_mode="HTML",
            reply_markup=None,
        )
        await callback.answer("Taklif havolasini yuboring")
        return

    await callback.answer("Qo'shildi")
