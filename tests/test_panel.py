import json
from types import SimpleNamespace

import pytest
from aiohttp.test_utils import TestClient, TestServer

from app.panel import auth
from app.panel.routes import make_app


class Bot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, **kw):
        self.sent.append((chat_id, text))

    async def download(self, file_id, destination=None):
        destination.write(b"\xff\xd8JPEG")


class Api:
    fail = False

    async def credits(self):
        if self.fail:
            raise RuntimeError("API ishlamayapti")
        return {"taqdimot": {"credits": 3, "unit_price": 3000}, "kurs_ishi": {"credits": 500, "unit_price": 25000}}


def settings(**kw):
    base = dict(admin_ids=[1], panel_url="", test_mode=False)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture
async def panel(store):
    auth._login_hits.clear()
    cfg, bot = settings(), Bot()
    client = TestClient(TestServer(make_app(store, cfg, bot, Api(), "teztopshirbot")))
    await client.start_server()
    client.bot, client.cfg, client.store = bot, cfg, store
    yield client
    await client.close()


async def login(client, admin_id=1):
    """Haqiqiy oqim: /login → botda tasdiq (bazada) → /auth/poll → sessiya cookie'si."""
    page = await client.get("/login")
    assert page.status == 200
    nonce = client.session.cookie_jar.filter_cookies(client.make_url("/"))["tz_lp"].value.split(":")[0]
    assert (await (await client.get("/auth/poll")).json())["status"] == "pending"
    await client.store.move_login(nonce, "pending", "approved", admin_id)
    assert (await (await client.get("/auth/poll")).json())["status"] == "ok"
    row = await client.store._one("SELECT csrf FROM admin_sessions")
    return row["csrf"]


async def test_kirishsiz_hech_narsa_ochilmaydi(panel):
    for path in ("/", "/orders", "/users", "/payments", "/audit", "/payments/1/receipt"):
        r = await panel.get(path, allow_redirects=False)
        assert r.status == 302 and r.headers["Location"] == "/login", path
    r = await panel.post("/users/5/balance", data={"amount": "5000", "reason": "x", "csrf": "x"}, allow_redirects=False)
    assert r.status == 302


async def test_login_oqimi_va_xavfsizlik_sarlavhalari(panel):
    await login(panel)
    r = await panel.get("/")
    assert r.status == 200 and "Bosh sahifa" in await r.text()
    assert r.headers["X-Frame-Options"] == "DENY" and "script-src 'self'" in r.headers["Content-Security-Policy"]
    assert r.headers["Cache-Control"] == "no-store"
    cookie = r.request_info.headers.get("Cookie", "")
    row = await panel.store._one("SELECT token_hash FROM admin_sessions")
    assert "tz_admin" in cookie and row["token_hash"] not in cookie        # bazada faqat xesh


async def test_boshqa_brauzer_sessiya_ola_olmaydi(panel):
    await panel.get("/login")
    nonce = panel.session.cookie_jar.filter_cookies(panel.make_url("/"))["tz_lp"].value.split(":")[0]
    await panel.store.move_login(nonce, "pending", "approved", 1)
    thief = TestClient(TestServer(panel.server.app))
    await thief.start_server()
    try:
        thief.session.cookie_jar.update_cookies({"tz_lp": f"{nonce}:noto'g'ri-sir"})
        assert (await (await thief.get("/auth/poll")).json())["status"] == "denied"
        assert (await thief.get("/", allow_redirects=False)).status == 302
    finally:
        await thief.close()


async def test_rad_etilgan_yoki_eskirgan_sorov_sessiya_bermaydi(panel):
    await panel.get("/login")
    nonce = panel.session.cookie_jar.filter_cookies(panel.make_url("/"))["tz_lp"].value.split(":")[0]
    await panel.store.move_login(nonce, "pending", "denied", 1)
    assert (await (await panel.get("/auth/poll")).json())["status"] == "denied"
    assert await panel.store._one("SELECT * FROM admin_sessions") is None


async def test_sessiya_bir_marta_beriladi(panel):
    await login(panel)
    nonce = (await panel.store._one("SELECT nonce FROM admin_login"))["nonce"]
    assert (await panel.store.login(nonce))["status"] == "used"
    assert (await (await panel.get("/auth/poll")).json())["status"] == "denied"


async def test_adminlikdan_chiqarilgan_sessiya_ishlamaydi(panel):
    await login(panel)
    panel.cfg.admin_ids = [999]
    assert (await panel.get("/", allow_redirects=False)).status == 302


async def test_csrf_siz_post_rad_etiladi(panel):
    csrf = await login(panel)
    r = await panel.post("/logout", data={}, allow_redirects=False)
    assert r.status == 403
    r = await panel.post("/logout", data={"csrf": csrf}, allow_redirects=False)
    assert r.status == 302
    assert (await panel.get("/", allow_redirects=False)).status == 302


