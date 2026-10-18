"""Web admin panel yo'llari. Pul amallari FAQAT `Store` / `payments` orqali (botdagi yo'l bilan bir xil)."""

import io
import json
import logging
import pathlib
import time
from datetime import datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import jinja2
from aiohttp import web

from .. import payments, ui
from ..catalog import ORDER, SERVICES, money, pick
from . import auth

logger = logging.getLogger(__name__)
HERE = pathlib.Path(__file__).parent
TZ = ZoneInfo("Asia/Tashkent")
PAGE = 50
STATUSES = ("queued", "submitted", "processing", "succeeded", "failed", "canceled")

env = jinja2.Environment(loader=jinja2.FileSystemLoader(HERE / "templates"), autoescape=True)
env.filters["money"] = lambda v: money(int(v or 0), "uz")
env.filters["dt"] = lambda ts: datetime.fromtimestamp(ts, TZ).strftime("%d.%m.%Y %H:%M") if ts else "—"


async def render(request: web.Request, template: str, **ctx) -> web.Response:
    store = request.app["store"]
    q = request.query
    flash = ("ok", q["ok"]) if q.get("ok") else ("err", q["err"]) if q.get("err") else None
    body = env.get_template(template).render(
        csrf=request["csrf"], pending=await store.pending_card_payments(), flash=flash, **ctx)
    return web.Response(text=body, content_type="text/html")


def back(path: str, **msg) -> web.HTTPFound:
    return web.HTTPFound(path + ("?" + urlencode(msg) if msg else ""))


# ── kirish ───────────────────────────────────────────────────────────────

async def login_page(request: web.Request) -> web.Response:
    if not auth.login_rate_ok(auth.client_ip(request)):
        raise web.HTTPTooManyRequests(text="Juda ko'p urinish. Bir daqiqadan so'ng qayta urining.")
    nonce, secret = await auth.start_login(request)
    username = request.app["bot_username"]
    link = f"https://t.me/{username}?start=alogin_{nonce}"
    response = web.Response(text=env.get_template("login.html").render(link=link), content_type="text/html")
    auth.set_cookie(response, auth.LOGIN_COOKIE, f"{nonce}:{secret}", request, auth.LOGIN_TTL * 2)
    response.headers.update({"Cache-Control": "no-store", "X-Frame-Options": "DENY",
                             "Content-Security-Policy": "default-src 'self'; style-src 'unsafe-inline'; script-src 'self'"})
    return response


async def poll(request: web.Request) -> web.Response:
    store = request.app["store"]
    nonce = request.cookies.get(auth.LOGIN_COOKIE, "").partition(":")[0]
    row = await store.login(nonce) if nonce else None
    if row is None or row["status"] in ("denied", "used") or time.time() - row["created_at"] > auth.LOGIN_TTL:
        return web.json_response({"status": "denied"})
    if row["status"] == "pending":
        return web.json_response({"status": "pending"})
    done = await auth.finish_login(request)
    if done is None:
        return web.json_response({"status": "denied"})
    token, _ = done
    response = web.json_response({"status": "ok"})
    auth.set_cookie(response, auth.COOKIE, token, request, auth.SESSION_TTL)
    response.del_cookie(auth.LOGIN_COOKIE)
    return response


async def logout(request: web.Request) -> web.Response:
    await request.app["store"].drop_session(request["token_hash"])
    response = web.HTTPFound("/login")
    response.del_cookie(auth.COOKIE)
    raise response


async def poll_js(request: web.Request) -> web.Response:
    return web.Response(text=(HERE / "poll.js").read_text(), content_type="application/javascript")


async def health(request: web.Request) -> web.Response:
    return web.json_response({"ok": True})


# ── bosh sahifa ──────────────────────────────────────────────────────────

