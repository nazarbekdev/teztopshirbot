import json

from aiogram.methods import EditMessageMedia, SendPhoto

from app.details import needs_details
from tests.test_flow import ADMIN, CUSTOMER, env  # noqa: F401  (fixture)


async def start_taqdimot(env, subject="Iqtisodiyot", topic="Kichik biznes rivoji"):
    await env.store.credit(5, 50_000, "topup")
    await env.say("📊 Taqdimot")
    await env.press("c:uz")
    await env.say(subject)
    await env.say(topic)


def photos(env):
    return [m for m in env.session.calls if isinstance(m, SendPhoto)]


def edits(env):
    return [m for m in env.session.calls if isinstance(m, EditMessageMedia)]


def test_shaxsiy_mavzu_aniqlash_asosiy_bot_bilan_bir_xil():
    for topic in ("Bizning mahalla", "Mening maktabim tarixi", "Наш город", "Мой колледж", "My city", "our school"):
        assert needs_details(topic), topic
    for topic in ("Qayta tiklanuvchi energiya", "Amir Temur davri", "Экономика Узбекистана", "Machine learning"):
        assert not needs_details(topic), topic


async def test_karusel_soha_shabloni_birinchi_va_navigatsiya(env):
    await start_taqdimot(env)
    assert env.api.template_calls == [("Iqtisodiyot", "Kichik biznes rivoji")]    # fan va mavzu API'ga ketdi
    assert "Dizayn shablonini" in env.last()
    assert len(photos(env)) == 1
    first = photos(env)[0]
    assert "econ_ledger uz" in first.caption and "Iqtisodiyot yo'nalishi uchun" in first.caption
    assert "1 / 4" in first.caption
    buttons = [b.callback_data for row in first.reply_markup.inline_keyboard for b in row]
    assert buttons[:3] == ["tn:3", "ts:0", "tn:1"] and buttons[3:] == ["tn:0", "tn:1", "tn:2", "tn:3"]   # aylanma

    await env.press("tn:2")
    assert len(edits(env)) == 1 and "med_clinic" in edits(env)[0].media.caption or "corporate_blue" in edits(env)[0].media.caption
    await env.press("ts:2")                                       # tanlash
    order = ["econ_ledger", "corporate_blue", "med_clinic", "it_terminal"]
    await env.press("c:20")
    await env.press("skip")
    await env.press("skip")
    assert order[2] in env.last() or "med_clinic" in env.last()   # tasdiq ekranida shablon nomi
    assert "6 500" in env.last()
    await env.press("ok")
    params = json.loads((await env.store.orders_by_status("queued"))[0]["params"])
    assert params["template"] == "med_clinic" and params["slides"] == 20


async def test_shablon_rasmi_telegramga_bir_marta_yuklanadi(env):
    await start_taqdimot(env)
    assert env.api.preview_calls == ["econ_ledger"]                # birinchi marta API'dan
    assert await env.store.tpl_file("econ_ledger")                 # file_id saqlandi
    await env.press("tn:1")
    await env.press("tn:0")                                        # qaytib kelganda keshdan
    assert env.api.preview_calls == ["econ_ledger", "corporate_blue"]
    assert edits(env)[-1].media.media.startswith("tgphoto")        # file_id bilan yuborildi, qayta yuklanmadi


async def test_shaxsiy_mavzuda_tafsilot_soraladi(env):
    await start_taqdimot(env, topic="Bizning mahalla")
    assert "sizning joyingiz" in env.last()
    await env.say('Samarqand sh., "Registon" mahallasi, maktab va bozor bor')
    assert "Dizayn shablonini" in env.last()
    await env.press("ts:0")
    await env.press("c:10")
    await env.press("skip")
    await env.press("skip")
    await env.press("ok")
    params = json.loads((await env.store.orders_by_status("queued"))[0]["params"])
    assert params["notes"].startswith("Samarqand sh.") and params["topic"] == "Bizning mahalla"


async def test_tafsilotda_tire_umumiy_yozilsin(env):
    await start_taqdimot(env, topic="Mening maktabim")
    await env.say("-")
    await env.press("ts:0")
    await env.press("c:10")
    await env.press("skip")
    await env.press("skip")
    await env.press("ok")
    params = json.loads((await env.store.orders_by_status("queued"))[0]["params"])
    assert "notes" not in params


async def test_oddiy_mavzuda_tafsilot_soralmaydi(env):
    await start_taqdimot(env)
    assert "sizning joyingiz" not in "\n".join(env.session.texts(5))


async def test_shablonlar_olinmasa_qadam_otkaziladi_va_buyurtma_beriladi(env):
    env.api.templates_fail = True
    await start_taqdimot(env)
    assert photos(env) == []
    assert "Nechta slayd" in env.last()                            # to'g'ridan-to'g'ri slaydlar soniga o'tdi
    await env.press("c:10")
    await env.press("skip")
    await env.press("skip")
    await env.press("ok")
    params = json.loads((await env.store.orders_by_status("queued"))[0]["params"])
    assert "template" not in params                                # hamkor standart shablonni qo'llaydi


async def test_eskirgan_shablon_tugmasi_rad_etiladi(env):
    await start_taqdimot(env)
    await env.press("ts:0")                                        # tanlandi, keyingi qadam
    texts_before = len(env.session.texts(5))
    await env.press("ts:1")                                        # eski karusel tugmasi
    await env.press("tn:2")
    assert len(env.session.texts(5)) == texts_before               # holat buzilmadi
    await env.press("c:10")
    assert "Taqdimotchi" in env.last() or "taqdimotchi" in env.last().lower()


async def test_shablon_nomi_hujjat_tilida(env):
    await env.store.credit(5, 50_000, "topup")
    await env.say("📊 Taqdimot")
    await env.press("c:ru")
    await env.say("Экономика")
    await env.say("Малый бизнес")
    assert "corporate_blue ru" in photos(env)[0].caption or "econ_ledger ru" in photos(env)[0].caption
