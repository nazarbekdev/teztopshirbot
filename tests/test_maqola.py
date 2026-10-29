import json

from tests.test_flow import ADMIN, CUSTOMER, env  # noqa: F401  (fixture)


async def start_maqola(env, topic="Sun'iy intellekt ta'limda qo'llanilishi"):
    await env.store.credit(5, 50_000, "topup")
    await env.say("📰 Ilmiy maqola")
    await env.press("c:uz")
    await env.press("skipall")                      # titul ma'lumotlari (ism/universitet/yo'nalish/rahbar)
    await env.say(topic)


async def last_order_params(env):
    return json.loads((await env.store.orders_by_status("queued"))[-1]["params"])


async def test_universitet_uslubi_qisqa_oqim(env):
    await start_maqola(env)
    assert "Qaysi uslubda" in env.last() or "uslub" in env.last().lower()
    await env.press("c:universitet")
    assert "Necha bet" in env.last() or "bet" in env.last().lower()
    await env.press("c:5")
    # universitet uslubida soha va muallif ma'lumoti so'ralmaydi — to'g'ridan-to'g'ri qo'shimcha talablar
    assert "Qo'shimcha talab" in env.last()
    await env.press("skip")
    assert "12 000" in env.last()
    await env.press("ok")
    params = await last_order_params(env)
    assert params == {"language": "uz", "topic": "Sun'iy intellekt ta'limda qo'llanilishi",
                      "style": "universitet", "pages": 5}
    assert (await env.store.orders_by_status("queued"))[-1]["price"] == 12_000
    assert await env.store.balance(5) == 38_000


async def test_imrad_uslubida_soha_va_malumot_soraladi(env):
    await start_maqola(env)
    await env.press("c:imrad")
    await env.press("c:7")
    assert "soha" in env.last().lower()
    await env.press("c:it")
    assert "raqam" in env.last().lower() or "fakt" in env.last().lower()
    await env.say("Respondentlar soni: 120, o'rtacha ball 4.3")
    await env.say("Jadval ko'proq bo'lsin")
    assert "12 000" in env.last()
    await env.press("ok")
    params = await last_order_params(env)
    assert params == {"language": "uz", "topic": "Sun'iy intellekt ta'limda qo'llanilishi", "style": "imrad",
                      "pages": 7, "field": "it", "user_data": "Respondentlar soni: 120, o'rtacha ball 4.3",
                      "notes": "Jadval ko'proq bo'lsin"}


async def test_oak_uslubida_hajm_7_yoki_10(env):
    await start_maqola(env)
    await env.press("c:oak")
    buttons = [b.callback_data for m in env.session.calls if getattr(m, "reply_markup", None)
               and hasattr(m.reply_markup, "inline_keyboard")
               for row in m.reply_markup.inline_keyboard for b in row if b.callback_data.startswith("c:")][-2:]
    assert buttons == ["c:7", "c:10"]
    await env.press("c:10")
    await env.press("c:med")
    await env.press("skip")                          # muallif ma'lumoti ixtiyoriy
    await env.press("skip")                           # qo'shimcha talablar ixtiyoriy
    await env.press("ok")
    params = await last_order_params(env)
    assert params["style"] == "oak" and params["pages"] == 10 and params["field"] == "med"
    assert "user_data" not in params and "notes" not in params


async def test_titul_malumotlari_saqlanadi_va_qayta_taklif_qilinadi(env):
    await env.store.credit(5, 50_000, "topup")
    await env.say("📰 Ilmiy maqola")
    await env.press("c:uz")
    await env.say("Ali Valiyev")
    await env.press("skipall")
    await env.say("Raqamli iqtisodiyot tendensiyalari")
    await env.press("c:universitet")
    await env.press("c:5")
    await env.press("skip")
    await env.press("ok")
    assert (await env.store.profile(5)) == {"full_name": "Ali Valiyev"}

    await env.say("📰 Ilmiy maqola")
    await env.press("c:uz")
    assert "Ali Valiyev" in env.last()
    await env.press("prof:yes")
    assert "Mavzu" in env.last() or "mavzu" in env.last().lower()


async def test_narx_va_menyuda_korinishi(env):
    await env.say("/start")
    assert "12 000" in env.last() and ("Ilmiy maqola" in env.last() or "📰" in env.last())


async def test_promokod_maqolaga_tegishli_emas(env):
    await env.store.create_promo("TEZSTART", ["test"], None, None)
    await env.store.redeem("TEZSTART", 5)
    await start_maqola(env)
    await env.press("c:universitet")
    await env.press("c:5")
    await env.press("skip")
    assert "bepul" not in env.last().lower()
