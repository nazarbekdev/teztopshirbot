"""Bot oqimlari: haqiqiy Dispatcher + SQLite FSM + onboarding, soxta Telegram sessiyasi."""

import datetime
import json
from types import SimpleNamespace

import pytest_asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import EditMessageMedia, GetChatMember, SendDocument, SendMessage, SendPhoto
from aiogram.types import CallbackQuery, Chat, ChatMemberLeft, ChatMemberMember, Message, PhotoSize, Update, User

from app import subscription

from app.api import PartnerError
from app.fsm_storage import SqliteStorage
from app.handlers import admin, balance, order, orders, promo, start
from app.middleware import Onboarding

CUSTOMER = User(id=5, is_bot=False, first_name="Ali")
ADMIN = User(id=1, is_bot=False, first_name="Admin")


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.members: set[int] = set()
        self.member_error = False

    async def close(self):
        pass

    async def stream_content(self, *a, **kw):
        yield b""

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, GetChatMember):
            if self.member_error:
                raise RuntimeError("bot kanalda admin emas")
            user = User(id=method.user_id, is_bot=False, first_name="u")
            return (ChatMemberMember(user=user) if method.user_id in self.members
                    else ChatMemberLeft(user=user))
        if isinstance(method, (SendPhoto, EditMessageMedia)):
            chat_id = getattr(method, "chat_id", 0) or 0
            return Message(message_id=len(self.calls), date=datetime.datetime.now(), chat=Chat(id=chat_id, type="private"),
                           photo=[PhotoSize(file_id=f"tgphoto{len(self.calls)}", file_unique_id="u", width=1, height=1)])
        if isinstance(method, (SendMessage, SendDocument)):
            return Message(message_id=len(self.calls), date=datetime.datetime.now(),
                           chat=Chat(id=method.chat_id, type="private"), text=getattr(method, "text", None))
        return True

    def texts(self, chat_id=None):
        return [m.text for m in self.calls if isinstance(m, SendMessage) and (chat_id is None or m.chat_id == chat_id)]

    def documents(self, chat_id=None):
        return [m for m in self.calls if isinstance(m, SendDocument) and (chat_id is None or m.chat_id == chat_id)]


TEMPLATES = [("corporate_blue", None), ("econ_ledger", "econ"), ("med_clinic", "med"), ("it_terminal", "it")]


class FakeApi:
    def __init__(self):
        self.remote = {"result": {"files": [{"id": "fil_1", "name": "a.docx"}]}}
        self.expired = False
        self.templates_fail = False
        self.template_calls = []
        self.preview_calls = []

    async def templates(self, subject="", topic=""):
        self.template_calls.append((subject, topic))
        if self.templates_fail:
            raise PartnerError(503, "unavailable")
        wanted = "econ" if "iqtisod" in subject.lower() else None
        order = sorted(TEMPLATES, key=lambda x: 0 if wanted and x[1] == wanted else 1)
        meta = {"econ": {"id": "econ", "emoji": "📈", "name": {"uz": "Iqtisodiyot", "ru": "Экономика", "en": "Economics"}}}
        return {"object": "list", "detected_direction": meta.get(wanted), "data": [
            {"id": tid, "name": {"uz": f"{tid} uz", "ru": f"{tid} ru", "en": f"{tid} en"},
             "direction": meta.get(d), "slides": [10, 15, 20, 25, 30], "preview_url": f"https://x/{tid}"}
            for tid, d in order]}

    async def template_preview(self, template_id):
        self.preview_calls.append(template_id)
        return b"\x89PNG"

    async def get_order(self, order_id):
        if self.expired:
            raise PartnerError(410, "file_expired")
        return self.remote

    async def download(self, file_id):
        return b"DATA"


