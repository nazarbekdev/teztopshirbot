"""
Chatni toza saqlash: savol-javob oqimidagi oraliq xabarlar (savollar, foydalanuvchining javoblari, xato
izohlari, shablon karuseli, reja ko'rinishi) keyingi qadamga o'tilganda O'CHIRILADI. Chatda faqat natija qoladi
(buyurtma qabul qilindi, tayyor fayl va h.k.).

Xabar ID'lari FSM ma'lumotida (`trash`) saqlanadi, ya'ni bot qayta ishga tushsa ham tozalash ishlayveradi.
Telegram shaxsiy chatda foydalanuvchining xabarini ham o'chirishga ruxsat beradi; o'chirib bo'lmasa (48 soatdan
eski, allaqachon o'chgan) xato yutiladi — oqim buziladi emas, shunchaki xabar qoladi.
"""

import logging

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

logger = logging.getLogger(__name__)


async def track(state: FSMContext, *message_ids: int) -> None:
    ids = [i for i in message_ids if i]
    if not ids:
        return
    trash = (await state.get_data()).get("trash") or []
    await state.update_data(trash=trash + [i for i in ids if i not in trash])


async def say(target: Message, state: FSMContext, text: str, **kwargs) -> Message:
    """Xabar yuboradi va keyin o'chirish uchun belgilab qo'yadi."""
    sent = await target.answer(text, **kwargs)
    await track(state, sent.message_id)
    return sent


async def sweep(bot, chat_id: int, state: FSMContext) -> None:
    """Belgilangan xabarlarning hammasini o'chiradi."""
    ids = (await state.get_data()).get("trash") or []
    if not ids:
        return
    await state.update_data(trash=[])
    try:
        await bot.delete_messages(chat_id, ids)
        return
    except Exception:
        pass
    for message_id in ids:                       # ommaviy o'chirish ketmasa — bittalab
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception:
            pass


async def reset(state: FSMContext, bot, chat_id: int) -> None:
    """Oqimni to'xtatadi: oraliq xabarlarni o'chiradi va holatni tozalaydi."""
    await sweep(bot, chat_id, state)
    await state.clear()


async def drop(message: Message) -> None:
    """Bitta xabarni o'chiradi (bo'lmasa — tugmalarini olib tashlaydi, xabar qoladi)."""
    try:
        await message.delete()
    except Exception:
        try:
            await message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
