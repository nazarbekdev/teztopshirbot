"""
Karta to'lovini ko'rib chiqish — botdagi tugmalar va web panel UCHUN YAGONA yo'l.

Pul mantiqi bir joyda bo'lishi shart: ikki joyda yozilsa biri ikkinchisidan ajralib ketadi
(masalan, panel summa farqini mijozga aytmay qo'yadi). `Store.settle_payment` holatni bir
martalik o'tkazadi, shuning uchun ikki marta bosilgan tugma yoki ikki adminning bir vaqtdagi
qarori balansni ikki marta to'ldirmaydi.
"""

import logging

from .catalog import money
from .i18n import t

logger = logging.getLogger(__name__)

MIN_ADMIN_AMOUNT = 1_000
MAX_AMOUNT = 5_000_000


async def _tell_user(bot, user: dict, text: str) -> None:
    try:
        await bot.send_message(user["tg_id"], text, parse_mode="HTML")
    except Exception:
        logger.warning("To'lov natijasini yuborib bo'lmadi: %s", user["tg_id"])


async def approve(store, bot, payment_id: int, admin_id: int) -> dict | None:
    """Tasdiqlaydi, balansni to'ldiradi, mijozga xabar beradi. Allaqachon ko'rib chiqilgan bo'lsa None."""
    payment = await store.settle_payment(payment_id, "pending", "approved", admin_id=admin_id)
    if payment is None:
        return None
    await store.credit(payment["tg_id"], payment["amount"], "card_topup", f"payment:{payment_id}")
    user = await store.user(payment["tg_id"])
    lang = user.get("lang") or "uz"
    original = payment.get("original_amount")
    if original and original != payment["amount"]:
        text = t(lang, "pay_approved_edited", asked=money(original, lang), amount=money(payment["amount"], lang))
    else:
        text = t(lang, "pay_approved", amount=money(payment["amount"], lang))
    await _tell_user(bot, user, text)
    return payment


async def reject(store, bot, payment_id: int, admin_id: int) -> dict | None:
    payment = await store.settle_payment(payment_id, "pending", "rejected", admin_id=admin_id)
    if payment is None:
        return None
    user = await store.user(payment["tg_id"])
    await _tell_user(bot, user, t(user.get("lang") or "uz", "pay_rejected"))
    return payment


async def edit_amount(store, payment_id: int, amount: int) -> dict | None:
    """Kutilayotgan to'lov summasini tuzatadi (tasdiqlamaydi). Summa chegarada bo'lmasa None."""
    if not MIN_ADMIN_AMOUNT <= amount <= MAX_AMOUNT:
        return None
    return await store.edit_pending_amount(payment_id, amount)
