"""Panelga kirishni botda tasdiqlash (faqat adminlar). `/start alogin_<nonce>` → IP/brauzer ko'rsatiladi → Ruxsat/Rad."""

import time

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton as IB, Message

from .. import ui
from ..panel.auth import LOGIN_TTL

router = Router()


@router.message(CommandStart(deep_link=True), F.text.regexp(r"^/start alogin_"))
async def login_request(message: Message, command: CommandObject, store, settings):
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ Ruxsat yo'q")
        return
    nonce = (command.args or "")[len("alogin_"):]
    row = await store.login(nonce)
    if row is None or row["status"] != "pending" or time.time() - row["created_at"] > LOGIN_TTL:
        await message.answer("⌛ Kirish so'rovi eskirgan. Panelda sahifani yangilab, qayta urining.")
        return
    await message.answer(
        "🔐 <b>Admin panelga kirish so'rovi</b>\n\n"
        f"🌐 IP: <code>{row['ip']}</code>\n💻 Brauzer: <code>{(row['agent'] or '—')[:120]}</code>\n\n"
        "Bu siz bo'lsangiz ruxsat bering. Begona bo'lsa — <b>Rad etish</b>.",
        parse_mode="HTML",
        reply_markup=ui.inline([IB(text="✅ Ruxsat berish", callback_data=f"al:y:{nonce}", style="success"),
                                IB(text="❌ Rad etish", callback_data=f"al:n:{nonce}", style="danger")]))


@router.callback_query(F.data.startswith("al:"))
async def login_decision(callback: CallbackQuery, store, settings):
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    _, choice, nonce = callback.data.split(":", 2)
    row = await store.login(nonce)
    fresh = row is not None and time.time() - row["created_at"] <= LOGIN_TTL
    if choice == "y" and fresh and await store.move_login(nonce, "pending", "approved", callback.from_user.id):
        text = "✅ Kirishga ruxsat berildi. Brauzerga qayting."
    elif choice == "n" and await store.move_login(nonce, "pending", "denied", callback.from_user.id):
        await store.audit(callback.from_user.id, "panel_login_denied", f"ip={row['ip']}")
        text = "❌ So'rov rad etildi."
    else:
        text = "⌛ So'rov eskirgan yoki allaqachon ko'rib chiqilgan."
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=None)