async def dashboard(request: web.Request) -> web.Response:
    app, store = request.app, request.app["store"]
    credits, error = [], ""
    try:
        remote = await app["api"].credits()
        for slug in ORDER:
            spec, row = SERVICES[slug], remote.get(slug, {})
            cost = row.get("unit_price")
            credits.append({"emoji": spec.emoji, "title": pick(spec.title, "uz"), "credits": row.get("credits", 0),
                            "cost": cost, "price_label": ui.price_line(slug, "uz"),
                            "margin": (spec.min_price - cost) if cost else None})
    except Exception as e:
        error = str(e)[:200]
    return await render(request, "dashboard.html", active="dash", s=await store.stats(), credits=credits,
                        credits_error=error, mode="TEST" if app["settings"].test_mode else "LIVE",
                        orders=await store.find_orders(limit=10))


# ── buyurtmalar ──────────────────────────────────────────────────────────

async def orders_list(request: web.Request) -> web.Response:
    q, store = request.query, request.app["store"]
    f = {"status": q.get("status", ""), "service": q.get("service", ""), "user": q.get("user", "").strip()}
    page = max(int(q.get("page", "0") or 0), 0)
    rows = await store.find_orders(f["status"] if f["status"] in STATUSES else "", f["service"] if f["service"] in SERVICES else "",
                                   int(f["user"]) if f["user"].isdigit() else None, PAGE + 1, page * PAGE)
    qs = urlencode({k: v for k, v in f.items() if v})
    return await render(request, "orders.html", active="orders", orders=rows[:PAGE], has_more=len(rows) > PAGE,
                        page=page, qs=qs, f=f, statuses=STATUSES, services=ORDER)


async def order_detail(request: web.Request) -> web.Response:
    store = request.app["store"]
    order = await store.order(int(request.match_info["id"]))
    if order is None:
        raise web.HTTPNotFound()
    user = await store.user(order["tg_id"]) or {"name": "?", "username": None}
    can_refund = not order["refunded"] and order["status"] in ("failed", "canceled", "queued")
    params = json.dumps(json.loads(order["params"]), ensure_ascii=False, indent=2)
    return await render(request, "order.html", active="orders", o=order, user=user, params=params, can_refund=can_refund)


async def order_refund(request: web.Request) -> web.Response:
    store, admin_id = request.app["store"], request["admin_id"]
    oid = int(request.match_info["id"])
    order = await store.order(oid)
    if order is None:
        raise web.HTTPNotFound()
    if order["status"] == "queued" and not await store.cancel_queued(oid):
        raise back(f"/orders/{oid}", err="Buyurtma hozirgina hamkorga yuborildi — qaytarib bo'lmaydi.")
    order = await store.order(oid)
    if order["status"] not in ("failed", "canceled") or not await store.refund_order(oid):
        raise back(f"/orders/{oid}", err="Bu buyurtma uchun pulni qaytarib bo'lmaydi (allaqachon qaytarilgan yoki tayyorlanmoqda).")
    await store.audit(admin_id, "order_refund", f"#{oid} {order['price']} → {order['tg_id']}")
    raise back(f"/orders/{oid}", ok="Pul mijoz balansiga qaytarildi.")


# ── foydalanuvchilar ─────────────────────────────────────────────────────

async def users_list(request: web.Request) -> web.Response:
    q = request.query.get("q", "")
    return await render(request, "users.html", active="users", q=q, users=await request.app["store"].search_users(q))


async def user_detail(request: web.Request) -> web.Response:
    store = request.app["store"]
    tg_id = int(request.match_info["tg_id"])
    user = await store.user(tg_id)
    if user is None:
        raise web.HTTPNotFound()
    return await render(request, "user.html", active="users", u=user, orders=await store.find_orders(tg_id=tg_id, limit=20),
                        ledger=await store.user_ledger(tg_id))


