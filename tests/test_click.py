import hashlib

import pytest
from aiohttp.test_utils import TestClient, TestServer

from app.click_server import make_app, sign_ok

SECRET, SERVICE = "sekret", "777"


class S:
    click_secret, click_service_id = SECRET, SERVICE


class Bot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, **kw):
        self.sent.append(chat_id)


def sign(d: dict, complete: bool) -> str:
    parts = [d["click_trans_id"], SERVICE, SECRET, d["merchant_trans_id"]]
    if complete:
        parts.append(d["merchant_prepare_id"])
    parts += [d["amount"], d["action"], d["sign_time"]]
    return hashlib.md5("".join(str(p) for p in parts).encode()).hexdigest()


def body(pid, amount="5000", action="0", complete=False):
    d = {"click_trans_id": "99", "merchant_trans_id": str(pid), "amount": amount, "action": action,
         "sign_time": "2026-10-17 10:00:00"}
    if complete:
        d["merchant_prepare_id"] = str(pid)
        d["action"] = "1" if action == "0" else action
    d["sign_string"] = sign(d, complete)
    return d


@pytest.fixture
async def client(store):
    bot = Bot()
    c = TestClient(TestServer(make_app(store, S(), bot)))
    await c.start_server()
    c.bot = bot
    yield c
    await c.close()


async def test_imzo_notogri_bolsa_rad(client, store):
    pid = await store.new_payment(1, 5000, "click", "pending")
    d = body(pid)
    d["sign_string"] = "x" * 32
    r = await (await client.post("/click/prepare", data=d)).json()
    assert r["error"] == -1


async def test_toliq_oqim_balansni_bir_marta_toldiradi(client, store):
    pid = await store.new_payment(1, 5000, "click", "pending")
    assert (await (await client.post("/click/prepare", data=body(pid))).json())["error"] == 0
    r = await (await client.post("/click/complete", data=body(pid, complete=True))).json()
    assert r["error"] == 0 and await store.balance(1) == 5000
    again = await (await client.post("/click/complete", data=body(pid, complete=True))).json()
    assert again["error"] == 0 and await store.balance(1) == 5000      # ikkinchi marta qo'shilmaydi
    assert client.bot.sent == [1]


async def test_summa_mos_kelmasa_rad(client, store):
    pid = await store.new_payment(1, 5000, "click", "pending")
    r = await (await client.post("/click/prepare", data=body(pid, amount="4000"))).json()
    assert r["error"] == -2 and await store.balance(1) == 0


async def test_prepare_siz_complete_pul_qoshmaydi(client, store):
    pid = await store.new_payment(1, 5000, "click", "pending")
    await client.post("/click/complete", data=body(pid, complete=True))
    assert await store.balance(1) == 0


async def test_noma_lum_tolov(client):
    r = await (await client.post("/click/prepare", data=body(12345))).json()
    assert r["error"] == -5


def test_sign_ok_funksiyasi():
    d = body(1)
    assert sign_ok(d, SECRET, SERVICE, complete=False)
