"""Buyurtma oqimi: haqiqiy Dispatcher, soxta Telegram sessiyasi."""

import datetime

import pytest_asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import SendMessage
from aiogram.types import CallbackQuery, Chat, Message, Update, User

from app.handlers import admin, balance, order, start


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []

    async def close(self):
        pass

    async def stream_content(self, *a, **kw):
        yield b""

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, SendMessage):
            return Message(message_id=len(self.calls), date=datetime.datetime.now(),
                           chat=Chat(id=method.chat_id, type="private"), text=method.text)
        return True

    def texts(self):
        return [m.text for m in self.calls if isinstance(m, SendMessage)]

    def last_markup(self):
        for m in reversed(self.calls):
            if isinstance(m, SendMessage) and m.reply_markup is not None:
                return m.reply_markup
        return None


USER = User(id=1, is_bot=False, first_name="Ali")
CHAT = Chat(id=1, type="private")


class Env:
    def __init__(self, store, session, dp, bot):
        self.store, self.session, self.dp, self.bot = store, session, dp, bot
        self.n = 0

    async def say(self, text):
        self.n += 1
        msg = Message(message_id=100 + self.n, date=datetime.datetime.now(), chat=CHAT, from_user=USER, text=text)
        await self.dp.feed_update(self.bot, Update(update_id=self.n, message=msg))

    async def press(self, data):
        self.n += 1
        msg = Message(message_id=200 + self.n, date=datetime.datetime.now(), chat=CHAT, from_user=USER, text="x")
        cb = CallbackQuery(id=str(self.n), from_user=USER, chat_instance="c", message=msg, data=data)
        await self.dp.feed_update(self.bot, Update(update_id=self.n, callback_query=cb))


@pytest_asyncio.fixture
async def env(store):
    class Settings:
        admin_ids = [1]
        card_number, card_holder, click_enabled = "8600 0000 0000 0000", "Ali", False
        support_username = ""

    session = FakeSession()
    bot = Bot("123456:TEST", session=session)
    dp = Dispatcher(storage=MemoryStorage())
    dp.workflow_data.update(store=store, settings=Settings(), api=None, notify_admins=None)
    for module in (start, order, balance, admin):
        module.router._parent_router = None   # modul darajasidagi router: har testda yangi Dispatcher
        dp.include_router(module.router)
    return Env(store, session, dp, bot)


async def test_taqdimot_toliq_oqim(env):
    await env.say("/start")
    await env.store.credit(1, 10_000, "topup")
    await env.say("📊 Taqdimot")
    await env.say("Sun'iy intellekt ta'limda")
    await env.press("c:15")
    await env.press("c:uz")
    await env.press("skip")                       # taqdimotchi ismi ixtiyoriy
    assert "4 500" in env.session.texts()[-1]     # tasdiq ekrani narxni ko'rsatadi
    await env.press("ok")
    rows = await env.store.orders_by_status("queued")
    assert len(rows) == 1 and rows[0]["service"] == "taqdimot"
    import json
    assert json.loads(rows[0]["params"]) == {"topic": "Sun'iy intellekt ta'limda", "slides": 15, "language": "uz"}
    assert await env.store.balance(1) == 5_500


async def test_ikki_marta_bosilgan_tasdiq_bitta_buyurtma(env):
    await env.say("/start")
    await env.store.credit(1, 20_000, "topup")
    await env.say("❓ Test")
    await env.say("Algebra asoslari")
    await env.press("c:10")
    await env.press("c:uz")
    await env.press("ok")
    await env.press("ok")
    assert len(await env.store.orders_by_status("queued")) == 1
    assert await env.store.balance(1) == 17_500


async def test_balans_yetmasa_toldirish_taklif_qilinadi(env):
    await env.say("/start")
    await env.say("🧩 Krossvord")
    await env.say("Geografiya")
    await env.press("c:10")
    await env.press("c:uz")
    assert "Yetmaydi" in env.session.texts()[-1]
    await env.press("ok")                         # tugma yo'q, holat confirming — yechilmaydi
    assert await env.store.balance(1) == 0
    assert await env.store.orders_by_status("queued") == []


async def test_qisqa_mavzu_qabul_qilinmaydi_va_menyu_oqimni_uzadi(env):
    await env.say("/start")
    await env.say("📊 Taqdimot")
    await env.say("abc")                          # 5 belgidan kam
    assert "belgi" in env.session.texts()[-1]
    await env.say("💰 Balans")                    # menyu tugmasi mavzu bo'lib ketmasligi kerak
    assert "Balansingiz" in env.session.texts()[-1]
