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

    async def open(self) -> "Store":
        self.db = await aiosqlite.connect(self.path)
        self.db.row_factory = aiosqlite.Row
        await self.db.execute("PRAGMA journal_mode=WAL")
        await self.db.executescript(SCHEMA)
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
    async def place_order(self, tg_id: int, service: str, params: dict, price: int) -> int | None:
        """Balansdan yechib buyurtma yaratadi. Balans yetmasa None."""
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
        await self.credit(row["tg_id"], row["price"], "refund", f"order:{order_id}")
        return True

    async def orders_by_status(self, *statuses: str) -> list[dict]:
        marks = ",".join("?" * len(statuses))
        return await self._all(f"SELECT * FROM orders WHERE status IN ({marks}) ORDER BY id", statuses)

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