async def user_balance(request: web.Request) -> web.Response:
    store, admin_id = request.app["store"], request["admin_id"]
    tg_id = int(request.match_info["tg_id"])
    form = await request.post()
    reason = " ".join(str(form.get("reason", "")).split())[:100]
    try:
        amount = int(str(form.get("amount", "")).strip())
    except ValueError:
        amount = 0
    if not reason or amount == 0 or abs(amount) > payments.MAX_AMOUNT:
        raise back(f"/users/{tg_id}", err="Summa va sabab to'g'ri kiritilishi kerak.")
    if not await store.adjust_balance(tg_id, amount, reason):
        raise back(f"/users/{tg_id}", err="Bajarilmadi: foydalanuvchi topilmadi yoki balans yetmaydi.")
    await store.audit(admin_id, "balance_adjust", f"{tg_id} {amount:+d}: {reason}")
    raise back(f"/users/{tg_id}", ok=f"Balans o'zgartirildi: {amount:+d} so'm.")


# ── to'lovlar ────────────────────────────────────────────────────────────

async def payments_list(request: web.Request) -> web.Response:
    status = request.query.get("status", "pending")
    return await render(request, "payments.html", active="payments",
                        payments=await request.app["store"].list_payments(status if status in ("pending", "approved", "rejected", "paid") else ""))


async def receipt(request: web.Request) -> web.Response:
    payment = await request.app["store"].payment(int(request.match_info["id"]))
    if payment is None or not payment["receipt_file_id"]:
        raise web.HTTPNotFound()
    buffer = io.BytesIO()
    await request.app["bot"].download(payment["receipt_file_id"], destination=buffer)
    return web.Response(body=buffer.getvalue(), content_type="image/jpeg")


async def payment_decide(request: web.Request) -> web.Response:
    store, bot, admin_id = request.app["store"], request.app["bot"], request["admin_id"]
    pid, action = int(request.match_info["id"]), request.match_info["action"]
    form = await request.post()
    if action == "edit":
        try:
            amount = int(str(form.get("amount", "")).strip())
        except ValueError:
            amount = 0
        payment = await payments.edit_amount(store, pid, amount)
        if payment is None:
            raise back("/payments", err="Summa noto'g'ri yoki to'lov allaqachon ko'rib chiqilgan.")
        await store.audit(admin_id, "payment_edit", f"#{pid} {payment['original_amount']}→{amount}")
        raise back("/payments", ok=f"#{pid} summasi yangilandi. Endi tasdiqlang.")
    decide = payments.approve if action == "approve" else payments.reject
    payment = await decide(store, bot, pid, admin_id)
    if payment is None:
        raise back("/payments", err="Bu to'lov allaqachon ko'rib chiqilgan.")
    await store.audit(admin_id, f"payment_{action}", f"#{pid} {payment['amount']}")
    raise back("/payments", ok=f"#{pid} {'tasdiqlandi' if action == 'approve' else 'rad etildi'}.")


async def audit_log(request: web.Request) -> web.Response:
    return await render(request, "audit.html", active="audit", audit=await request.app["store"].recent_audit())


def make_app(store, settings, bot, api, bot_username: str) -> web.Application:
    app = web.Application(middlewares=[auth.security])
    app["store"], app["settings"], app["bot"], app["api"], app["bot_username"] = store, settings, bot, api, bot_username
    r = app.router
    r.add_get("/login", login_page)
    r.add_get("/auth/poll", poll)
    r.add_get("/static/poll.js", poll_js)
    r.add_get("/health", health)
    r.add_post("/logout", logout)
    r.add_get("/", dashboard)
    r.add_get("/orders", orders_list)
    r.add_get(r"/orders/{id:\d+}", order_detail)
    r.add_post(r"/orders/{id:\d+}/refund", order_refund)
    r.add_get("/users", users_list)
    r.add_get(r"/users/{tg_id:\d+}", user_detail)
    r.add_post(r"/users/{tg_id:\d+}/balance", user_balance)
    r.add_get("/payments", payments_list)
    r.add_get(r"/payments/{id:\d+}/receipt", receipt)
    r.add_post(r"/payments/{id:\d+}/{action:approve|reject|edit}", payment_decide)
    r.add_get("/audit", audit_log)
    return app