class Env:
    def __init__(self, store, session, dp, bot, admin_notes, api):
        self.store, self.session, self.dp, self.bot, self.admin_notes, self.api = store, session, dp, bot, admin_notes, api
        self.n = 0

    async def say(self, text, user=CUSTOMER, photo=False):
        self.n += 1
        extra = {"photo": [PhotoSize(file_id="rcpt", file_unique_id="u", width=1, height=1)]} if photo else {"text": text}
        msg = Message(message_id=100 + self.n, date=datetime.datetime.now(), chat=Chat(id=user.id, type="private"),
                      from_user=user, **extra)
        await self.dp.feed_update(self.bot, Update(update_id=self.n, message=msg))

    async def press(self, data, user=CUSTOMER):
        self.n += 1
        msg = Message(message_id=200 + self.n, date=datetime.datetime.now(), chat=Chat(id=user.id, type="private"),
                      text="x", caption="card")
        cb = CallbackQuery(id=str(self.n), from_user=user, chat_instance="c", message=msg, data=data)
        await self.dp.feed_update(self.bot, Update(update_id=self.n, callback_query=cb))

    async def onboard(self, user=CUSTOMER, lang="uz"):
        await self.store.touch_user(user.id, user.first_name, None)
        await self.store.set_lang(user.id, lang)
        await self.store.accept_consent(user.id, "1.0")

    def last(self, chat_id=CUSTOMER.id):
        return self.session.texts(chat_id)[-1]


def make_dispatcher(store, settings, api, admin_notes):
    async def notify_admins(text, photo=None, markup=None):
        admin_notes.append((text, photo, markup))

    dp = Dispatcher(storage=SqliteStorage(store))
    async def alert(key, text):
        admin_notes.append((key, text, None))

    dp.workflow_data.update(store=store, settings=settings, api=api, notify_admins=notify_admins, alert=alert)
    dp.message.outer_middleware(Onboarding())
    dp.callback_query.outer_middleware(Onboarding())
    for module in (start, promo, order, orders, balance, admin):
        module.router._parent_router = None   # modul darajasidagi router: har testda yangi Dispatcher
        dp.include_router(module.router)
    return dp


@pytest_asyncio.fixture
async def env(store):
    settings = SimpleNamespace(admin_ids=[1], card_number="8600 0000 0000 0000", card_holder="Ali", click_enabled=False,
                               support_username="support", per_user_active=5, required_channel="")
    session, api, notes = FakeSession(), FakeApi(), []
    bot = Bot("123456:TEST", session=session)
    e = Env(store, session, make_dispatcher(store, settings, api, notes), bot, notes, api)
    e.settings = settings
    await e.onboard(CUSTOMER)
    await e.onboard(ADMIN)
    return e


async def test_onboarding_til_rozilik_menyu(env, store):
    new = User(id=77, is_bot=False, first_name="Vali")
    await env.say("/start", user=new)
    assert "Choose language" in env.last(77)
    await env.press("lang:ru", user=new)
    assert "Конфиденциальность" in env.last(77)
    await env.press("consent:full", user=new)
    assert "Политика конфиденциальности" in env.last(77) and "@support" in env.last(77)
    await env.press("consent:yes", user=new)
    assert "Привет" in env.last(77) and "Курсовая работа" in env.last(77)
    row = await store.user(77)
    assert row["lang"] == "ru" and row["consent_version"] == "1.0"


async def test_rozilik_siz_hech_narsa_ishlamaydi(env, store):
    new = User(id=78, is_bot=False, first_name="Vali")
    await store.touch_user(78, "Vali", None)
    await store.set_lang(78, "en")
    await env.say("📊 Presentation", user=new)
    assert "accept the terms" in env.last(78)
    await env.press("c:uz", user=new)
    assert await env.dp.storage.get_state(__import__("aiogram").fsm.storage.base.StorageKey(
        bot_id=env.bot.id, chat_id=78, user_id=78)) is None


async def test_taqdimot_toliq_oqim(env):
    await env.store.credit(5, 10_000, "topup")
    await env.say("📊 Taqdimot")
    await env.press("c:uz")                       # 1) hujjat tili
    await env.say("Iqtisodiyot")                  # 2) fan
    await env.say("Sun'iy intellekt ta'limda")    # 3) mavzu
    await env.press("ts:0")                       # 4) shablon (karusel)
    await env.press("c:15")                       # 5) slaydlar
    await env.press("skip")                       # 6) taqdimotchi
    await env.press("skip")                       # 7) rahbar
    assert "5 500" in env.last()                  # 15 slayd = boshlang'ich 4 500 + 1 000
    await env.press("ok")
    rows = await env.store.orders_by_status("queued")
    assert len(rows) == 1 and rows[0]["service"] == "taqdimot" and rows[0]["price"] == 5_500
    assert json.loads(rows[0]["params"]) == {"language": "uz", "subject": "Iqtisodiyot",
                                             "topic": "Sun'iy intellekt ta'limda", "template": "econ_ledger", "slides": 15}
    assert await env.store.balance(5) == 4_500


