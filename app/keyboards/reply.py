from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_SUBSCRIPTION = "🔔 Obuna sozlamalari"
BTN_ADD_CONTENT = "🎞 Kontentlar"
BTN_ADMINS = "🛡 Adminlar"
BTN_STATS = "📈 Statistika"
BTN_BROADCAST = "📣 Xabar tarqatish"
BTN_TEXTS = "🎨 Matn dizayni"
BTN_BACK = "🏠 Asosiy panel"

SUB_ADD = "➕ Kanal ulash"
SUB_DEL = "🗑 Kanalni o'chirish"
SUB_LIST = "📋 Kanallar ro'yxati"

CONTENT_ADD = "➕ Kontent qo'shish"
CONTENT_LIST = "📚 Kontentlar ro'yxati"
CONTENT_DEL = "🗑 Kontentni o'chirish"

ADM_ADD = "➕ Admin qo'shish"
ADM_DEL = "➖ Adminni o'chirish"
ADM_LIST = "🧾 Adminlar ro'yxati"

TEXT_START = "🌟 Start matni"
TEXT_INVALID_CODE = "⚠️ Noto'g'ri kod matni"
TEXT_NOT_FOUND = "🔎 Kod topilmadi matni"
TEXT_SUBSCRIPTION = "🔐 Obuna matni"

LEGACY_BTN_SUBSCRIPTION = "📣 Majburiy obuna"
LEGACY_BTN_ADD_CONTENT = "🎬 Kino qo'shish"
LEGACY_BTN_ADD_CONTENT_V2 = "🎞 Kontent qo'shish"
LEGACY_BTN_ADMINS = "👤 Adminlar"
LEGACY_BTN_STATS = "📊 Statistika"
LEGACY_BTN_BROADCAST = "📨 Obunachilarga xabar yuborish"
LEGACY_BTN_TEXTS = "💬 Matnlar"
LEGACY_BTN_BACK = "⬅️ Orqaga"

LEGACY_SUB_ADD = "➕ Kanal qo'shish"
LEGACY_SUB_DEL = "➖ Kanal o'chirish"
LEGACY_SUB_LIST = "📋 Kanal ro'yxati"

LEGACY_ADM_DEL = "➖ Admin o'chirish"
LEGACY_ADM_LIST = "📋 Adminlar ro'yxati"

LEGACY_TEXT_START = "✍️ /start matni"
LEGACY_TEXT_INVALID_CODE = "✍️ Kod noto'g'ri matni"
LEGACY_TEXT_NOT_FOUND = "✍️ Kod topilmadi matni"
LEGACY_TEXT_SUBSCRIPTION = "✍️ Majburiy obuna matni"

BTN_SUBSCRIPTION_ALIASES = {BTN_SUBSCRIPTION, LEGACY_BTN_SUBSCRIPTION}
BTN_ADD_CONTENT_ALIASES = {
    BTN_ADD_CONTENT,
    LEGACY_BTN_ADD_CONTENT,
    LEGACY_BTN_ADD_CONTENT_V2,
}
BTN_ADMINS_ALIASES = {BTN_ADMINS, LEGACY_BTN_ADMINS}
BTN_STATS_ALIASES = {BTN_STATS, LEGACY_BTN_STATS}
BTN_BROADCAST_ALIASES = {BTN_BROADCAST, LEGACY_BTN_BROADCAST}
BTN_TEXTS_ALIASES = {BTN_TEXTS, LEGACY_BTN_TEXTS}
BTN_BACK_ALIASES = {BTN_BACK, LEGACY_BTN_BACK}

SUB_ADD_ALIASES = {SUB_ADD, LEGACY_SUB_ADD}
SUB_DEL_ALIASES = {SUB_DEL, LEGACY_SUB_DEL}
SUB_LIST_ALIASES = {SUB_LIST, LEGACY_SUB_LIST}

CONTENT_ADD_ALIASES = {CONTENT_ADD}
CONTENT_LIST_ALIASES = {CONTENT_LIST}
CONTENT_DEL_ALIASES = {CONTENT_DEL}

ADM_ADD_ALIASES = {ADM_ADD}
ADM_DEL_ALIASES = {ADM_DEL, LEGACY_ADM_DEL}
ADM_LIST_ALIASES = {ADM_LIST, LEGACY_ADM_LIST}

TEXT_START_ALIASES = {TEXT_START, LEGACY_TEXT_START}
TEXT_INVALID_CODE_ALIASES = {TEXT_INVALID_CODE, LEGACY_TEXT_INVALID_CODE}
TEXT_NOT_FOUND_ALIASES = {TEXT_NOT_FOUND, LEGACY_TEXT_NOT_FOUND}
TEXT_SUBSCRIPTION_ALIASES = {TEXT_SUBSCRIPTION, LEGACY_TEXT_SUBSCRIPTION}

ADMIN_PANEL_TEXTS = set().union(
    BTN_SUBSCRIPTION_ALIASES,
    BTN_ADD_CONTENT_ALIASES,
    BTN_ADMINS_ALIASES,
    BTN_STATS_ALIASES,
    BTN_BROADCAST_ALIASES,
    BTN_TEXTS_ALIASES,
    BTN_BACK_ALIASES,
    SUB_ADD_ALIASES,
    SUB_DEL_ALIASES,
    SUB_LIST_ALIASES,
    CONTENT_ADD_ALIASES,
    CONTENT_LIST_ALIASES,
    CONTENT_DEL_ALIASES,
    ADM_ADD_ALIASES,
    ADM_DEL_ALIASES,
    ADM_LIST_ALIASES,
    TEXT_START_ALIASES,
    TEXT_INVALID_CODE_ALIASES,
    TEXT_NOT_FOUND_ALIASES,
    TEXT_SUBSCRIPTION_ALIASES,
)


def admin_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SUBSCRIPTION), KeyboardButton(text=BTN_ADD_CONTENT)],
            [KeyboardButton(text=BTN_ADMINS), KeyboardButton(text=BTN_STATS)],
            [KeyboardButton(text=BTN_BROADCAST), KeyboardButton(text=BTN_TEXTS)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Kerakli bo'limni tanlang...",
    )


def subscription_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SUB_ADD), KeyboardButton(text=SUB_DEL)],
            [KeyboardButton(text=SUB_LIST)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Obuna bo'limidan amal tanlang...",
    )


def content_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=CONTENT_ADD), KeyboardButton(text=CONTENT_DEL)],
            [KeyboardButton(text=CONTENT_LIST)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Kontent bo'limidan amal tanlang...",
    )


def admins_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADM_ADD), KeyboardButton(text=ADM_DEL)],
            [KeyboardButton(text=ADM_LIST)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Adminlar bo'limidan amal tanlang...",
    )


def texts_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=TEXT_START)],
            [KeyboardButton(text=TEXT_INVALID_CODE)],
            [KeyboardButton(text=TEXT_NOT_FOUND)],
            [KeyboardButton(text=TEXT_SUBSCRIPTION)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Tahrirlash uchun matnni tanlang...",
    )
