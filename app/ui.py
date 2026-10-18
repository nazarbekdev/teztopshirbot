"""Menyu va umumiy klaviaturalar (uch tilda). Ranglar — Bot API 9.4 `style`."""

from aiogram.types import (InlineKeyboardButton as IB, InlineKeyboardMarkup,
                           KeyboardButton as KB, ReplyKeyboardMarkup)

from .catalog import ORDER, SERVICES, money, pick
from .i18n import LANGS, LANG_NAMES, all_langs, t

CONSENT_VERSION = "1.0"


def label(slug: str, lang: str) -> str:
    s = SERVICES[slug]
    return f"{s.emoji} {pick(s.title, lang)}"


# Tugma matni → xizmat (uchala tilda): menyu tili o'zgargandan keyin eski tugma ham ishlaydi
SERVICE_LABELS = {label(slug, lang): slug for slug in ORDER for lang in LANGS}
BALANCE_TEXTS, ORDERS_TEXTS = all_langs("btn_balance"), all_langs("btn_orders")
HELP_TEXTS, LANG_TEXTS = all_langs("btn_help"), all_langs("btn_lang")
PROMO_TEXTS = all_langs("btn_promo")
MENU_TEXTS = set(SERVICE_LABELS) | BALANCE_TEXTS | ORDERS_TEXTS | HELP_TEXTS | LANG_TEXTS | PROMO_TEXTS


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    """Chap ustun ko'k, o'ng ustun yashil, «Yordam» qizil — asosiy botdagi uslub."""
    rows = []
    slugs = list(ORDER)
    for i in range(0, len(slugs), 2):
        pair = slugs[i:i + 2]
        rows.append([KB(text=label(s, lang), style=("primary", "success")[j]) for j, s in enumerate(pair)])
    rows.append([KB(text=t(lang, "btn_balance"), style="primary"), KB(text=t(lang, "btn_orders"), style="success")])
    rows.append([KB(text=t(lang, "btn_lang"), style="primary"), KB(text=t(lang, "btn_promo"), style="success")])
    rows.append([KB(text=t(lang, "btn_help"), style="danger")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, input_field_placeholder=t(lang, "menu_placeholder"))


def cancel_button(lang: str) -> IB:
    return IB(text=t(lang, "btn_cancel"), callback_data="cancel", style="danger")


def inline(*rows: list[IB]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=list(rows))


def lang_keyboard() -> InlineKeyboardMarkup:
    return inline([IB(text=name, callback_data=f"lang:{code}") for code, name in LANG_NAMES.items()])


def consent_keyboard(lang: str, with_full: bool = True) -> InlineKeyboardMarkup:
    rows = []
    if with_full:
        rows.append([IB(text=t(lang, "btn_full"), callback_data="consent:full")])
    rows.append([IB(text=t(lang, "btn_agree"), callback_data="consent:yes", style="success")])
    return inline(*rows)


def subscribe_keyboard(lang: str, channel: str) -> InlineKeyboardMarkup:
    url = f"https://t.me/{channel.lstrip('@')}"
    return inline([IB(text=t(lang, "btn_channel"), url=url, style="primary")],
                  [IB(text=t(lang, "btn_subscribed"), callback_data="sub:check", style="success")])


def price_line(slug: str, lang: str) -> str:
    s = SERVICES[slug]
    if s.is_tiered:
        return t(lang, "from_price", price=money(s.min_price, lang))
    return money(s.price, lang)