async def test_kurs_ishi_pogona_narxi_va_titul_saqlanadi(env):
    await env.store.credit(5, 200_000, "topup")
    await env.say("📖 Kurs ishi")
    await env.press("c:uz")
    await env.say("Ali Valiyev")                  # ism
    await env.press("skipall")                    # qolgan titul maydonlari
    await env.say("Menejment")
    await env.say("Korxonada boshqaruv tizimi")
    await env.press("c:40-50")
    assert "75 000" in env.last()
    await env.press("ok")
    row = (await env.store.orders_by_status("queued"))[0]
    params = json.loads(row["params"])
    assert params["pages"] == "40-50" and params["student"] == {"full_name": "Ali Valiyev"} and row["price"] == 75_000
    assert await env.store.balance(5) == 125_000
    assert (await env.store.profile(5)) == {"full_name": "Ali Valiyev"}

    # ikkinchi buyurtma: saqlangan ma'lumot taklif qilinadi va titul savollari o'tkazib yuboriladi
    await env.say("📖 Kurs ishi")
    await env.press("c:uz")
    assert "Ali Valiyev" in env.last()
    await env.press("prof:yes")
    assert "Fan" in env.last() or "fan" in env.last().lower()
    await env.say("Marketing")
    await env.say("Raqamli marketing strategiyasi")
    await env.press("c:20-30")
    assert "55 000" in env.last() and "Ali Valiyev" in env.last()


async def test_ikki_marta_bosilgan_tasdiq_bitta_buyurtma(env):
    await env.store.credit(5, 20_000, "topup")
    await env.say("❓ Test")
    await env.press("c:uz")
    await env.say("Matematika")
    await env.say("Algebra asoslari")
    await env.press("c:10")
    await env.press("ok")
    await env.press("ok")
    assert len(await env.store.orders_by_status("queued")) == 1
    assert await env.store.balance(5) == 17_500


async def test_foydalanuvchi_faol_buyurtma_limiti(env):
    env.settings.per_user_active = 1
    await env.store.credit(5, 20_000, "topup")
    for _ in range(2):
        await env.say("🧩 Krossvord")
        await env.press("c:uz")
        await env.say("Geografiya")
        await env.say("Daryolar")
        await env.press("c:10")
        await env.press("ok")
    assert len(await env.store.orders_by_status("queued")) == 1
    assert await env.store.balance(5) == 18_500       # ikkinchisidan pul yechilmadi
    assert "1" in env.last()


async def test_balans_yetmasa_toldirish_taklif_qilinadi(env):
    await env.say("🧩 Krossvord")
    await env.press("c:uz")
    await env.say("Geografiya")
    await env.say("Daryolar")
    await env.press("c:10")
    assert "Yetmaydi" in env.last()
    await env.press("ok")
    assert await env.store.balance(5) == 0 and await env.store.orders_by_status("queued") == []


async def test_qisqa_mavzu_va_menyu_oqimni_uzadi(env):
    await env.say("📊 Taqdimot")
    await env.press("c:uz")
    await env.say("Fan")
    await env.say("abc")                          # 5 belgidan kam
    assert "belgi" in env.last()
    await env.say("💰 Balans")                    # menyu tugmasi mavzu bo'lib ketmasligi kerak
    assert "Balansingiz" in env.last()


async def test_fsm_holati_qayta_ishga_tushganda_saqlanadi(env, store):
    await env.say("📊 Taqdimot")
    await env.press("c:uz")
    await env.say("Iqtisodiyot")
    # bot qayta ishga tushdi: yangi Dispatcher, xuddi shu baza
    fresh = make_dispatcher(store, env.settings, env.api, env.admin_notes)
    env.dp = fresh
    await env.say("Raqamli iqtisodiyot mavzusi")  # savol uzilmasdan davom etadi
    assert "shablon" in env.last().lower()


