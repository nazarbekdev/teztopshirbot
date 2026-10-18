"""Balans va to'ldirish: Click (avtomatik) yoki karta (chek + admin tasdig'i, summani tahrirlash)."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton as IB, Message

from .. import payments, ui
from ..catalog import money
from ..i18n import t

logger = logging.getLogger(__name__)
router = Router()

MIN_TOPUP = 3_000
MAX_TOPUP = 5_000_000
AMOUNTS = (5_000, 10_000, 20_000, 50_000, 100_000)


class Topup(StatesGroup):
    amount = State()
    receipt = State()


class AdminEdit(StatesGroup):
    amount = State()


def _amount_kb(lang: str):
    rows = [[IB(text=money(a, lang), callback_data=f"ta:{a}") for a in AMOUNTS[i:i + 2]] for i in range(0, len(AMOUNTS), 2)]
    rows.append([IB(text=t(lang, "btn_other_amount"), callback_data="ta:other")])
    rows.append([ui.cancel_button(lang)])
    return ui.inline(*rows)


@router.message(F.text.in_(ui.BALANCE_TEXTS))
async def show_balance(message: Message, state: FSMContext, store, lang):
    await state.clear()
    balance = await store.balance(message.from_user.id)
    await message.answer(
        t(lang, "balance_screen", amount=money(balance, lang)), parse_mode="HTML",
        reply_markup=ui.inline([IB(text=t(lang, "btn_topup"), callback_data="topup:0", style="success")]))


@router.callback_query(F.data.startswith("topup:"))
async def topup_start(callback: CallbackQuery, state: FSMContext, lang):
    await state.clear()
    await callback.answer()
    need = int(callback.data.split(":")[1])
    hint = t(lang, "topup_hint", need=money(need, lang)) if need else ""
    await callback.message.answer(t(lang, "topup_howmuch", hint=hint), parse_mode="HTML", reply_markup=_amount_kb(lang))


@router.callback_query(F.data.startswith("ta:"))
async def topup_amount(callback: CallbackQuery, state: FSMContext, settings, lang):
    value = callback.data[3:]
    await callback.answer()
    if value == "other":
        await state.set_state(Topup.amount)
        await callback.message.answer(t(lang, "type_amount", lo=money(MIN_TOPUP, lang), hi=money(MAX_TOPUP, lang)))
        return
    await _choose_method(callback.message, int(value), settings, lang)


@router.message(Topup.amount, F.text & ~F.text.in_(ui.MENU_TEXTS) & ~F.text.startswith("/"))
async def topup_custom(message: Message, state: FSMContext, settings, lang):
    digits = "".join(ch for ch in message.text if ch.isdigit())
    amount = int(digits) if digits else 0
    if not MIN_TOPUP <= amount <= MAX_TOPUP:
        await message.answer(t(lang, "amount_range", lo=money(MIN_TOPUP, lang), hi=money(MAX_TOPUP, lang)))
        return
    await state.clear()
    await _choose_method(message, amount, settings, lang)


async def _choose_method(target: Message, amount: int, settings, lang: str) -> None:
    rows = []
    if settings.click_enabled:
        rows.append([IB(text=t(lang, "btn_click"), callback_data=f"pm:click:{amount}", style="primary")])
    if settings.card_number:
        rows.append([IB(text=t(lang, "btn_card"), callback_data=f"pm:card:{amount}", style="success")])
    if not rows:
        await target.answer(t(lang, "no_methods"))
        return
    rows.append([ui.cancel_button(lang)])
    await target.answer(t(lang, "choose_method", amount=money(amount, lang)), parse_mode="HTML",
                        reply_markup=ui.inline(*rows))


@router.callback_query(F.data.startswith("pm:"))
async def method_chosen(callback: CallbackQuery, state: FSMContext, store, settings, lang):
    _, method, raw = callback.data.split(":")
    amount = int(raw)
    await callback.answer()
    if not MIN_TOPUP <= amount <= MAX_TOPUP:
        return
    if method == "click" and settings.click_enabled:
        pid = await store.new_payment(callback.from_user.id, amount, "click", "pending")
        url = (f"https://my.click.uz/services/pay?service_id={settings.click_service_id}"
               f"&merchant_id={settings.click_merchant_id}&amount={amount}"
               f"&transaction_param={pid}&merchant_trans_id={pid}")
        await callback.message.answer(t(lang, "click_screen", amount=money(amount, lang)), parse_mode="HTML",
                                      reply_markup=ui.inline([IB(text=t(lang, "btn_pay"), url=url)]))
    elif method == "card" and settings.card_number:
        await state.set_state(Topup.receipt)
        await state.update_data(amount=amount)
        holder = t(lang, "card_holder", name=settings.card_holder) if settings.card_holder else ""
        await callback.message.answer(
            t(lang, "card_screen", amount=money(amount, lang), card=settings.card_number, holder=holder),
            parse_mode="HTML", reply_markup=ui.inline([ui.cancel_button(lang)]))


def card_caption(payment: dict, user: dict) -> str:
    """Admin kartasi (o'zbekcha). Summa tahrirlangan bo'lsa, asl summa ham ko'rinadi."""
    amount = f"💵 {money(payment['amount'])}"
    if payment.get("original_amount") and payment["original_amount"] != payment["amount"]:
        amount += f" ✏️ (mijoz yozgan: {money(payment['original_amount'])})"
    return (f"💳 <b>Yangi to'lov #{payment['id']}</b>\n👤 {user['name']}"
            f" (@{user.get('username') or '—'})\n🆔 <code>{user['tg_id']}</code>\n{amount}")


def card_markup(pid: int):
    return ui.inline([IB(text="✅ Tasdiqlash", callback_data=f"pa:{pid}", style="success"),
                      IB(text="❌ Rad etish", callback_data=f"pr:{pid}", style="danger")],
                     [IB(text="✏️ Summani tahrirlash", callback_data=f"pe:{pid}", style="primary")])


@router.message(Topup.receipt, F.photo)
async def receipt_photo(message: Message, state: FSMContext, store, notify_admins, lang):
    data = await state.get_data()
    await state.clear()
    pid = await store.new_payment(message.from_user.id, data["amount"], "card", "pending", message.photo[-1].file_id)
    await message.answer(t(lang, "receipt_ok"), reply_markup=ui.main_menu(lang))
    payment, user = await store.payment(pid), await store.user(message.from_user.id)
    await notify_admins(photo=message.photo[-1].file_id, text=card_caption(payment, user), markup=card_markup(pid))


@router.message(Topup.receipt)
async def receipt_not_photo(message: Message, lang):
    await message.answer(t(lang, "receipt_not_photo"), parse_mode="HTML")


# ── admin: tasdiqlash / rad etish / summani tahrirlash ───────────────────

@router.callback_query(F.data.startswith(("pa:", "pr:")))
async def admin_decision(callback: CallbackQuery, store, settings):
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    action, raw = callback.data.split(":")
    pid = int(raw)
    approve = action == "pa"
    decide = payments.approve if approve else payments.reject
    payment = await decide(store, callback.bot, pid, callback.from_user.id)
    if payment is None:
        await callback.answer("Bu to'lov allaqachon ko'rib chiqilgan", show_alert=True)
        return
    await store.audit(callback.from_user.id, "payment_approve" if approve else "payment_reject",
                      f"#{pid} {payment['amount']} (bot)")
    user = await store.user(payment["tg_id"])
    mark = (f"✅ Tasdiqlandi ({callback.from_user.full_name}): {money(payment['amount'])}" if approve
            else f"❌ Rad etildi ({callback.from_user.full_name})")
    await callback.answer(mark[:150])
    await callback.message.edit_caption(caption=card_caption(payment, user) + f"\n\n{mark}", parse_mode="HTML",
                                        reply_markup=None)


@router.callback_query(F.data.startswith("pe:"))
async def admin_edit_start(callback: CallbackQuery, state: FSMContext, store, settings):
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    pid = int(callback.data[3:])
    payment = await store.payment(pid)
    if payment is None or payment["status"] != "pending":
        await callback.answer("Bu to'lov allaqachon ko'rib chiqilgan", show_alert=True)
        return
    await state.set_state(AdminEdit.amount)
    await state.update_data(pid=pid, chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    await callback.answer()
    await callback.message.answer(f"✏️ #{pid} uchun chekdagi <b>haqiqiy summani</b> yozing "
                                  f"({money(payment['amount'])} yozilgan):", parse_mode="HTML")


@router.message(AdminEdit.amount, F.text & ~F.text.startswith("/"))
async def admin_edit_amount(message: Message, state: FSMContext, store, settings):
    if message.from_user.id not in settings.admin_ids:
        return
    digits = "".join(ch for ch in message.text if ch.isdigit())
    amount = int(digits) if digits else 0
    if not payments.MIN_ADMIN_AMOUNT <= amount <= payments.MAX_AMOUNT:
        await message.answer(f"Summa {money(payments.MIN_ADMIN_AMOUNT)} dan {money(payments.MAX_AMOUNT)} gacha "
                             "bo'lishi kerak. Qayta yozing.")
        return
    data = await state.get_data()
    await state.clear()
    payment = await payments.edit_amount(store, data["pid"], amount)
    if payment:
        await store.audit(message.from_user.id, "payment_edit", f"#{data['pid']} {payment['original_amount']}→{amount} (bot)")
    if payment is None:
        await message.answer("Bu to'lov allaqachon ko'rib chiqilgan.")
        return
    user = await store.user(payment["tg_id"])
    try:
        await message.bot.edit_message_caption(chat_id=data["chat_id"], message_id=data["message_id"],
                                               caption=card_caption(payment, user), parse_mode="HTML",
                                               reply_markup=card_markup(payment["id"]))
    except Exception:
        logger.warning("Admin kartasini yangilab bo'lmadi (#%s)", payment["id"])
    await message.answer(f"✅ Summa yangilandi: <b>{money(amount)}</b>. Endi kartadagi tugma orqali tasdiqlang.",
                         parse_mode="HTML")
