"""
Panelga kirish: parol YO'Q — Telegram orqali tasdiqlash.

Oqim: brauzer `/login` ochadi → bir martalik so'rov (nonce + brauzerga bog'langan sir) yaratiladi →
admin botda `/start alogin_<nonce>` havolasini ochadi → bot IP va brauzerni ko'rsatib «Ruxsat» so'raydi →
brauzer `/auth/poll` orqali sessiya cookie'sini oladi.

Nega shunday:
  · parol/2FA saqlash va tiklash kerak emas; admin allaqachon Telegram'da;
  · so'rovni boshlagan brauzergina sessiya oladi (cookie'dagi sir) — begona so'rovni admin
    tasodifan tasdiqlasa ham, sessiya unga emas, so'rov boshlagan brauzerga beriladi, shuning
    uchun botdagi xabarda IP va brauzer ko'rsatiladi: admin begonani rad etadi;
  · tokenlar bazada faqat xesh ko'rinishida; sessiya 12 soat; POST'lar CSRF tokeni bilan.
"""

import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque

from aiohttp import web

SESSION_TTL = 12 * 3600
LOGIN_TTL = 300
COOKIE = "tz_admin"
LOGIN_COOKIE = "tz_lp"
PUBLIC = ("/login", "/auth/poll", "/health", "/static/poll.js")
_login_hits: dict[str, deque] = defaultdict(deque)


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def client_ip(request: web.Request) -> str:
    # nginx ortida: Real-IP faqat loopback'dan kelganda ishoniladi
    if request.remote in ("127.0.0.1", "::1"):
        return request.headers.get("X-Real-IP") or request.remote or "?"
    return request.remote or "?"


def login_rate_ok(ip: str, limit: int = 10, window: int = 60) -> bool:
    hits = _login_hits[ip]
    cutoff = time.monotonic() - window
    while hits and hits[0] < cutoff:
        hits.popleft()
    if len(hits) >= limit:
        return False
    hits.append(time.monotonic())
    return True


def set_cookie(response: web.StreamResponse, name: str, value: str, request: web.Request, max_age: int) -> None:
    secure = request.app["settings"].panel_url.startswith("https://")
    response.set_cookie(name, value, max_age=max_age, httponly=True, secure=secure, samesite="Lax", path="/")


@web.middleware
async def security(request: web.Request, handler):
    path = request.path
    if path not in PUBLIC:
        token = request.cookies.get(COOKIE, "")
        session = await request.app["store"].session(h(token)) if token else None
        if session is None:
            raise web.HTTPFound("/login")
        request["admin_id"], request["csrf"], request["token_hash"] = session["admin_id"], session["csrf"], h(token)
        if request.app["settings"].admin_ids and session["admin_id"] not in request.app["settings"].admin_ids:
            raise web.HTTPFound("/login")           # adminlikdan chiqarilgan odam sessiyasi ishlamaydi
        if request.method == "POST":
            form = await request.post()
            if not hmac.compare_digest(str(form.get("csrf", "")), session["csrf"]):
                raise web.HTTPForbidden(text="CSRF tekshiruvi o'tmadi")
    response = await handler(request)
    response.headers.update({
        "Cache-Control": "no-store",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'self'; img-src 'self'; style-src 'unsafe-inline'; script-src 'self'; form-action 'self'",
    })
    return response


async def start_login(request: web.Request) -> tuple[str, str]:
    store = request.app["store"]
    nonce, secret = secrets.token_urlsafe(9), secrets.token_urlsafe(24)
    await store.new_login(nonce, h(secret), client_ip(request), request.headers.get("User-Agent", ""))
    return nonce, secret


async def finish_login(request: web.Request) -> tuple[str, str] | None:
    """Tasdiqlangan so'rov egasiga sessiya beradi: (token, csrf). Aks holda None."""
    store = request.app["store"]
    raw = request.cookies.get(LOGIN_COOKIE, "")
    nonce, _, secret = raw.partition(":")
    row = await store.login(nonce) if nonce else None
    if row is None or time.time() - row["created_at"] > LOGIN_TTL * 2:
        return None
    if not hmac.compare_digest(row["secret_hash"], h(secret)):
        return None
    if not await store.move_login(nonce, "approved", "used"):
        return None
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
    await store.create_session(h(token), row["admin_id"], csrf, SESSION_TTL)
    await store.audit(row["admin_id"], "panel_login", f"ip={row['ip']}")
    return token, csrf
