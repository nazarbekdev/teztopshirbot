import json

from app.catalog import SERVICES
from tests.test_flow import ADMIN, CUSTOMER, env  # noqa: F401  (fixture)


async def start_pro(env, subject="Iqtisodiyot", topic="Qayta tiklanuvchi energiya manbalari"):
    await env.store.credit(5, 50_000, "topup")
    await env.say("✨ Taqdimot Pro")
    await env.press("c:uz")
    await env.say(subject)
    await env.say(topic)


async def last_order_params(env):
    return json.loads((await env.store.orders_by_status("queued"))[-1]["params"])


async def test_narxlar_pogonalari_va_tanlovda_korinishi(env):
    s = SERVICES["taqdimot_pro"]
    assert s.is_tiered and s.price == {10: 9_000, 15: 11_000, 20: 13_000}
    step = next(st for st in s.steps if st.key == "slides")
    assert {int(v) for v, _ in step.choices} == {10, 15, 20}      # 25/30 yo'q — hamkor API qabul qilmaydi


async def test_toliq_oqim_shablon_sorlmaydi(env):
    await start_pro(env)
    assert "Dizayn" not in env.last() and "shablon" not in env.last().lower()   # shablon tanlash yo'q
    await env.press("c:15")
    await env.press("skip")
    await env.press("skip")
    assert "11 000" in env.last()
    await env.press("ok")
    params = await last_order_params(env)
    assert params == {"language": "uz", "subject": "Iqtisodiyot",
                      "topic": "Qayta tiklanuvchi energiya manbalari", "slides": 15}
    assert "template" not in params
    assert (await env.store.orders_by_status("queued"))[-1]["price"] == 11_000
    assert await env.store.balance(5) == 39_000


async def test_taqdimotchi_va_rahbar_toldiriladi(env):
    await start_pro(env)
    await env.press("c:10")
    await env.say("Aliyev Vali")
    await env.say("Prof. Karimov S.")
    await env.press("ok")
    params = await last_order_params(env)
    assert params["presenter"] == "Aliyev Vali" and params["supervisor"] == "Prof. Karimov S."
    assert params["slides"] == 10 and (await env.store.orders_by_status("queued"))[-1]["price"] == 9_000


async def test_shaxsiy_mavzuda_tafsilot_soraladi(env):
    await env.store.credit(5, 50_000, "topup")
    await env.say("✨ Taqdimot Pro")
    await env.press("c:uz")
    await env.say("Iqtisodiyot")
    await env.say("Bizning mahalla")
    assert "sizning joyingiz" in env.last()
    await env.say("Samarqand sh., Registon mahallasi")
    await env.press("c:20")
    await env.press("skip")
    await env.press("skip")
    await env.press("ok")
    params = await last_order_params(env)
    assert params["notes"] == "Samarqand sh., Registon mahallasi" and params["topic"] == "Bizning mahalla"


async def test_promokodga_tegishli_emas(env):
    await env.store.create_promo("TEZSTART", ["test"], None, None)
    await env.store.redeem("TEZSTART", 5)
    await start_pro(env)
    await env.press("c:10")
    await env.press("skip")
    await env.press("skip")
    assert "bepul" not in env.last().lower()


async def test_qabul_xabari_animatsiya_uchun_saqlanadi(env):
    await start_pro(env)
    await env.press("c:10")
    await env.press("skip")
    await env.press("skip")
    await env.press("ok")
    oid = (await env.store.orders_by_status("queued"))[-1]["id"]
    order = await env.store.order(oid)
    assert order["notify_msg_id"]


async def test_narx_menyuda_dan_korinishi(env):
    await env.say("/start")
    assert "9 000" in env.last() and "Taqdimot Pro" in env.last()
