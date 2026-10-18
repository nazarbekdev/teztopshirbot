"""
Kanalga a'zolik tekshiruvi.

Qoidalar:
  · Bot kanalda ADMIN bo'lishi kerak, aks holda Telegram a'zolikni ko'rsatmaydi. Tekshiruv xato bersa
    (bot admin emas, kanal topilmadi, Telegram javob bermadi) foydalanuvchi ZAHARLANMAYDI: tekshiruv
    o'tkazib yuboriladi va adminga bir soatda bir marta ogohlantirish ketadi — noto'g'ri sozlama
    hamma mijozni bloklab qo'ymasligi uchun.
  · Ijobiy natija 10 daqiqa keshlanadi (har xabarda Telegram'ga so'rov ketmasin); salbiy natija
    keshlanmaydi: foydalanuvchi a'zo bo'lib «A'zo bo'ldim» bossa darhol o'tadi.
  · Adminlar tekshiruvdan ozod.
"""

import logging
import time

from aiogram.enums import ChatMemberStatus

logger = logging.getLogger(__name__)

MEMBER_STATUSES = {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
CACHE_TTL = 600
_cache: dict[int, float] = {}


def forget(user_id: int) -> None:
    _cache.pop(user_id, None)


async def is_member(bot, settings, user_id: int, alert=None) -> bool:
    channel = settings.required_channel
    if not channel or user_id in settings.admin_ids:
        return True
    if _cache.get(user_id, 0) > time.monotonic():
        return True
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
    except Exception as e:
        logger.warning("Kanal a'zoligini tekshirib bo'lmadi (%s): %s", channel, e)
        if alert:
            await alert("sub_check_failed",
                        f"🟠 <b>Kanal a'zoligi tekshirilmayapti</b> ({channel}): <code>{str(e)[:150]}</code>\n"
                        "Bot kanalda admin ekanini tekshiring. Hozircha tekshiruv o'tkazib yuborilmoqda.")
        return True
    if member.status in MEMBER_STATUSES:
        _cache[user_id] = time.monotonic() + CACHE_TTL
        return True
    return False
