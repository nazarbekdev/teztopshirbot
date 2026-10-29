"""
SQLite ombori. Bitta jarayon, bitta ulanish: yozuvlar ketma-ket bajariladi, shuning
uchun balans amallari poyga holatisiz (har biri bitta UPDATE ... WHERE).

Pul qoidasi: balans FAQAT `Store.credit` / `Store.debit` orqali o'zgaradi va har
o'zgarish `ledger` ga yoziladi — "pul qayerga ketdi" savoliga javob shu jadvalda.
"""

import json
import time

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    tg_id INTEGER PRIMARY KEY,
    name TEXT, username TEXT,
    balance INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    last_seen INTEGER
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER NOT NULL,
    service TEXT NOT NULL,
    params TEXT NOT NULL,
    price INTEGER NOT NULL,
    status TEXT NOT NULL,              -- queued | submitted | processing | succeeded | failed | canceled
    partner_order_id TEXT,
    error TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_try_at INTEGER NOT NULL DEFAULT 0,
    delivered INTEGER NOT NULL DEFAULT 0,
    refunded INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS orders_user ON orders(tg_id, id);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    method TEXT NOT NULL,              -- card | click
    status TEXT NOT NULL,              -- pending | approved | rejected | prepared | paid | cancelled
    receipt_file_id TEXT,
    click_trans_id INTEGER,
    admin_id INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER NOT NULL,
    delta INTEGER NOT NULL,
    reason TEXT NOT NULL,
    ref TEXT,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS promo_codes (
    code TEXT PRIMARY KEY,
    services TEXT NOT NULL,            -- JSON: bepul olinadigan xizmatlar ro'yxati
    max_uses INTEGER,                  -- NULL = cheksiz
    expires_at INTEGER,                -- NULL = muddatsiz
    active INTEGER NOT NULL DEFAULT 1,
    note TEXT,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS vouchers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    status TEXT NOT NULL,              -- active | used
    order_id INTEGER,
    created_at INTEGER NOT NULL,
    used_at INTEGER,
    UNIQUE(code, tg_id)                -- bitta foydalanuvchi bitta kodni bir marta kiritadi
);
CREATE TABLE IF NOT EXISTS tpl_files (
    template_id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fsm (
    key TEXT PRIMARY KEY,
    state TEXT,
    data TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS admin_login (
    nonce TEXT PRIMARY KEY,
    secret_hash TEXT NOT NULL,
    status TEXT NOT NULL,              -- pending | approved | denied | used
    admin_id INTEGER,
    ip TEXT, agent TEXT,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS admin_sessions (
    token_hash TEXT PRIMARY KEY,
    admin_id INTEGER NOT NULL,
    csrf TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS admin_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    detail TEXT,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    key TEXT PRIMARY KEY,
    sent_at INTEGER NOT NULL
);
"""


def now() -> int:
    return int(time.time())


class Store:
    def __init__(self, path: str):
        self.path = path
        self.db: aiosqlite.Connection | None = None

    # Eski bazalarga keyin qo'shilgan ustunlar (CREATE TABLE ularni qayta yaratmaydi)
    MIGRATIONS = (
        ("users", "lang", "TEXT"),
        ("users", "consent_version", "TEXT"),
        ("users", "consent_at", "INTEGER"),
        ("users", "profile", "TEXT"),
        ("orders", "tg_files", "TEXT"),
        ("orders", "voucher_id", "INTEGER"),
        ("orders", "notify_msg_id", "INTEGER"),
        ("payments", "original_amount", "INTEGER"),
    )

    async def open(self) -> "Store":
        self.db = await aiosqlite.connect(self.path)
        self.db.row_factory = aiosqlite.Row
        await self.db.execute("PRAGMA journal_mode=WAL")
        await self.db.executescript(SCHEMA)
        for table, column, kind in self.MIGRATIONS:
            cols = {r["name"] for r in await self._all(f"PRAGMA table_info({table})")}
            if column not in cols:
                await self.db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {kind}")
        await self.db.commit()
        return self

    async def close(self) -> None:
        if self.db:
            await self.db.close()

    async def _one(self, sql: str, args: tuple = ()):
        cur = await self.db.execute(sql, args)
        row = await cur.fetchone()
        await cur.close()
        return dict(row) if row else None

    async def _all(self, sql: str, args: tuple = ()) -> list[dict]:
        cur = await self.db.execute(sql, args)
        rows = await cur.fetchall()
        await cur.close()
        return [dict(r) for r in rows]

    # ── foydalanuvchi ────────────────────────────────────────────────────
    async def touch_user(self, tg_id: int, name: str, username: str | None) -> dict:
        await self.db.execute(
            "INSERT INTO users(tg_id, name, username, created_at, last_seen) VALUES(?,?,?,?,?) "
            "ON CONFLICT(tg_id) DO UPDATE SET name=excluded.name, username=excluded.username, "
            "last_seen=excluded.last_seen",
            (tg_id, name, username, now(), now()),
        )
        await self.db.commit()
        return await self.user(tg_id)

    async def user(self, tg_id: int) -> dict | None:
        return await self._one("SELECT * FROM users WHERE tg_id=?", (tg_id,))

    async def set_lang(self, tg_id: int, lang: str) -> None:
        await self.db.execute("UPDATE users SET lang=? WHERE tg_id=?", (lang, tg_id))
        await self.db.commit()

    async def accept_consent(self, tg_id: int, version: str) -> None:
        await self.db.execute("UPDATE users SET consent_version=?, consent_at=? WHERE tg_id=?",
                              (version, now(), tg_id))
        await self.db.commit()

    async def profile(self, tg_id: int) -> dict:
        row = await self.user(tg_id)
        return json.loads(row["profile"]) if row and row["profile"] else {}

    async def save_profile(self, tg_id: int, fields: dict) -> None:
        """Titul ma'lumotlari: yangi qiymatlar eskisiga qo'shiladi, bo'sh qiymat o'chirmaydi."""
        merged = {**await self.profile(tg_id), **{k: v for k, v in fields.items() if v}}
        await self.db.execute("UPDATE users SET profile=? WHERE tg_id=?",
                              (json.dumps(merged, ensure_ascii=False), tg_id))
        await self.db.commit()

    async def balance(self, tg_id: int) -> int:
        row = await self.user(tg_id)
        return row["balance"] if row else 0

    # ── balans (yagona kirish nuqtasi) ───────────────────────────────────
    async def credit(self, tg_id: int, amount: int, reason: str, ref: str = "") -> None:
        assert amount > 0
        await self.db.execute("UPDATE users SET balance=balance+? WHERE tg_id=?", (amount, tg_id))
        await self.db.execute(
            "INSERT INTO ledger(tg_id, delta, reason, ref, created_at) VALUES(?,?,?,?,?)",
            (tg_id, amount, reason, ref, now()),
        )
        await self.db.commit()

    async def debit(self, tg_id: int, amount: int, reason: str, ref: str = "") -> bool:
        """Yetarli bo'lsa yechadi (True), bo'lmasa hech narsa qilmaydi (False)."""
        assert amount > 0
        cur = await self.db.execute(
            "UPDATE users SET balance=balance-? WHERE tg_id=? AND balance>=?", (amount, tg_id, amount)
        )
        ok = cur.rowcount == 1
        await cur.close()
        if ok:
            await self.db.execute(
                "INSERT INTO ledger(tg_id, delta, reason, ref, created_at) VALUES(?,?,?,?,?)",
                (tg_id, -amount, reason, ref, now()),
            )
        await self.db.commit()
        return ok

    # ── buyurtmalar ──────────────────────────────────────────────────────
    async def place_order(self, tg_id: int, service: str, params: dict, price: int,
                          max_active: int | None = None) -> int | str | None:
        """
        Balansdan yechib buyurtma yaratadi. Balans yetmasa None; foydalanuvchining faol
        buyurtmalari `max_active` ga yetgan bo'lsa "limit" (pul yechilmaydi).
        """
        if max_active is not None and await self.active_count(tg_id) >= max_active:
            return "limit"
        if not await self.debit(tg_id, price, "order", service):
            return None
        cur = await self.db.execute(
            "INSERT INTO orders(tg_id, service, params, price, status, created_at, updated_at) "
            "VALUES(?,?,?,?, 'queued', ?, ?)",
            (tg_id, service, json.dumps(params, ensure_ascii=False), price, now(), now()),
        )
        order_id = cur.lastrowid
        await cur.close()
        await self.db.execute("UPDATE ledger SET ref=? WHERE id=(SELECT MAX(id) FROM ledger WHERE tg_id=? AND reason='order')",
                              (f"order:{order_id}", tg_id))
        await self.db.commit()
        return order_id

    # ── shablon rasmlari: Telegram file_id keshi ─────────────────────────
    async def tpl_file(self, template_id: str) -> str | None:
        row = await self._one("SELECT file_id FROM tpl_files WHERE template_id=?", (template_id,))
        return row["file_id"] if row else None

    async def set_tpl_file(self, template_id: str, file_id: str) -> None:
        await self.db.execute("INSERT INTO tpl_files(template_id, file_id) VALUES(?,?) "
                              "ON CONFLICT(template_id) DO UPDATE SET file_id=excluded.file_id", (template_id, file_id))
        await self.db.commit()

    async def forget_tpl_file(self, template_id: str) -> None:
        await self.db.execute("DELETE FROM tpl_files WHERE template_id=?", (template_id,))
        await self.db.commit()

    # ── promokod ─────────────────────────────────────────────────────────
    async def create_promo(self, code: str, services: list[str], max_uses: int | None,
                           expires_at: int | None, note: str = "") -> bool:
        cur = await self.db.execute(
            "INSERT OR IGNORE INTO promo_codes(code, services, max_uses, expires_at, active, note, created_at) "
            "VALUES(?,?,?,?,1,?,?)", (code, json.dumps(services), max_uses, expires_at, note, now()))
        ok = cur.rowcount == 1
        await cur.close()
        await self.db.commit()
        return ok

    async def promo(self, code: str) -> dict | None:
        return await self._one("SELECT * FROM promo_codes WHERE code=?", (code,))

    async def set_promo_active(self, code: str, active: bool) -> None:
        await self.db.execute("UPDATE promo_codes SET active=? WHERE code=?", (int(active), code))
        await self.db.commit()

    async def list_promos(self) -> list[dict]:
        return await self._all(
            "SELECT p.*, (SELECT COUNT(*) FROM vouchers v WHERE v.code=p.code) AS used, "
            "(SELECT COUNT(*) FROM vouchers v WHERE v.code=p.code AND v.status='used') AS spent "
            "FROM promo_codes p ORDER BY created_at DESC")

    # VAQTINCHALIK: reklama videosi uchun bitta akkaunt bitta kodni istagancha marta qayta
    # kirita olsin (odatdagi "bir marta" chegarasi chetlab o'tiladi). Video tayyor bo'lgach
    # bu yozuv olib tashlanadi va holat avvalgidek qaytadi.
    PROMO_DEMO_BYPASS: dict[int, str] = {5605407368: "TEZSTART"}  # Nazarbek Kabulov (@mr_uzdev)

    async def redeem(self, code: str, tg_id: int) -> tuple[str, dict | None]:
        """
        Promokodni kiritadi. Natija: ("ok", kupon) yoki xato kodi:
        invalid | expired | limit | used | has_active.
        Hisoblash va yozish bitta so'rovda ketma-ket (bitta ulanish) — chegaradan oshib ketmaydi.
        """
        promo = await self.promo(code)
        if promo is None or not promo["active"]:
            return "invalid", None
        if promo["expires_at"] and promo["expires_at"] < now():
            return "expired", None
        demo = self.PROMO_DEMO_BYPASS.get(tg_id) == code
        if not demo:
            if await self._one("SELECT 1 FROM vouchers WHERE code=? AND tg_id=?", (code, tg_id)):
                return "used", None
            if await self._one("SELECT 1 FROM vouchers WHERE tg_id=? AND status='active'", (tg_id,)):
                return "has_active", None
            if promo["max_uses"] is not None:
                taken = (await self._one("SELECT COUNT(*) AS n FROM vouchers WHERE code=?", (code,)))["n"]
                if taken >= promo["max_uses"]:
                    return "limit", None
            cur = await self.db.execute(
                "INSERT INTO vouchers(tg_id, code, status, created_at) VALUES(?,?, 'active', ?)", (tg_id, code, now()))
            voucher_id = cur.lastrowid
            await cur.close()
        else:
            # Shu kod+foydalanuvchi uchun bor yozuv qayta "active" ga qaytariladi (yangisi qo'shilmaydi —
            # haqiqiy ishlatilganlar sonini (`max_uses`) buzmaydi).
            await self.db.execute(
                "INSERT INTO vouchers(tg_id, code, status, created_at) VALUES(?,?,'active',?) "
                "ON CONFLICT(code, tg_id) DO UPDATE SET status='active', order_id=NULL, used_at=NULL, created_at=excluded.created_at",
                (tg_id, code, now()))
            voucher_id = (await self._one("SELECT id FROM vouchers WHERE code=? AND tg_id=?", (code, tg_id)))["id"]
        await self.db.commit()
        return "ok", {"id": voucher_id, "services": json.loads(promo["services"]), "code": code}

    async def active_voucher(self, tg_id: int) -> dict | None:
        row = await self._one(
            "SELECT v.*, p.services FROM vouchers v JOIN promo_codes p ON p.code=v.code "
            "WHERE v.tg_id=? AND v.status='active' ORDER BY v.id LIMIT 1", (tg_id,))
        if row:
            row["services"] = json.loads(row["services"])
        return row

    async def place_free_order(self, tg_id: int, service: str, params: dict, voucher_id: int,
                               max_active: int | None = None) -> int | str | None:
        """
        Kupon bilan bepul buyurtma. Kupon FAQAT 'active' bo'lsa va shu foydalanuvchiniki bo'lsa sarflanadi
        (bitta shartli UPDATE: ikki marta bosish ikki buyurtma bermaydi). None — kupon yaroqsiz, "limit" — faol
        buyurtmalar chegarasi.
        """
        if max_active is not None and await self.active_count(tg_id) >= max_active:
            return "limit"
        cur = await self.db.execute(
            "UPDATE vouchers SET status='used', used_at=? WHERE id=? AND tg_id=? AND status='active'",
            (now(), voucher_id, tg_id))
        ok = cur.rowcount == 1
        await cur.close()
        if not ok:
            await self.db.commit()
            return None
        cur = await self.db.execute(
            "INSERT INTO orders(tg_id, service, params, price, status, voucher_id, created_at, updated_at) "
            "VALUES(?,?,?,0,'queued',?,?,?)",
            (tg_id, service, json.dumps(params, ensure_ascii=False), voucher_id, now(), now()))
        order_id = cur.lastrowid
        await cur.close()
        await self.db.execute("UPDATE vouchers SET order_id=? WHERE id=?", (order_id, voucher_id))
        await self.db.commit()
        return order_id

    async def order(self, order_id: int) -> dict | None:
        return await self._one("SELECT * FROM orders WHERE id=?", (order_id,))

    async def update_order(self, order_id: int, **fields) -> None:
        fields["updated_at"] = now()
        cols = ", ".join(f"{k}=?" for k in fields)
        await self.db.execute(f"UPDATE orders SET {cols} WHERE id=?", (*fields.values(), order_id))
        await self.db.commit()

    async def refund_order(self, order_id: int) -> bool:
        """Pulni BIR MARTA qaytaradi (`refunded` bayrog'i takroriy qaytarishni to'sadi)."""
        cur = await self.db.execute(
            "UPDATE orders SET refunded=1, updated_at=? WHERE id=? AND refunded=0", (now(), order_id)
        )
        first = cur.rowcount == 1
        await cur.close()
        await self.db.commit()
        if not first:
            return False
        row = await self.order(order_id)
        if row["voucher_id"]:
            # Bepul buyurtma: pul emas, promokod huquqi qaytadi
            await self.db.execute("UPDATE vouchers SET status='active', order_id=NULL, used_at=NULL WHERE id=?",
                                  (row["voucher_id"],))
            await self.db.commit()
            return True
        await self.credit(row["tg_id"], row["price"], "refund", f"order:{order_id}")
        return True

    async def cancel_queued(self, order_id: int) -> bool:
        """Hamkorga hali yuborilmagan buyurtmani bekor qiladi (ishchi bilan poyga: faqat 'queued' bo'lsa)."""
        cur = await self.db.execute(
            "UPDATE orders SET status='canceled', error='admin_canceled', updated_at=? WHERE id=? AND status='queued'",
            (now(), order_id))
        ok = cur.rowcount == 1
        await cur.close()
        await self.db.commit()
        return ok

    async def orders_by_status(self, *statuses: str) -> list[dict]:
        marks = ",".join("?" * len(statuses))
        return await self._all(f"SELECT * FROM orders WHERE status IN ({marks}) ORDER BY id", statuses)

    async def active_count(self, tg_id: int) -> int:
        row = await self._one(
            "SELECT COUNT(*) AS n FROM orders WHERE tg_id=? AND status IN ('queued','submitted','processing')", (tg_id,))
        return row["n"]

    async def user_orders(self, tg_id: int, limit: int = 10) -> list[dict]:
        return await self._all("SELECT * FROM orders WHERE tg_id=? ORDER BY id DESC LIMIT ?", (tg_id, limit))

    async def undelivered(self) -> list[dict]:
        return await self._all("SELECT * FROM orders WHERE status='succeeded' AND delivered=0 ORDER BY id")

    # ── to'lovlar ────────────────────────────────────────────────────────
    async def new_payment(self, tg_id: int, amount: int, method: str, status: str,
                          receipt_file_id: str | None = None) -> int:
        cur = await self.db.execute(
            "INSERT INTO payments(tg_id, amount, method, status, receipt_file_id, created_at, updated_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (tg_id, amount, method, status, receipt_file_id, now(), now()),
        )
        pid = cur.lastrowid
        await cur.close()
        await self.db.commit()
        return pid

    async def payment(self, payment_id: int) -> dict | None:
        return await self._one("SELECT * FROM payments WHERE id=?", (payment_id,))

    async def set_payment(self, payment_id: int, **fields) -> None:
        fields["updated_at"] = now()
        cols = ", ".join(f"{k}=?" for k in fields)
        await self.db.execute(f"UPDATE payments SET {cols} WHERE id=?", (*fields.values(), payment_id))
        await self.db.commit()

    async def settle_payment(self, payment_id: int, from_status: str, to_status: str, **fields) -> dict | None:
        """
        Holatni `from_status` → `to_status` ga O'TKAZADI va to'lovni qaytaradi; holat boshqa
        bo'lsa (allaqachon tasdiqlangan) None. Ikki marta bosilgan "Tasdiqlash" yoki qayta
        kelgan Click so'rovi balansni ikki marta to'ldirmasligi shu bilan kafolatlanadi.
        """
        extra = "".join(f", {k}=?" for k in fields)
        cur = await self.db.execute(
            f"UPDATE payments SET status=?, updated_at=?{extra} WHERE id=? AND status=?",
            (to_status, now(), *fields.values(), payment_id, from_status),
        )
        ok = cur.rowcount == 1
        await cur.close()
        await self.db.commit()
        return await self.payment(payment_id) if ok else None

    async def edit_pending_amount(self, payment_id: int, amount: int) -> dict | None:
        """Kutilayotgan to'lov summasini o'zgartiradi; asl summa `original_amount` da saqlanadi."""
        cur = await self.db.execute(
            "UPDATE payments SET original_amount=COALESCE(original_amount, amount), amount=?, updated_at=? "
            "WHERE id=? AND status='pending'", (amount, now(), payment_id))
        ok = cur.rowcount == 1
        await cur.close()
        await self.db.commit()
        return await self.payment(payment_id) if ok else None

    async def pending_card_payments(self) -> int:
        row = await self._one("SELECT COUNT(*) AS n FROM payments WHERE method='card' AND status='pending'")
        return row["n"]

    # ── ogohlantirish chastotasi ─────────────────────────────────────────
    async def alert_due(self, key: str, every: int = 3600) -> bool:
        """Bir xil ogohlantirish `every` soniyada bir martadan ko'p ketmasin."""
        row = await self._one("SELECT sent_at FROM alerts WHERE key=?", (key,))
        if row and now() - row["sent_at"] < every:
            return False
        await self.db.execute(
            "INSERT INTO alerts(key, sent_at) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET sent_at=excluded.sent_at",
            (key, now()),
        )
        await self.db.commit()
        return True

    # ── admin panel: kirish va sessiya ───────────────────────────────────
    async def new_login(self, nonce: str, secret_hash: str, ip: str, agent: str) -> None:
        await self.db.execute(
            "INSERT INTO admin_login(nonce, secret_hash, status, ip, agent, created_at) VALUES(?,?, 'pending', ?,?,?)",
            (nonce, secret_hash, ip, agent[:200], now()))
        await self.db.commit()

    async def login(self, nonce: str) -> dict | None:
        return await self._one("SELECT * FROM admin_login WHERE nonce=?", (nonce,))

    async def move_login(self, nonce: str, from_status: str, to_status: str, admin_id: int | None = None) -> bool:
        cur = await self.db.execute(
            "UPDATE admin_login SET status=?, admin_id=COALESCE(?, admin_id) WHERE nonce=? AND status=?",
            (to_status, admin_id, nonce, from_status))
        ok = cur.rowcount == 1
        await cur.close()
        await self.db.commit()
        return ok

    async def create_session(self, token_hash: str, admin_id: int, csrf: str, ttl: int) -> None:
        await self.db.execute("DELETE FROM admin_sessions WHERE expires_at<?", (now(),))
        await self.db.execute("INSERT INTO admin_sessions(token_hash, admin_id, csrf, created_at, expires_at) VALUES(?,?,?,?,?)",
                              (token_hash, admin_id, csrf, now(), now() + ttl))
        await self.db.commit()

    async def session(self, token_hash: str) -> dict | None:
        return await self._one("SELECT * FROM admin_sessions WHERE token_hash=? AND expires_at>?", (token_hash, now()))

    async def drop_session(self, token_hash: str) -> None:
        await self.db.execute("DELETE FROM admin_sessions WHERE token_hash=?", (token_hash,))
        await self.db.commit()

    # ── admin panel: so'rovlar ───────────────────────────────────────────
    async def audit(self, admin_id: int, action: str, detail: str = "") -> None:
        await self.db.execute("INSERT INTO admin_audit(admin_id, action, detail, created_at) VALUES(?,?,?,?)",
                              (admin_id, action, detail[:500], now()))
        await self.db.commit()

    async def recent_audit(self, limit: int = 100) -> list[dict]:
        return await self._all("SELECT * FROM admin_audit ORDER BY id DESC LIMIT ?", (limit,))

    async def adjust_balance(self, tg_id: int, delta: int, reason: str) -> bool:
        """Qo'lda to'ldirish (+) yoki ayirish (−). Ayirishda balans yetmasa False."""
        if delta == 0 or await self.user(tg_id) is None:
            return False
        if delta > 0:
            await self.credit(tg_id, delta, f"admin:{reason}"[:120])
            return True
        return await self.debit(tg_id, -delta, f"admin:{reason}"[:120])

    async def find_orders(self, status: str = "", service: str = "", tg_id: int | None = None,
                          limit: int = 50, offset: int = 0) -> list[dict]:
        where, args = [], []
        if status:
            where.append("status=?"); args.append(status)
        if service:
            where.append("service=?"); args.append(service)
        if tg_id:
            where.append("tg_id=?"); args.append(tg_id)
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        return await self._all(f"SELECT * FROM orders {clause} ORDER BY id DESC LIMIT ? OFFSET ?", (*args, limit, offset))

    async def search_users(self, query: str = "", limit: int = 50) -> list[dict]:
        q = query.strip().lstrip("@")
        if not q:
            return await self._all("SELECT * FROM users ORDER BY COALESCE(last_seen, 0) DESC LIMIT ?", (limit,))
        if q.isdigit():
            return await self._all("SELECT * FROM users WHERE tg_id=? OR name LIKE ? OR username LIKE ? LIMIT ?",
                                   (int(q), f"%{q}%", f"%{q}%", limit))
        return await self._all("SELECT * FROM users WHERE name LIKE ? OR username LIKE ? ORDER BY last_seen DESC LIMIT ?",
                               (f"%{q}%", f"%{q}%", limit))

    async def user_ledger(self, tg_id: int, limit: int = 50) -> list[dict]:
        return await self._all("SELECT * FROM ledger WHERE tg_id=? ORDER BY id DESC LIMIT ?", (tg_id, limit))

    async def list_payments(self, status: str = "", limit: int = 100) -> list[dict]:
        if status:
            return await self._all("SELECT * FROM payments WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit))
        return await self._all("SELECT * FROM payments ORDER BY id DESC LIMIT ?", (limit,))

    async def stats(self) -> dict:
        day = now() - 86400
        return {
            "users": (await self._one("SELECT COUNT(*) AS n FROM users"))["n"],
            "orders_24h": (await self._one("SELECT COUNT(*) AS n FROM orders WHERE created_at>?", (day,)))["n"],
            "revenue_24h": (await self._one(
                "SELECT COALESCE(SUM(price),0) AS s FROM orders WHERE created_at>? AND status='succeeded'", (day,)))["s"],
            "failed_24h": (await self._one(
                "SELECT COUNT(*) AS n FROM orders WHERE created_at>? AND status='failed'", (day,)))["n"],
            "pending_cards": await self.pending_card_payments(),
        }
