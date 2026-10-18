import json
import time

from app import subscription
from tests.test_flow import ADMIN, CUSTOMER, env, make_dispatcher  # noqa: F401  (fixture)

ALL5 = ["taqdimot", "mustaqil_ish", "referat", "test", "krossvord"]


# ── Store: qoidalar ──────────────────────────────────────────────────────

async def test_promokod_qoidalari(store):
    await store.touch_user(2, "B", None)
    await store.touch_user(3, "C", None)
    await store.create_promo("TEZ", ALL5, max_uses=2, expires_at=None)
    assert (await store.redeem("YOQ", 1))[0] == "invalid"
    assert (await store.redeem("TEZ", 1))[0] == "ok"
    assert (await store.redeem("TEZ", 1))[0] == "used"            # bir kishi bir marta
    assert (await store.redeem("TEZ", 2))[0] == "ok"
    assert (await store.redeem("TEZ", 3))[0] == "limit"           # chegara tugadi


async def test_muddati_tugagan_va_ochirilgan_kod(store):
    await store.create_promo("OLD", ALL5, None, int(time.time()) - 10)
    await store.create_promo("OFF", ALL5, None, None)
    await store.set_promo_active("OFF", False)
    assert (await store.redeem("OLD", 1))[0] == "expired"
    assert (await store.redeem("OFF", 1))[0] == "invalid"


async def test_ikkinchi_kod_faol_kupon_borida_olinmaydi(store):
    await store.create_promo("A1", ALL5, None, None)
    await store.create_promo("B2", ALL5, None, None)
    assert (await store.redeem("A1", 1))[0] == "ok"
    assert (await store.redeem("B2", 1))[0] == "has_active"


async def test_bepul_buyurtma_kuponi_bir_marta_sarflanadi_va_xatoda_qaytadi(store):
    await store.create_promo("TEZ", ALL5, None, None)
    _, voucher = await store.redeem("TEZ", 1)
    oid = await store.place_free_order(1, "referat", {"topic": "x"}, voucher["id"])
    assert isinstance(oid, int) and (await store.order(oid))["price"] == 0
    assert await store.place_free_order(1, "referat", {}, voucher["id"]) is None      # ikkinchi marta yo'q
    assert await store.active_voucher(1) is None
    assert await store.refund_order(oid) is True                                       # buyurtma xato bo'ldi
    assert (await store.active_voucher(1))["id"] == voucher["id"]                      # kupon qaytdi
    assert await store.balance(1) == 0                                                 # pul emas, huquq qaytdi
    assert await store.refund_order(oid) is False


async def test_begona_kupon_ishlamaydi(store):
    await store.touch_user(2, "B", None)
    await store.create_promo("TEZ", ALL5, None, None)
    _, voucher = await store.redeem("TEZ", 1)
    assert await store.place_free_order(2, "test", {}, voucher["id"]) is None


async def test_bepul_buyurtma_faol_buyurtma_chegarasini_hurmat_qiladi(store):
    await store.create_promo("TEZ", ALL5, None, None)
    _, voucher = await store.redeem("TEZ", 1)
    await store.credit(1, 10_000, "t")
    await store.place_order(1, "test", {}, 2_500)
    assert await store.place_free_order(1, "referat", {}, voucher["id"], max_active=1) == "limit"
    assert (await store.active_voucher(1)) is not None                                 # kupon sarflanmadi


# ── Bot oqimi ────────────────────────────────────────────────────────────

async def test_promokod_tunneli_va_bepul_buyurtma(env):
    await env.store.create_promo("TEZSTART", ALL5, 300, None)
    await env.say("🎁 Promokod")
    await env.say("noto'g'ri kod")
    assert "yo'q" in env.last()                                  # holat saqlanadi, qayta yozsa bo'ladi
    await env.say("tez start")                                    # katta-kichik harf va bo'shliqqa befarq
    assert "istalgan bittasi bepul" in env.last() and "Taqdimot" in env.last()
    assert (await env.store.active_voucher(5))["code"] == "TEZSTART"

    await env.say("📝 Mustaqil ish")
    await env.press("c:uz")
    await env.press("skipall")
    await env.say("Marketing")
    await env.say("Raqamli marketing strategiyasi")
    await env.press("c:20")                                       # hajm ahamiyatsiz
    assert "bepul buyurtma" in env.last()
    await env.press("free")
    rows = await env.store.orders_by_status("queued")
    assert len(rows) == 1 and rows[0]["price"] == 0 and rows[0]["voucher_id"]
    assert await env.store.balance(5) == 0 and await env.store.active_voucher(5) is None
    await env.press("free")                                       # ikki marta bosish
    assert len(await env.store.orders_by_status("queued")) == 1


