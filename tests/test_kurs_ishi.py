import json

from app import casedata
from tests.test_flow import ADMIN, CUSTOMER, env  # noqa: F401  (fixture)

CASE = 'Korxona: «Toshkent Tekstil» MChJ\n2022: tushum 120 mln, debitorlik 18 mln\n2023: tushum 150 mln, debitorlik 27 mln'


async def start_kurs(env, lang="uz", skip_titul=True):
    await env.store.credit(5, 200_000, "topup")
    await env.say("📖 Kurs ishi")
    await env.press(f"c:{lang}")
    if skip_titul:
        await env.say("Ali Valiyev")
        await env.press("skipall")
    await env.say("Menejment")
    await env.say("Korxonada boshqaruv tizimi")


async def params_of_last_order(env):
    return json.loads((await env.store.orders_by_status("queued"))[-1]["params"])


async def finish(env, pages="20-30"):
    await env.press(f"c:{pages}")
    await env.press("ok")
    return await params_of_last_order(env)


def test_korxona_malumoti_qoidasi_api_bilan_bir_xil():
    assert casedata.clean(CASE).startswith("Korxona:")
    for bad in ("yo'q", "нет", "-", "", None, "qisqa 123", "Korxona nomi bor, lekin raqamsiz matn bu yerda yozilgan"):
        assert casedata.clean(bad) == "", bad
    assert len(casedata.clean("1 " * 5000)) <= casedata.MAX_CHARS


async def test_toliq_avtomatik_reja_oqimi(env):
    await start_kurs(env)
    assert "Kurs ishi rejasi" in env.last() or "reja" in env.last().lower()
    await env.press("c:auto")
    assert "Bob va bo'lim" in env.last()
    await env.press("c:3_2")
    assert env.api.plan_calls == [{"topic": "Korxonada boshqaruv tizimi", "subject": "Menejment", "language": "uz",
                                   "bob_count": 3, "bolim_per_bob": 2}]
    assert "Nazariy asoslar v1" in env.last()                       # reja ko'rsatildi
    await env.press("plan:ok")
    assert "Qo'shimcha talablaringiz" in env.last()
    await env.press("skip")
    await env.press("c:yes")                                        # diagramma
    await env.press("c:no")                                         # rasm
    await env.press("c:no")                                         # snoska
    params = await finish(env, "30-40")
    assert params["plan"].startswith("1-bob. Nazariy asoslar v1")
    assert (params["bob_count"], params["bolim_per_bob"]) == (3, 2)
    assert (params["has_diagrams"], params["has_images"], params["has_footnotes"]) == (True, False, False)
    assert params["pages"] == "30-40" and params["language"] == "uz"
    assert "extra_instructions" not in params and "case_data" not in params
    assert (await env.store.orders_by_status("queued"))[0]["price"] == 65_000


async def test_qayta_generatsiya_oxirgi_rejani_oladi(env):
    await start_kurs(env)
    await env.press("c:auto")
    await env.press("c:2_3")
    await env.press("plan:regen")
    assert len(env.api.plan_calls) == 2 and "v2" in env.last()
    await env.press("plan:ok")
    for cb in ("skip", "c:yes", "c:no", "c:yes"):
        await env.press(cb)
    assert "v2" in (await finish(env))["plan"]


async def test_oz_rejasini_yozish(env):
    await start_kurs(env)
    await env.press("c:manual")
    assert "Kurs ishi rejangizni yuboring" in env.last()
    await env.say("qisqa")                                          # 10 belgidan kam
    assert "belgi" in env.last()
    await env.say("1-bob. Nazariy asoslar\n1.1 Tushuncha\n2-bob. Tahlil")
    assert env.api.plan_calls == []                                 # avto-reja so'ralmadi
    for cb in ("skip", "c:no", "c:no", "c:yes"):
        await env.press(cb)
    params = await finish(env)
    assert params["plan"].startswith("1-bob. Nazariy") and "bob_count" not in params


async def test_qoshimcha_talab_va_korxona_malumoti(env):
    await start_kurs(env)
    await env.press("c:manual")
    await env.say("1-bob. Nazariy asoslar\n1.1 Tushuncha\n2-bob. Tahlil")
    await env.press("case:open")                                    # «Korxona ma'lumotini kiritish»
    assert "HAQIQIY korxona" in env.last()
    await env.say("yo'q")
    assert "Raqamlar topilmadi" in env.last()                       # yaroqsiz — qayta so'raladi
    await env.say(CASE)
    assert "qabul qilindi" in "\n".join(env.session.texts(5)[-2:])
    for cb in ("c:yes", "c:yes", "c:yes"):
        await env.press(cb)
    params = await finish(env)
    assert params["case_data"] == CASE and "extra_instructions" not in params