async def test_balansni_qolda_ozgartirish_audit_bilan(panel):
    csrf = await login(panel)
    await panel.store.touch_user(5, "Ali", "ali")
    r = await panel.post("/users/5/balance", data={"amount": "7000", "reason": "bonus", "csrf": csrf}, allow_redirects=False)
    assert r.status == 302 and await panel.store.balance(5) == 7_000
    r = await panel.post("/users/5/balance", data={"amount": "-3000", "reason": "tuzatish", "csrf": csrf}, allow_redirects=False)
    assert await panel.store.balance(5) == 4_000
    r = await panel.post("/users/5/balance", data={"amount": "-9000", "reason": "ko'p", "csrf": csrf}, allow_redirects=False)
    assert await panel.store.balance(5) == 4_000                      # yetmasa ayirilmaydi
    r = await panel.post("/users/5/balance", data={"amount": "100", "reason": "", "csrf": csrf}, allow_redirects=False)
    assert await panel.store.balance(5) == 4_000                      # sababsiz — yo'q
    ledger = await panel.store.user_ledger(5)
    assert {l["reason"] for l in ledger} == {"admin:bonus", "admin:tuzatish"}
    audit = await panel.store.recent_audit()
    assert [a["action"] for a in audit][:2] == ["balance_adjust", "balance_adjust"]


async def test_tolov_tahrirlash_va_tasdiqlash_mijozga_xabar(panel):
    csrf = await login(panel)
    await panel.store.touch_user(5, "Ali", "ali")
    pid = await panel.store.new_payment(5, 5_000, "card", "pending", "rcpt")
    r = await panel.post(f"/payments/{pid}/edit", data={"amount": "3000", "csrf": csrf}, allow_redirects=False)
    assert (await panel.store.payment(pid))["amount"] == 3_000
    await panel.post(f"/payments/{pid}/approve", data={"csrf": csrf}, allow_redirects=False)
    await panel.post(f"/payments/{pid}/approve", data={"csrf": csrf}, allow_redirects=False)   # ikkinchi marta
    assert await panel.store.balance(5) == 3_000
    assert len(panel.bot.sent) == 1 and "3 000" in panel.bot.sent[0][1] and "5 000" in panel.bot.sent[0][1]
    r = await panel.post(f"/payments/{pid}/edit", data={"amount": "9000", "csrf": csrf}, allow_redirects=False)
    assert (await panel.store.payment(pid))["amount"] == 3_000          # tasdiqlangandan keyin tahrirlanmaydi


async def test_tolovni_rad_etish_va_chek_rasmi(panel):
    csrf = await login(panel)
    await panel.store.touch_user(5, "Ali", "ali")
    pid = await panel.store.new_payment(5, 5_000, "card", "pending", "rcpt")
    r = await panel.get(f"/payments/{pid}/receipt")
    assert r.status == 200 and r.headers["Content-Type"] == "image/jpeg" and (await r.read()).startswith(b"\xff\xd8")
    await panel.post(f"/payments/{pid}/reject", data={"csrf": csrf}, allow_redirects=False)
    assert (await panel.store.payment(pid))["status"] == "rejected" and await panel.store.balance(5) == 0
    page = await (await panel.get("/payments?status=")).text()
    assert "rejected" in page


async def test_buyurtma_qaytarish_qoidalari(panel):
    csrf = await login(panel)
    await panel.store.touch_user(5, "Ali", "ali")
    await panel.store.credit(5, 50_000, "topup")
    ids = {}
    for status in ("queued", "failed", "processing", "succeeded"):
        oid = await panel.store.place_order(5, "test", {"topic": "x"}, 2_500)
        await panel.store.update_order(oid, status=status)
        ids[status] = oid
    assert await panel.store.balance(5) == 40_000
    for status in ("queued", "failed", "processing", "succeeded"):
        await panel.post(f"/orders/{ids[status]}/refund", data={"csrf": csrf}, allow_redirects=False)
    assert await panel.store.balance(5) == 45_000                       # faqat queued va failed qaytdi
    assert (await panel.store.order(ids["queued"]))["status"] == "canceled"
    await panel.post(f"/orders/{ids['failed']}/refund", data={"csrf": csrf}, allow_redirects=False)
    assert await panel.store.balance(5) == 45_000                       # ikki marta qaytmaydi


async def test_sahifalar_ochiladi_va_html_ekranlanadi(panel):
    await login(panel)
    await panel.store.touch_user(5, "<script>alert(1)</script>", "ali")
    await panel.store.credit(5, 10_000, "topup")
    oid = await panel.store.place_order(5, "taqdimot", {"topic": "<b>x</b>"}, 4_500)
    for path in ("/", "/orders", f"/orders/{oid}", "/users", "/users/5", "/payments", "/audit",
                 "/orders?status=failed&service=test&user=5"):
        r = await panel.get(path)
        text = await r.text()
        assert r.status == 200, path
        assert "<script>alert(1)</script>" not in text and "<b>x</b>" not in text
    assert (await panel.get("/orders/99999")).status == 404


async def test_bosh_sahifa_kreditlar_va_api_xatosi(panel):
    await login(panel)
    page = await (await panel.get("/")).text()
    assert "25 000" in page and "500" in page                            # kurs ishi: hamkor narxi va kredit
    panel.server.app["api"].fail = True
    page = await (await panel.get("/")).text()
    assert "Kreditlarni olib bo'lmadi" in page


async def test_kirish_urinishlari_cheklanadi(panel):
    statuses = [(await panel.get("/login")).status for _ in range(12)]
    assert statuses[:10] == [200] * 10 and statuses[10:] == [429, 429]
