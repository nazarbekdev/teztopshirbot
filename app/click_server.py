"""
Click Shop API qabul qiluvchisi (Prepare / Complete). Imzo va xato kodlari asosiy
OsonTopshir botidagi bilan bir xil (`backend/click/views.py`).

Click kabinetida shu manzillar ko'rsatiladi:
    Prepare:  {PUBLIC_URL}/click/prepare
    Complete: {PUBLIC_URL}/click/complete

Xavfsizlik: imzo (`sign_string`) tekshirilmaguncha hech narsa o'zgarmaydi; summa
to'lovdagi summa bilan SOLISHTIRILADI; qayta kelgan so'rov balansni ikki marta
to'ldirmaydi (`settle_payment` holatni bir martalik o'tkazadi).
"""

import hashlib
import logging
from decimal import Decimal, InvalidOperation

from aiohttp import web

from .catalog import money
from .i18n import t

logger = logging.getLogger(__name__)

OK, SIGN_FAILED, BAD_AMOUNT, BAD_ACTION, ALREADY_PAID, NOT_FOUND, FAILED, BAD_REQUEST, CANCELLED = (
    0, -1, -2, -3, -4, -5, -7, -8, -9)


def _md5(raw: str) -> str:
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def sign_ok(data: dict, secret: str, service_id: str, *, complete: bool) -> bool:
    parts = [data.get("click_trans_id"), service_id, secret, data.get("merchant_trans_id")]
    if complete:
        parts.append(data.get("merchant_prepare_id"))
    parts += [data.get("amount"), data.get("action"), data.get("sign_time")]
    return _md5("".join(str(p) for p in parts)) == data.get("sign_string")


def _amount(value) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


async def _payment(app, data: dict):
    try:
        pid = int(data.get("merchant_trans_id"))
    except (TypeError, ValueError):
        return None
    payment = await app["store"].payment(pid)
    return payment if payment and payment["method"] == "click" else None


async def prepare(request: web.Request) -> web.Response:
    app, settings = request.app, request.app["settings"]
    data = dict(await request.post())
    if not sign_ok(data, settings.click_secret, settings.click_service_id, complete=False):
        return web.json_response({"error": SIGN_FAILED})
    payment = await _payment(app, data)
    if payment is None:
        return web.json_response({"error": NOT_FOUND})
    if _amount(data.get("amount")) != Decimal(payment["amount"]):
        return web.json_response({"error": BAD_AMOUNT})
    if payment["status"] == "paid":
        return web.json_response({"error": ALREADY_PAID})
    if payment["status"] == "cancelled":
        return web.json_response({"error": CANCELLED})
    await app["store"].set_payment(payment["id"], status="prepared", click_trans_id=int(data["click_trans_id"]))
    return web.json_response({
        "click_trans_id": int(data["click_trans_id"]), "merchant_trans_id": str(payment["id"]),
        "merchant_prepare_id": payment["id"], "error": OK,
    })


async def complete(request: web.Request) -> web.Response:
    app, settings, store = request.app, request.app["settings"], request.app["store"]
    data = dict(await request.post())
    if not sign_ok(data, settings.click_secret, settings.click_service_id, complete=True):
        return web.json_response({"error": SIGN_FAILED})
    payment = await _payment(app, data)
    if payment is None or str(payment["id"]) != str(data.get("merchant_prepare_id")):
        return web.json_response({"error": NOT_FOUND})
    if _amount(data.get("amount")) != Decimal(payment["amount"]):
        return web.json_response({"error": BAD_AMOUNT})
    reply = {"click_trans_id": int(data["click_trans_id"]), "merchant_trans_id": str(payment["id"]),
             "merchant_confirm_id": payment["id"], "error": OK}

    if str(data.get("action")) != "1":                       # Click bekor qildi
        await store.settle_payment(payment["id"], "prepared", "cancelled")
        return web.json_response({"error": OK})
    if payment["status"] == "paid":                          # qayta kelgan so'rov: idempotent
        return web.json_response(reply)

    settled = await store.settle_payment(payment["id"], "prepared", "paid")
    if settled is None:
        return web.json_response({"error": NOT_FOUND})
    await store.credit(settled["tg_id"], settled["amount"], "click_topup", f"payment:{settled['id']}")
    try:
        lang = ((await store.user(settled["tg_id"])) or {}).get("lang")
        await app["bot"].send_message(
            settled["tg_id"], t(lang, "click_paid", amount=money(settled["amount"], lang or "uz")), parse_mode="HTML")
    except Exception:
        logger.warning("Click to'lovi xabari yuborilmadi: %s", settled["tg_id"])
    return web.json_response(reply)


async def health(request: web.Request) -> web.Response:
    return web.json_response({"ok": True})


def make_app(store, settings, bot) -> web.Application:
    app = web.Application()
    app["store"], app["settings"], app["bot"] = store, settings, bot
    app.router.add_post("/click/prepare", prepare)
    app.router.add_post("/click/complete", complete)
    app.router.add_get("/health", health)
    return app
