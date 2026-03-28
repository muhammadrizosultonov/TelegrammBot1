from __future__ import annotations

DEFAULT_TEXTS: dict[str, str] = {
    "start": (
        "✨ <b>Assalomu alaykum va xush kelibsiz!</b>\n\n"
        "🎬 Bu bot maxsus kod orqali sizga biriktirilgan kontentni bir zumda yuboradi.\n\n"
        "🔑 Namunaviy kod: <code>1024</code>\n\n"
        "📌 Jarayon juda oddiy:\n"
        "• kodni yuborasiz\n"
        "• obuna tekshiriladi\n"
        "• kontent avtomatik ochiladi\n\n"
        "Marhamat, kodni yuboring 👇"
    ),
    "invalid_code": (
        "⚠️ <b>Kod formati mos kelmadi.</b>\n\n"
        "To'g'ri format:\n"
        "• faqat harf va raqamlar\n"
        "• <code>-</code> va <code>_</code> ishlatish mumkin\n"
        "• uzunligi 1 dan 64 belgigacha\n\n"
        "Kodni qayta yuborib ko'ring 👇"
    ),
    "code_not_found": (
        "😕 Bunday kod bo'yicha kontent topilmadi.\n\n"
        "Tekshirib ko'ring:\n"
        "• kod to'liq yozilganmi\n"
        "• bo'sh joy yoki ortiqcha belgi yo'qmi\n"
        "• kerak bo'lsa admin bilan bog'laning"
    ),
    "subscription_template": (
        "🔐 Kontentni ochish uchun avval quyidagi kanallarga qo'shiling:\n\n"
        "{channels}\n\n"
        "✅ Obuna bo'lib bo'lgach, pastdagi tugma orqali tekshiruvni yangilang."
    ),
}

TEXT_PARSE_MODE: dict[str, str | None] = {
    "start": "HTML",
    "invalid_code": "HTML",
    "code_not_found": None,
    "subscription_template": None,
}
