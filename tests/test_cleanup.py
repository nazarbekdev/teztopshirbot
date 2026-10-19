"""Chat toza qoladi: javob berilgan savollar va foydalanuvchi javoblari o'chadi, faqat natija qoladi."""

from aiogram.methods import DeleteMessages

from app import subscription
from tests.test_flow import ADMIN, CUSTOMER, env  # noqa: F401  (fixture)


def user_ids(env):
    """`say` bilan yuborilgan foydalanuvchi xabarlari ID'lari (Env.say: 100 + n)."""
    return {100 + i for i in range(1, env.n + 1)}


def deleted_user_messages(env):
    return {mid for mid in env.session.deleted if 100 < mid < 200}


async def test_savol_javobdan_keyin_ochadi_faqat_joriy_savol_qoladi(env):
    await env.say("/start")
    base = len(env.session.alive())                                  # /start salomi
    await env.say("📊 Taqdimot")
    await env.press("c:uz")
    assert len(env.session.alive()) == base + 1                      # faqat «Fan nomi» savoli
    await env.say("Iqtisodiyot")
    assert len(env.session.alive()) == base + 1                      # fan savoli ketdi, mavzu savoli keldi
    assert "Mavzu" in env.last() or "mavzu" in env.last().lower()
    await env.say("Kichik biznes rivoji")
    # foydalanuvchining javoblari («Taqdimot», fan, mavzu) chatdan o'chdi
    assert {101 + 0, 102, 103} <= deleted_user_messages(env) or len(deleted_user_messages(env)) >= 3


async def test_buyurtma_tugagach_faqat_natija_qoladi(env):
    await env.store.credit(5, 50_000, "topup")
    await env.say("/start")
    await env.say("📊 Taqdimot")
    await env.press("c:uz")
    await env.say("Iqtisodiyot")
    await env.say("Kichik biznes rivoji")
    await env.press("ts:0")
    await env.press("c:15")
    await env.press("skip")
    await env.press("skip")
    await env.press("ok")
    alive = env.session.alive()
    assert any("qabul qilindi" in t for t in alive)                  # natija qoldi
    for t in alive:                                                  # oraliq xabarlar yo'q
        assert "Fan nomi" not in t and "Dizayn" not in t and "Narxi" not in t, t
    assert "<photo>" not in alive                                    # shablon karuseli ham o'chdi
    assert deleted_user_messages(env) == {102, 104, 105}            # menyu tugmasi, fan va mavzu javoblari o`chdi (/start qoladi)


async def test_xato_javob_va_xato_izohi_keyingi_togri_javobda_ochadi(env):
    await env.say("📊 Taqdimot")
    await env.press("c:uz")
    await env.say("Fan nomi")
    await env.say("abc")                                             # mavzu juda qisqa
    assert "belgi" in env.last()
    alive_before = len(env.session.alive())
    await env.say("Yetarlicha uzun mavzu")
    # xato izohi va noto'g'ri javob o'chdi: chatda yangi savol/karusel qoldi, xato izohi emas
    assert not any("belgi bo'lishi kerak" in t for t in env.session.alive())
    assert len(env.session.alive()) <= alive_before


async def test_bekor_qilganda_oqim_xabarlari_ochadi(env):
    await env.say("📖 Kurs ishi")
    await env.press("c:uz")
    await env.say("Ali Valiyev")
    await env.press("cancel")
    alive = env.session.alive()
    assert alive and "Bekor qilindi" in alive[-1]
    assert not any("Ism" in t or "ism" in t.lower() and "titul" in t.lower() for t in alive[:-1])
    assert len(alive) == 1


async def test_menyu_tugmasi_oqimni_uzsa_xabarlar_ochadi(env):
    await env.say("📊 Taqdimot")
    await env.press("c:uz")
    await env.say("💰 Balans")                                       # oqim o'rtasida boshqa bo'limga o'tdi
    alive = env.session.alive()
    assert len(alive) == 1 and "Balansingiz" in alive[0]


async def test_promokod_tunnelidan_keyin_faqat_natija(env):
    await env.store.create_promo("TEZSTART", ["test"], None, None)
    await env.say("🎁 Promokod")
    await env.say("noto'g'ri")
    await env.say("tez start")
    alive = env.session.alive()
    assert len(alive) == 1 and "qabul qilindi" in alive[0]


async def test_balans_toldirish_chek_yuborilgach_faqat_tasdiq_qoladi(env):
    await env.say("💰 Balans")
    await env.press("topup:0")
    await env.press("ta:5000")
    await env.press("pm:card:5000")
    await env.say("", photo=True)
    alive = env.session.alive()
    assert "Chek qabul qilindi" in alive[-1]
    assert not any("Karta:" in t for t in alive)                     # karta ko'rsatmasi o'chdi
    assert not any("Qancha to'ldirasiz" in t for t in alive)


async def test_ochirish_xatosi_oqimni_buzmaydi(env):
    """Telegram xabarni o'chirmasa (eski/allaqachon o'chgan) javob baribir qabul qilinadi."""
    original = env.session.make_request

    async def failing(bot, method, timeout=None):
        if method.__class__.__name__ in ("DeleteMessages", "DeleteMessage"):
            raise RuntimeError("message can't be deleted")
        return await original(bot, method, timeout)

    env.session.make_request = failing
    await env.say("📊 Taqdimot")
    await env.press("c:uz")
    await env.say("Iqtisodiyot")
    assert "Mavzu" in env.last() or "mavzu" in env.last().lower()
