"""Balans va to'ldirish: Click (avtomatik) yoki karta (chek + admin tasdig'i)."""

import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton as IB, Message

from .. import ui
from ..catalog import money

logger = logging.getLogger(__name__)
router = Router()

MIN_TOPUP = 3_000
MAX_TOPUP = 5_000_000
AMOUNTS = (5_000, 10_000, 20_000, 50_000, 100_000)


class Topup(StatesGroup):
    amount = State()
    receipt = State()


def _amount_kb():
    rows = [[IB(text=money(a), callback_data=f"ta:{a}") for a in AMOUNTS[i:i + 2]] for i in range(0, len(AMOUNTS), 2)]
    rows.append([IB(text="✏️ Boshqa summa", callback_data="ta:other")])
    rows.append([ui.cancel_button()])
    return ui.inline(*rows)


@router.message(F.text == ui.BALANCE)
async def show_balance(message: Message, state: FSMContext, store):
    await state.clear()
    balance = await store.balance(message.from_user.id)
    await message.answer(
        f"💰 <b>Balansingiz: {money(balance)}</b>\n\nBuyurtma narxi balansdan yechiladi.",
        parse_mode="HTML",
        reply_markup=ui.inline([IB(text="➕ Balansni to'ldirish", callback_data="topup:0", style="success")]),
    )


@router.callback_query(F.data.startswith("topup:"))
async def topup_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    need = int(callback.data.split(":")[1])
    hint = f"\nKerakli summa: <b>{money(need)}</b>" if need else ""
    await callback.message.answer(f"💳 <b>Qancha to'ldirasiz?</b>{hint}", parse_mode="HTML", reply_markup=_amount_kb())


@router.callback_query(F.data.startswith("ta:"))
async def topup_amount(callback: CallbackQuery, state: FSMContext, settings):
    value = callback.data[3:]
    await callback.answer()
    if value == "other":
        await state.set_state(Topup.amount)
        await callback.message.answer(f"Summani yozing ({money(MIN_TOPUP)} – {money(MAX_TOPUP)}):")
        return
    await _choose_method(callback.message, int(value), settings)


@router.message(Topup.amount, F.text & ~F.text.in_(ui.MENU_TEXTS) & ~F.text.startswith("/"))
async def topup_custom(message: Message, state: FSMContext, settings):
    digits = "".join(ch for ch in message.text if ch.isdigit())
    amount = int(digits) if digits else 0
    if not MIN_TOPUP <= amount <= MAX_TOPUP:
        await message.answer(f"Summa {money(MIN_TOPUP)} dan {money(MAX_TOPUP)} gacha bo'lishi kerak. Qayta yozing.")
        return
    await state.clear()
    await _choose_method(message, amount, settings)


async def _choose_method(target: Message, amount: int, settings) -> None:
    rows = []
    if settings.click_enabled:
        rows.append([IB(text="🔵 Click (avtomatik)", callback_data=f"pm:click:{amount}", style="primary")])
    if settings.card_number:
        rows.append([IB(text="💳 Karta orqali (chek)", callback_data=f"pm:card:{amount}", style="success")])
    rows.append([ui.cancel_button()])
    if len(rows) == 1:
        await target.answer("To'lov usullari hozircha sozlanmagan. Administratorga murojaat qiling.")
        return
    await target.answer(f"💵 To'ldirish summasi: <b>{money(amount)}</b>\nTo'lov usulini tanlang:",
                        parse_mode="HTML", reply_markup=ui.inline(*rows))


@router.callback_query(F.data.startswith("pm:"))
async def method_chosen(callback: CallbackQuery, state: FSMContext, store, settings):
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
        await callback.message.answer(
            f"🔵 <b>Click orqali to'lash</b>\nSumma: <b>{money(amount)}</b>\n\n"
            "To'lov tasdiqlangach balansingiz avtomatik to'ladi.",
            parse_mode="HTML", reply_markup=ui.inline([IB(text="💳 To'lash", url=url)]),
        )
    elif method == "card" and settings.card_number:
        await state.set_state(Topup.receipt)
        await state.update_data(amount=amount)
        await callback.message.answer(
            f"💳 <b>Karta orqali to'lash</b>\n\n"
            f"Summa: <b>{money(amount)}</b>\nKarta: <code>{settings.card_number}</code>\n"
            + (f"Qabul qiluvchi: {settings.card_holder}\n" if settings.card_holder else "")
            + "\nO'tkazgach <b>chek rasmini</b> shu yerga yuboring. Administrator tekshirib, balansni to'ldiradi.",
            parse_mode="HTML", reply_markup=ui.inline([ui.cancel_button()]),
        )


@router.message(Topup.receipt, F.photo)
async def receipt_photo(message: Message, state: FSMContext, store, notify_admins):
    data = await state.get_data()
    await state.clear()
    amount = data["amount"]
    pid = await store.new_payment(message.from_user.id, amount, "card", "pending", message.photo[-1].file_id)
    await message.answer("✅ Chek qabul qilindi. Administrator tekshirgach, balansingiz to'ladi va sizga xabar beraman.",
                         reply_markup=ui.main_menu())
    await notify_admins(
        photo=message.photo[-1].file_id,
        text=(f"💳 <b>Yangi to'lov #{pid}</b>\n👤 {message.from_user.full_name}"
              f" (@{message.from_user.username or '—'})\n🆔 <code>{message.from_user.id}</code>\n"
              f"💵 {money(amount)}"),
        markup=ui.inline([IB(text="✅ Tasdiqlash", callback_data=f"pa:{pid}", style="success"),
                          IB(text="❌ Rad etish", callback_data=f"pr:{pid}", style="danger")]),
    )


@router.message(Topup.receipt)
async def receipt_not_photo(message: Message):
    await message.answer("Iltimos, chek <b>rasmini</b> yuboring (fayl emas, rasm).", parse_mode="HTML")


@router.callback_query(F.data.startswith(("pa:", "pr:")))
async def admin_decision(callback: CallbackQuery, store, settings):
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    action, raw = callback.data.split(":")
    pid = int(raw)
    approve = action == "pa"
    payment = await store.settle_payment(pid, "pending", "approved" if approve else "rejected",
                                         admin_id=callback.from_user.id)
    if payment is None:
        await callback.answer("Bu to'lov allaqachon ko'rib chiqilgan", show_alert=True)
        return
    if approve:
        await store.credit(payment["tg_id"], payment["amount"], "card_topup", f"payment:{pid}")
        text, mark = (f"✅ To'lovingiz tasdiqlandi: <b>+{money(payment['amount'])}</b>. Balansingiz to'ldi.",
                      f"✅ Tasdiqlandi ({callback.from_user.full_name})")
    else:
        text, mark = ("❌ To'lovingiz tasdiqlanmadi. Chek noto'g'ri bo'lsa, qayta yuboring yoki administratorga yozing.",
                      f"❌ Rad etildi ({callback.from_user.full_name})")
    await callback.answer(mark)
    await callback.message.edit_caption(caption=(callback.message.caption or "") + f"\n\n{mark}", reply_markup=None)
    try:
        await callback.bot.send_message(payment["tg_id"], text, parse_mode="HTML")
    except Exception:
        logger.warning("To'lov natijasini yuborib bo'lmadi: %s", payment["tg_id"])
