"""
Kanalga a'zolik tekshiruvi.

Qoidalar:
  · A'zolik MAJBURIY: tekshirib bo'lmasa ham (bot kanalda admin emas, kanal topilmadi, Telegram javob
    bermadi) foydalanuvchi O'TKAZILMAYDI. Ilgari xatoda "o'tkazib yuborish" (fail-open) bor edi va u
    a'zo bo'lmaganlarni ichkariga kiritib yuborardi. Noto'g'ri sozlama hamma uchun bloklashga olib
    kelmasligi uchun adminga soatiga bir marta ogohlantirish ketadi.
  · Ijobiy natija 2 daqiqa keshlanadi (har xabarda Telegram'ga so'rov ketmasin, lekin kanaldan chiqib
    ketgan odam uzoq vaqt o'tib yurmasin); salbiy natija keshlanmaydi: a'zo bo'lib «A'zo bo'ldim»
    bossa darhol o'tadi.
  · Adminlar (`ADMIN_IDS`) tekshiruvdan ozod — o'z hisobingiz bilan sinasangiz kanalni so'ramaydi.
    Adminni ham tekshirib ko'rish uchun `.env` da `CHANNEL_CHECK_ADMINS=1`.
"""

import logging
import time

from aiogram.enums import ChatMemberStatus

logger = logging.getLogger(__name__)

MEMBER_STATUSES = {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
CACHE_TTL = 120
_cache: dict[int, float] = {}


def forget(user_id: int) -> None:
    _cache.pop(user_id, None)


async def is_member(bot, settings, user_id: int, alert=None) -> bool:
    channel = settings.required_channel
    if not channel:
        return True
    if user_id in settings.admin_ids and not getattr(settings, "channel_check_admins", False):
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
                        "Bot kanalda admin ekanini tekshiring. Tekshiruv o'tmaguncha foydalanuvchilar bloklanadi.")
        return False
    if member.status in MEMBER_STATUSES:
        _cache[user_id] = time.monotonic() + CACHE_TTL
        return True
    return False