async def test_qoshimcha_talab_matni(env):
    await start_kurs(env)
    await env.press("c:manual")
    await env.say("1-bob. Nazariy asoslar\n1.1 Tushuncha\n2-bob. Tahlil")
    await env.say("Jadvallar ko'proq bo'lsin")
    for cb in ("c:no", "c:no", "c:no"):
        await env.press(cb)
    params = await finish(env)
    assert params["extra_instructions"] == "Jadvallar ko'proq bo'lsin"
    assert (params["has_diagrams"], params["has_images"], params["has_footnotes"]) == (False, False, False)


async def test_korxona_malumotini_otkazib_yuborish(env):
    await start_kurs(env)
    await env.press("c:manual")
    await env.say("1-bob. Nazariy asoslar\n1.1 Tushuncha\n2-bob. Tahlil")
    await env.press("case:open")
    await env.press("skip")
    for cb in ("c:no", "c:no", "c:no"):
        await env.press(cb)
    assert "case_data" not in await finish(env)


async def test_reja_olinmasa_qadam_otkaziladi_buyurtma_beriladi(env):
    env.api.plan_fail = True
    await start_kurs(env)
    await env.press("c:auto")
    await env.press("c:2_2")
    assert "avtomatik tuziladi" in "\n".join(env.session.texts(5)[-3:])
    assert "Qo'shimcha talablaringiz" in env.last()                  # oqim to'xtamadi
    for cb in ("skip", "c:no", "c:no", "c:yes"):
        await env.press(cb)
    params = await finish(env)
    assert "plan" not in params and (params["bob_count"], params["bolim_per_bob"]) == (2, 2)


async def test_7_til_tanlash(env):
    await env.store.credit(5, 200_000, "topup")
    await env.say("📖 Kurs ishi")
    buttons = [b.callback_data for m in env.session.calls if getattr(m, "reply_markup", None) and hasattr(m.reply_markup, "inline_keyboard")
               for row in m.reply_markup.inline_keyboard for b in row if b.callback_data.startswith("c:")]
    assert buttons == ["c:uz", "c:ru", "c:en", "c:kz", "c:tr", "c:tj", "c:kaa"]
    await env.press("c:kaa")
    await env.say("Ali Valiyev")
    await env.press("skipall")
    await env.say("Menejment")
    await env.say("Korxonada boshqaruv tizimi")
    await env.press("c:manual")
    await env.say("1-bob. Nazariy asoslar\n1.1 Tushuncha\n2-bob. Tahlil")
    for cb in ("skip", "c:no", "c:no", "c:no"):
        await env.press(cb)
    assert (await finish(env))["language"] == "kaa"


async def test_qisqa_mavzu_va_fan_qabul_qilinmaydi(env):
    await env.store.credit(5, 100_000, "topup")
    await env.say("📖 Kurs ishi")
    await env.press("c:uz")
    await env.say("Ali Valiyev")
    await env.press("skipall")
    await env.say("Fan")                                            # 3 belgi — fan uchun kamida 4
    assert "belgi" in env.last()
    await env.say("Menejment")
    await env.say("Qisqa")                                          # mavzu uchun kamida 10
    assert "belgi" in env.last()
    await env.say("Qisqa mavzu!!")
    assert "Kurs ishi rejasi" in env.last() or "reja" in env.last().lower()


async def test_tasdiq_ekranida_reja_toliq_chiqmaydi(env):
    await start_kurs(env)
    await env.press("c:manual")
    await env.say("1-bob. " + "Juda uzun reja nomi " * 20)
    for cb in ("skip", "c:no", "c:no", "c:no", "c:20-30"):
        await env.press(cb)
    assert "…" in env.last() and len(env.last()) < 1500


async def test_promokod_kurs_ishiga_tegishli_emas_lekin_oqim_buzilmaydi(env):
    await env.store.create_promo("TEZSTART", ["test"], None, None)
    await env.store.redeem("TEZSTART", 5)
    await start_kurs(env)
    await env.press("c:manual")
    await env.say("1-bob. Nazariy asoslar\n1.1 Tushuncha\n2-bob. Tahlil")
    for cb in ("skip", "c:no", "c:no", "c:no", "c:20-30"):
        await env.press(cb)
    assert "bepul" not in env.last().lower()
