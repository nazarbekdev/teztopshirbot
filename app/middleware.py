"""Onboarding darvozasi: til tanlanmagan yoki shartlarga rozilik bildirilmagan foydalanuvchi
boshqa hech narsa qila olmaydi (faqat /start, til va rozilik tugmalari)."""

import logging

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from . import ui
from .i18n import t

logger = logging.getLogger(__name__)

FREE_COMMANDS = ("/start", "/privacy")
FREE_CALLBACKS = ("lang:", "consent:")
ADMIN_CALLBACKS = ("pa:", "pr:", "pe:", "al:")


class Onboarding(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = event.from_user
        if user is None or user.is_bot:
            return await handler(event, data)
        store, settings = data["store"], data["settings"]
        row = await store.touch_user(user.id, user.full_name, user.username)
        data["lang"] = row.get("lang")

        if isinstance(event, Message):
            if (event.text or "").startswith(FREE_COMMANDS):
                return await handler(event, data)
            target = event
        elif isinstance(event, CallbackQuery):
            payload = event.data or ""
            if payload.startswith(FREE_CALLBACKS):
                return await handler(event, data)
            if user.id in settings.admin_ids and payload.startswith(ADMIN_CALLBACKS):
                return await handler(event, data)
            target = event.message
        else:
            return await handler(event, data)

        # Admin chek summasini yozayotgan paytda (AdminEdit holati) darvoza o'tkazib yuboriladi
        state = data.get("state")
        if user.id in settings.admin_ids and state is not None:
            current = await state.get_state()
            if current and current.startswith("AdminEdit"):
                return await handler(event, data)

        lang = row.get("lang")
        if not lang:
            if isinstance(event, CallbackQuery):
                await event.answer()
            await target.answer(t(None, "lang_prompt"), reply_markup=ui.lang_keyboard())
            return None
        if row.get("consent_version") != ui.CONSENT_VERSION:
            if isinstance(event, CallbackQuery):
                await event.answer()
            await target.answer(t(lang, "consent_needed") + "\n\n" + t(lang, "consent_intro"),
                                parse_mode="HTML", reply_markup=ui.consent_keyboard(lang))
            return None
        data["lang"] = lang
        return await handler(event, data)
