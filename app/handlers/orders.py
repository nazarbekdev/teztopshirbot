"""Buyurtmalarim va tayyor faylni qayta yuklab olish."""

import json
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton as IB, Message

from .. import ui
from ..cleanup import reset
from ..api import PartnerError
from ..catalog import SERVICES, pick
from ..i18n import t

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text.in_(ui.ORDERS_TEXTS))
async def my_orders(message: Message, state: FSMContext, store, lang):
    await reset(state, message.bot, message.chat.id)
    rows = await store.user_orders(message.from_user.id)
    if not rows:
        await message.answer(t(lang, "no_orders"))
        return
    lines = [t(lang, "orders_title")]
    buttons = []
    for o in rows:
        s = SERVICES.get(o["service"])
        title = f"{s.emoji} {pick(s.title, lang)}" if s else o["service"]
        lines.append(f"#{o['id']} {title} — {t(lang, 'st_' + o['status'])}")
        if o["status"] == "succeeded" and o["delivered"] and len(buttons) < 5:
            buttons.append([IB(text=t(lang, "btn_download", id=o["id"]), callback_data=f"dl:{o['id']}", style="primary")])
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=ui.inline(*buttons) if buttons else None)


@router.callback_query(F.data.startswith("dl:"))
async def download(callback: CallbackQuery, store, api, lang):
    order = await store.order(int(callback.data[3:]))
    if order is None or order["tg_id"] != callback.from_user.id:
        await callback.answer(t(lang, "dl_missing"), show_alert=True)
        return
    if order["status"] != "succeeded":
        await callback.answer(t(lang, "dl_not_ready"), show_alert=True)
        return
    await callback.answer()
    sent = await _send_from_api(callback, order, api)
    if not sent:
        sent = await _send_from_telegram(callback, order)
    if not sent:
        await callback.message.answer(t(lang, "dl_expired"))


async def _send_from_api(callback: CallbackQuery, order: dict, api) -> bool:
    """Hamkor API'dan (fayl 7 kun saqlanadi). Muddat tugagan bo'lsa False — Telegram nusxasiga o'tiladi."""
    try:
        remote = await api.get_order(order["partner_order_id"])
        files = (remote.get("result") or {}).get("files") or []
        if not files:
            return False
        for f in files:
            data = await api.download(f["id"])
            await callback.message.answer_document(BufferedInputFile(data, filename=f.get("name") or f"{f['id']}.bin"))
        return True
    except PartnerError as e:
        logger.info("Qayta yuklash: hamkor fayli yo'q (%s) — Telegram nusxasi sinab ko'riladi", e)
        return False
    except Exception:
        logger.exception("Qayta yuklashda kutilmagan xato (#%s)", order["id"])
        return False


async def _send_from_telegram(callback: CallbackQuery, order: dict) -> bool:
    """Yetkazishda saqlangan Telegram `file_id` lari: muddatsiz ishlaydi."""
    file_ids = json.loads(order["tg_files"]) if order.get("tg_files") else []
    for file_id in file_ids:
        await callback.message.answer_document(file_id)
    return bool(file_ids)
