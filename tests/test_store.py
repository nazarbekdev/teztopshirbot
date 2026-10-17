async def test_yechish_va_qaytarish(store):
    await store.credit(1, 10_000, "topup")
    order_id = await store.place_order(1, "taqdimot", {"topic": "x"}, 4_500)
    assert order_id and await store.balance(1) == 5_500
    assert await store.refund_order(order_id) is True
    assert await store.refund_order(order_id) is False      # ikkinchi marta qaytmaydi
    assert await store.balance(1) == 10_000


async def test_balans_yetmasa_buyurtma_yaratilmaydi(store):
    await store.credit(1, 1_000, "topup")
    assert await store.place_order(1, "taqdimot", {}, 4_500) is None
    assert await store.balance(1) == 1_000
    assert await store.orders_by_status("queued") == []


async def test_tolov_bir_marta_tasdiqlanadi(store):
    pid = await store.new_payment(1, 5_000, "card", "pending")
    assert await store.settle_payment(pid, "pending", "approved") is not None
    assert await store.settle_payment(pid, "pending", "approved") is None


async def test_ogohlantirish_chastotasi(store):
    assert await store.alert_due("k", every=3600) is True
    assert await store.alert_due("k", every=3600) is False
    assert await store.alert_due("boshqa", every=3600) is True


async def test_ledger_har_ozgarishni_yozadi(store):
    await store.credit(1, 5_000, "topup")
    await store.place_order(1, "test", {}, 2_500)
    rows = await store._all("SELECT delta, reason FROM ledger ORDER BY id")
    assert [(r["delta"], r["reason"]) for r in rows] == [(5_000, "topup"), (-2_500, "order")]