async def test_kurs_ishi_promokodga_kirmaydi(env):
    await env.store.create_promo("TEZSTART", ALL5, None, None)
    await env.store.redeem("TEZSTART", 5)
    await env.say("📖 Kurs ishi")
    await env.press("c:uz")
    await env.press("skipall")
    await env.say("Menejment")
    await env.say("Boshqaruv tizimi mavzusi")
    await env.press("c:20-30")
    assert "bepul" not in env.last().lower() and "free" not in env.last().lower()
    assert "55 000" in env.last()


# ── Kanalga a'zolik darvozasi ────────────────────────────────────────────

async def test_kanalga_azo_bolmagan_foydalana_olmaydi(env):
    env.settings.required_channel = "@teztopshir"
    subscription._cache.clear()
    await env.say("📊 Taqdimot")
    assert "kanalimizga a'zo bo'ling" in env.last()
    assert await env.dp.storage.get_state(__import__("aiogram").fsm.storage.base.StorageKey(
        bot_id=env.bot.id, chat_id=5, user_id=5)) is None            # oqim boshlanmadi

    env.session.members.add(5)
    await env.press("sub:check")                                      # «A'zo bo'ldim»
    assert "Salom" in env.last()
    await env.say("📊 Taqdimot")                                      # endi ishlaydi
    assert "Hujjat qaysi tilda" in env.last()


async def test_azo_bolmasa_sub_check_rad_etadi(env):
    env.settings.required_channel = "@teztopshir"
    subscription._cache.clear()
    before = len(env.session.texts(5))
    await env.press("sub:check")
    assert len(env.session.texts(5)) == before                        # menyu ochilmadi


async def test_start_ham_kanalni_tekshiradi(env):
    env.settings.required_channel = "@teztopshir"
    subscription._cache.clear()
    await env.say("/start")
    assert "kanalimizga a'zo bo'ling" in env.last()
    env.session.members.add(5)
    subscription._cache.clear()
    await env.say("/start")
    assert "Salom" in env.last()


async def test_tekshiruv_xato_bersa_ham_otkazilmaydi_va_admin_ogohlantiriladi(env):
    env.settings.required_channel = "@teztopshir"
    subscription._cache.clear()
    env.session.member_error = True                                   # bot kanalda admin emas
    await env.say("📊 Taqdimot")
    assert "kanalimizga a'zo bo'ling" in env.last()                   # fail-open YO'Q
    assert any(n[0] == "sub_check_failed" for n in env.admin_notes)


async def test_til_almashtirish_azo_bolmaganga_menyu_ochmaydi(env):
    env.settings.required_channel = "@teztopshir"
    subscription._cache.clear()
    await env.press("lang:ru")
    assert "подпишитесь" in env.last()                                # menyu emas, a'zolik talabi
    assert "Привет" not in env.last()


async def test_kanaldan_chiqqan_kesh_tugagach_otmaydi(env):
    env.settings.required_channel = "@teztopshir"
    subscription._cache.clear()
    env.session.members.add(5)
    await env.say("📊 Taqdimot")
    assert "Hujjat qaysi tilda" in env.last()
    env.session.members.discard(5)                                    # kanaldan chiqib ketdi
    subscription._cache[5] = 0                                        # kesh muddati tugadi
    await env.say("📝 Mustaqil ish")
    assert "kanalimizga a'zo bo'ling" in env.last()


async def test_adminlar_kanal_tekshiruvidan_ozod(env):
    env.settings.required_channel = "@teztopshir"
    subscription._cache.clear()
    await env.say("📊 Taqdimot", user=ADMIN)
    assert "Hujjat qaysi tilda" in env.last(1)


async def test_adminni_ham_tekshirish_yoqilsa_kanal_soraladi(env):
    env.settings.required_channel = "@teztopshir"
    env.settings.channel_check_admins = True
    subscription._cache.clear()
    await env.say("📊 Taqdimot", user=ADMIN)
    assert "kanalimizga a'zo bo'ling" in env.last(1)