async def test_karta_tolovi_summani_tahrirlash_va_tasdiqlash(env, store):
    await env.press("topup:0")
    await env.press("ta:5000")
    await env.press("pm:card:5000")
    await env.say("", photo=True)
    assert env.admin_notes and "5 000" in env.admin_notes[-1][0]
    markup = env.admin_notes[-1][2]
    assert [b.callback_data for row in markup.inline_keyboard for b in row] == ["pa:1", "pr:1", "pe:1"]

    await env.press("pe:1", user=ADMIN)
    await env.say("3000", user=ADMIN)                 # chekdagi haqiqiy summa
    payment = await store.payment(1)
    assert payment["amount"] == 3_000 and payment["original_amount"] == 5_000

    await env.press("pa:1", user=ADMIN)
    assert await store.balance(5) == 3_000
    assert "3 000" in env.last(5) and "5 000" in env.last(5)       # mijozga farq tushuntiriladi
    await env.press("pa:1", user=ADMIN)                           # ikkinchi bosish
    assert await store.balance(5) == 3_000


async def test_oddiy_foydalanuvchi_admin_tugmalarini_bosolmaydi(env, store):
    pid = await store.new_payment(5, 5_000, "card", "pending", "x")
    await env.press(f"pa:{pid}", user=CUSTOMER)
    await env.press(f"pe:{pid}", user=CUSTOMER)
    assert (await store.payment(pid))["status"] == "pending" and await store.balance(5) == 0


async def test_qayta_yuklab_olish_api_va_telegram_nusxasi(env, store):
    await store.credit(5, 10_000, "topup")
    oid = await store.place_order(5, "test", {}, 2_500)
    await store.update_order(oid, status="succeeded", delivered=1, partner_order_id="ord_1",
                             tg_files=json.dumps(["tgfile1"]))
    await env.say("📦 Buyurtmalarim")
    assert "#1" in env.last()
    await env.press(f"dl:{oid}")
    assert len(env.session.documents(5)) == 1                    # hamkor API'dan
    env.api.expired = True
    await env.press(f"dl:{oid}")
    docs = env.session.documents(5)
    assert len(docs) == 2 and docs[-1].document == "tgfile1"      # muddat tugagan: Telegram nusxasi
    await store.update_order(oid, tg_files=None)
    await env.press(f"dl:{oid}")
    assert "7" in env.last()                                      # muddat tugagani aytiladi


async def test_boshqa_foydalanuvchi_buyurtmasini_yuklab_olmaydi(env, store):
    await store.credit(1, 10_000, "topup")
    oid = await store.place_order(1, "test", {}, 2_500)
    await store.update_order(oid, status="succeeded", delivered=1, partner_order_id="ord_1")
    await env.press(f"dl:{oid}", user=CUSTOMER)
    assert env.session.documents(5) == []


async def test_til_ozgartirish_menyuni_yangilaydi(env, store):
    await env.say("🌐 Til")
    await env.press("lang:en")
    assert (await store.user(5))["lang"] == "en"
    assert "Hello" in env.last()


async def test_hajmga_qarab_narx_referat_va_test(env):
    await env.store.credit(5, 50_000, "topup")
    await env.say("📄 Referat")
    await env.press("c:uz")
    await env.press("skipall")
    await env.say("Tarix")
    await env.say("Amir Temur davri")
    await env.press("c:20")                         # 20 bet = 4 500 + 2 × 1 000
    assert "6 500" in env.last()
    await env.press("ok")
    assert await env.store.balance(5) == 43_500

    await env.say("❓ Test")
    await env.press("c:uz")
    await env.say("Fizika")
    await env.say("Mexanika asoslari")
    await env.press("c:30")                         # 30 savol = 2 500 + 4 × 1 000
    assert "6 500" in env.last()
    await env.press("ok")
    assert await env.store.balance(5) == 37_000


async def test_menyuda_boshlangich_narx_dan_korinadi(env):
    await env.say("/start")
    text = env.last()
    assert "4 500 so'm dan" in text and "55 000 so'm dan" in text and "1 500 so'm dan" in text
