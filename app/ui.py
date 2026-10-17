"""Menyu va umumiy klaviaturalar. Ranglar — Bot API 9.4 `style` (success/danger/primary)."""

from aiogram.types import (InlineKeyboardButton as IB, InlineKeyboardMarkup,
                           KeyboardButton as KB, ReplyKeyboardMarkup)

from .catalog import ORDER, SERVICES

BALANCE = "💰 Balans"
ORDERS = "📦 Buyurtmalarim"
HELP = "ℹ️ Yordam"


def label(slug: str) -> str:
    s = SERVICES[slug]
    return f"{s.emoji} {s.title}"


SERVICE_LABELS = {label(slug): slug for slug in ORDER}
MENU_TEXTS = set(SERVICE_LABELS) | {BALANCE, ORDERS, HELP}


def main_menu() -> ReplyKeyboardMarkup:
    """Chap ustun ko'k, o'ng ustun yashil, «Yordam» qizil — asosiy botdagi uslub."""
    rows = []
    slugs = list(ORDER)
    for i in range(0, len(slugs), 2):
        pair = slugs[i:i + 2]
        rows.append([KB(text=label(s), style=("primary", "success")[j]) for j, s in enumerate(pair)])
    rows.append([KB(text=BALANCE, style="primary"), KB(text=ORDERS, style="success")])
    rows.append([KB(text=HELP, style="danger")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, input_field_placeholder="Xizmatni tanlang 👇")


def cancel_button() -> IB:
    return IB(text="❌ Bekor qilish", callback_data="cancel", style="danger")


def inline(*rows: list[IB]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=list(rows))
