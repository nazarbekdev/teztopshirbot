"""Promokod tunneli: kodni kiritadi → bitta bepul buyurtma huquqi (kupon) beriladi."""

import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton as IB, Message

from .. import ui
from ..catalog import SERVICES, pick
from ..i18n import t

router = Router()

ERRORS = {"invalid": "promo_invalid", "expired": "promo_expired", "limit": "promo_limit",
          "used": "promo_used", "has_active": "promo_has_active"}


class Promo(StatesGroup):
    code = State()


def normalize(text: str) -> str:
    """Kod katta-kichik harfga va bo'sh joyga befarq: «tez start» = TEZSTART."""
    return re.sub(r"[\s\-_]+", "", text or "").upper()[:40]


@router.message(F.text.in_(ui.PROMO_TEXTS))
@router.message(Command("promo"))
async def ask_code(message: Message, state: FSMContext, lang):
    await state.clear()
    await state.set_state(Promo.code)
    await message.answer(t(lang, "promo_ask"), parse_mode="HTML",
                         reply_markup=ui.inline([ui.cancel_button(lang)]))


@router.message(Promo.code, F.text & ~F.text.startswith("/") & ~F.text.in_(ui.MENU_TEXTS))
async def got_code(message: Message, state: FSMContext, store, lang):
    code = normalize(message.text)
    result, voucher = await store.redeem(code, message.from_user.id)
    if result != "ok":
        # Noto'g'ri kodda holat saqlanadi: foydalanuvchi qayta yozishi mumkin (xato harf)
        if result == "invalid":
            await message.answer(t(lang, ERRORS[result]))
        else:
            await state.clear()
            await message.answer(t(lang, ERRORS[result]), reply_markup=ui.main_menu(lang))
        return
    await state.clear()
    services = "\n".join(f"• {SERVICES[s].emoji} {pick(SERVICES[s].title, lang)}" for s in voucher["services"] if s in SERVICES)
    await message.answer(t(lang, "promo_ok", services=services), parse_mode="HTML", reply_markup=ui.main_menu(lang))
