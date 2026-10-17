import json

import httpx
import pytest

from app.api import PartnerClient
from app.worker import Worker


class FakeBot:
    def __init__(self):
        self.messages, self.documents = [], []

    async def send_message(self, chat_id, text, **kw):
        self.messages.append((chat_id, text))

    async def send_document(self, chat_id, document, caption=None, **kw):
        self.documents.append((chat_id, document.filename, caption))


def make(handler):
    api = PartnerClient("https://api.test/partner/v1", "ot_test_x", transport=httpx.MockTransport(handler))
    alerts = []

    async def alert(key, text):
        alerts.append(key)

    return api, alerts, alert


async def place(store, service="taqdimot", price=4_500):
    await store.credit(1, 20_000, "topup")
    return await store.place_order(1, service, {"topic": "Mavzu uzun", "slides": 10}, price)


async def test_muvaffaqiyatli_oqim(store):
    seen = {}

    def handler(request: httpx.Request):
        if request.method == "POST":
            seen["idem"] = request.headers["Idempotency-Key"]
            seen["body"] = json.loads(request.content)
            return httpx.Response(202, json={"id": "ord_1", "status": "queued"})
        if request.url.path.endswith("/orders/ord_1"):
            return httpx.Response(200, json={"id": "ord_1", "status": "succeeded",
                                             "result": {"files": [{"id": "fil_1", "name": "t.pptx"}]}})
        return httpx.Response(200, content=b"PPTXDATA")

    api, alerts, alert = make(handler)
    bot = FakeBot()
    oid = await place(store)
    w = Worker(store, api, bot, 8, alert)
    w.poll_every = 0
    await w.tick()
    order = await store.order(oid)
    assert seen["idem"] == f"tez-{oid}" and seen["body"]["service"] == "taqdimot"
    assert order["partner_order_id"] == "ord_1"
    await w.tick()
    order = await store.order(oid)
    assert order["status"] == "succeeded" and order["delivered"] == 1
    assert bot.documents[0][:2] == (1, "t.pptx") and "sun'iy intellekt" in bot.documents[0][2]
    assert await store.balance(1) == 15_500 and alerts == []


async def test_kredit_tugasa_pul_qaytadi_va_admin_ogohlantiriladi(store):
    def handler(request):
        return httpx.Response(402, json={"error": {"code": "insufficient_credits", "message": "x"}})

    api, alerts, alert = make(handler)
    bot = FakeBot()
    oid = await place(store)
    await Worker(store, api, bot, 8, alert).tick()
    order = await store.order(oid)
    assert order["status"] == "failed" and order["refunded"] == 1
    assert await store.balance(1) == 20_000
    assert alerts == ["credits:taqdimot"] and bot.messages


async def test_5xx_da_navbatda_qoladi_pul_qaytmaydi(store):
    api, alerts, alert = make(lambda r: httpx.Response(503, json={"error": {"code": "unavailable"}}))
    oid = await place(store)
    await Worker(store, api, FakeBot(), 8, alert).tick()
    order = await store.order(oid)
    assert order["status"] == "queued" and order["attempts"] == 1 and order["next_try_at"] > 0
    assert await store.balance(1) == 15_500


async def test_hamkor_failed_desa_pul_qaytadi(store):
    def handler(request):
        if request.method == "POST":
            return httpx.Response(202, json={"id": "ord_2", "status": "queued"})
        return httpx.Response(200, json={"id": "ord_2", "status": "failed", "error": {"code": "generation_failed"}})

    api, alerts, alert = make(handler)
    bot = FakeBot()
    oid = await place(store)
    w = Worker(store, api, bot, 8, alert)
    w.poll_every = 0
    await w.tick()
    await w.tick()
    assert (await store.order(oid))["status"] == "failed"
    assert await store.balance(1) == 20_000
    assert "qaytarildi" in bot.messages[-1][1]


async def test_faol_buyurtma_chegarasi(store):
    calls = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"status": "processing"})
        calls.append(1)
        return httpx.Response(202, json={"id": f"ord_{len(calls)}", "status": "queued"})

    api, alerts, alert = make(handler)
    await store.credit(1, 100_000, "topup")
    for _ in range(3):
        await store.place_order(1, "test", {"topic": "Mavzu", "questions": 10}, 2_500)
    await Worker(store, api, FakeBot(), 2, alert).tick()      # chegara 2
    assert len(calls) == 2 and len(await store.orders_by_status("queued")) == 1


async def test_yetkazish_xatosi_keyin_qayta_uriniladi(store):
    ok = {"send": False}

    class FlakyBot(FakeBot):
        async def send_document(self, chat_id, document, caption=None, **kw):
            if not ok["send"]:
                raise RuntimeError("telegram down")
            await super().send_document(chat_id, document, caption)

    def handler(request):
        if request.method == "POST":
            return httpx.Response(202, json={"id": "ord_3", "status": "queued"})
        if request.url.path.endswith("/orders/ord_3"):
            return httpx.Response(200, json={"id": "ord_3", "status": "succeeded",
                                             "result": {"files": [{"id": "f", "name": "a.docx"}]}})
        return httpx.Response(200, content=b"x")

    api, alerts, alert = make(handler)
    bot = FlakyBot()
    oid = await place(store)
    w = Worker(store, api, bot, 8, alert)
    w.poll_every = 0
    await w.tick()
    await w.tick()
    assert (await store.order(oid))["delivered"] == 0       # fayl yo'qolmadi
    ok["send"] = True
    await w.tick()
    assert (await store.order(oid))["delivered"] == 1 and len(bot.documents) == 1
