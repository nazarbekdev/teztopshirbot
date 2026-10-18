"""
Buyurtma ishchisi: navbatdagi buyurtmalarni hamkor API'ga yuboradi, holatini
so'raydi va tayyor faylni mijozga yetkazadi.

Holatlar (`orders.status`):
  queued     bizda navbatda (hamkorga hali yuborilmagan)
  submitted  hamkor qabul qildi (queued)
  processing hamkor tayyorlayapti
  succeeded  tayyor (delivered=0 bo'lsa fayl hali yetkazilmagan)
  failed / canceled  pul mijozga qaytarilgan

Ishonchlilik qoidalari:
  · Yuborish `Idempotency-Key = tez-<id>` bilan: tarmoq uzilib qayta urinsak ham
    hamkorda kredit ikki marta yechilmaydi.
  · Pul mijozdan buyurtma yaratilganda yechiladi va FAQAT `refund_order` orqali
    (bir martalik bayroq) qaytariladi.
  · Hamkor bir vaqtda 10 tagacha faol buyurtmaga ruxsat beradi — biz `max_active`
    dan oshirmaymiz, qolganlari bizda navbatda kutadi.
  · Yetkazish alohida bosqich: Telegram xato bersa fayl yo'qolmaydi, keyingi
    aylanishda qayta uriniladi (hamkor fayli 7 kun saqlanadi).
"""

import asyncio
import html
import json
import logging
import time

from aiogram.types import BufferedInputFile

from .api import PartnerClient, PartnerError
from .catalog import SERVICES, pick
from .db import Store, now
from .i18n import t

logger = logging.getLogger(__name__)

POLL_EVERY = 10          # soniya: hamkor tavsiyasi 10 dan kam bo'lmasin
GIVE_UP_AFTER = 30 * 60  # hamkorga yuborib bo'lmasa (5xx/tarmoq) shuncha vaqtdan so'ng pul qaytariladi
STUCK_AFTER = 45 * 60    # shuncha vaqt "tayyorlanmoqda" bo'lsa adminga xabar


class Worker:
    def __init__(self, store: Store, api: PartnerClient, bot, max_active: int, alert):
        self.store = store
        self.api = api
        self.bot = bot
        self.max_active = max_active
        self.alert = alert                      # async (key, text) -> None
        self._last_poll = 0.0
        self.poll_every = POLL_EVERY

    # ── aylanish ─────────────────────────────────────────────────────────
    async def run(self, interval: float = 5.0) -> None:
        while True:
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Ishchi aylanishida xato")
            await asyncio.sleep(interval)

    async def tick(self) -> None:
        await self.submit_queued()
        await self.poll_active()
        await self.deliver_pending()

    # ── yuborish ─────────────────────────────────────────────────────────
    async def submit_queued(self) -> None:
        active = len(await self.store.orders_by_status("submitted", "processing"))
        slots = self.max_active - active
        if slots <= 0:
            return
        for order in await self.store.orders_by_status("queued"):
            if slots <= 0:
                break
            if order["next_try_at"] > now():
                continue
            if await self._submit(order):
                slots -= 1

    async def _submit(self, order: dict) -> bool:
        try:
            response = await self.api.create_order(
                order["service"], json.loads(order["params"]), f"tez-{order['id']}",
                {"tez_order_id": str(order["id"])},
            )
        except PartnerError as e:
            await self._submit_failed(order, e)
            return False
        status = response.get("status", "queued")
        await self.store.update_order(
            order["id"], partner_order_id=response["id"],
            status="processing" if status == "processing" else "submitted",
        )
        logger.info("Buyurtma #%s hamkorga yuborildi: %s", order["id"], response["id"])
        return True

    async def _submit_failed(self, order: dict, e: PartnerError) -> None:
        oid = order["id"]
        if e.code == "insufficient_credits":
            await self._fail(order, e.code, "fail_unavailable")
            await self.alert(f"credits:{order['service']}",
                             f"🔴 <b>Hamkor krediti tugadi: {order['service']}</b>\n"
                             f"Buyurtma #{oid} bajarilmadi (mijozga pul qaytarildi). "
                             "Kreditni to'ldiring: developers.osontopshir.uz/dashboard")
        elif e.retryable:
            attempts = order["attempts"] + 1
            if now() - order["created_at"] > GIVE_UP_AFTER:
                await self._fail(order, e.code, "fail_down")
                await self.alert("partner_down", f"🟠 Hamkor API javob bermayapti ({e.code}), "
                                                  f"buyurtma #{oid} bekor qilindi.")
            else:
                await self.store.update_order(oid, attempts=attempts,
                                              next_try_at=now() + min(30 * attempts, 300))
                logger.warning("Buyurtma #%s yuborilmadi (%s), qayta uriniladi", oid, e)
        else:
            # 400/403/409: so'rovni o'zgartirmasdan qayta yuborish foydasiz — bu bizning xatomiz
            await self._fail(order, e.code, "fail_rejected")
            await self.alert(f"order_error:{e.code}",
                             f"🔴 Hamkor buyurtmani rad etdi: <code>{html.escape(str(e))}</code>\n"
                             f"Buyurtma #{oid} ({order['service']}). Parametr yoki sozlama xatosi bo'lishi mumkin.")

    async def _fail(self, order: dict, code: str, text_key: str) -> None:
        await self.store.update_order(order["id"], status="failed", error=code)
        await self.store.refund_order(order["id"])
        await self._notify(order["tg_id"], text_key, id=order["id"])

    # ── holat so'rash ────────────────────────────────────────────────────
    async def poll_active(self) -> None:
        """
        Faol buyurtmalar holati. Ro'yxat endpoint'i bitta so'rovda 100 tagacha buyurtmani
        qaytaradi (80 ta faol buyurtmani alohida so'rash daqiqasiga ~500 so'rov bo'lardi).
        Ro'yxatda ko'rinmagani (eski yoki ro'yxat xato bergani) alohida so'raladi.
        """
        if time.monotonic() - self._last_poll < self.poll_every:
            return
        self._last_poll = time.monotonic()
        active = await self.store.orders_by_status("submitted", "processing")
        if not active:
            return
        remote_by_id: dict[str, dict] = {}
        try:
            remote_by_id = {o["id"]: o for o in await self.api.list_orders()}
        except Exception as e:
            logger.warning("Buyurtmalar ro'yxatini olib bo'lmadi (%s) — alohida so'raladi", e)
        for order in active:
            oid = order["id"]
            remote = remote_by_id.get(order["partner_order_id"])
            if remote is None:
                try:
                    remote = await self.api.get_order(order["partner_order_id"])
                except PartnerError as e:
                    logger.warning("Buyurtma #%s holatini olib bo'lmadi: %s", oid, e)
                    continue
            await self._apply_remote(order, remote)

            if now() - order["updated_at"] > STUCK_AFTER:
                await self.alert(f"stuck:{oid}", f"🟠 Buyurtma #{oid} ({order['service']}) "
                                                 f"{STUCK_AFTER // 60} daqiqadan beri tayyor bo'lmadi.")

    async def _apply_remote(self, order: dict, remote: dict) -> None:
        status = remote.get("status")
        oid = order["id"]
        if status == "succeeded":
            await self.store.update_order(oid, status="succeeded")
            await self._deliver(order, remote)
        elif status in ("failed", "canceled"):
            code = (remote.get("error") or {}).get("code") or status
            await self.store.update_order(oid, status=status, error=code)
            await self.store.refund_order(oid)
            await self._notify(order["tg_id"], "fail_generation", id=oid)
            if status == "failed":
                await self.alert(f"gen_failed:{order['service']}",
                                 f"🟠 Generatsiya xatosi: buyurtma #{oid} ({order['service']}), kod <code>{code}</code>")
        elif status == "processing" and order["status"] != "processing":
            await self.store.update_order(oid, status="processing")

    # ── yetkazish ────────────────────────────────────────────────────────
    async def deliver_pending(self) -> None:
        for order in await self.store.undelivered():
            try:
                remote = await self.api.get_order(order["partner_order_id"])
                await self._deliver(order, remote)
            except PartnerError as e:
                logger.warning("Buyurtma #%s faylini olib bo'lmadi: %s", order["id"], e)

    async def _deliver(self, order: dict, remote: dict) -> None:
        files = (remote.get("result") or {}).get("files") or []
        lang = ((await self.store.user(order["tg_id"])) or {}).get("lang")
        spec = SERVICES.get(order["service"])
        caption = (t(lang, "delivered", title=pick(spec.title, lang) if spec else order["service"], id=order["id"])
                   + t(lang, "disclaimer"))
        tg_files: list[str] = []
        try:
            for index, f in enumerate(files):
                data = await self.api.download(f["id"])
                sent = await self.bot.send_document(
                    order["tg_id"], BufferedInputFile(data, filename=f.get("name") or f"{f['id']}.bin"),
                    caption=caption if index == 0 else None, parse_mode="HTML",
                )
                file_id = getattr(getattr(sent, "document", None), "file_id", None)
                if file_id:
                    tg_files.append(file_id)
        except PartnerError as e:
            logger.warning("Fayl yuklab olinmadi (#%s): %s", order["id"], e)
            return
        except Exception:
            logger.exception("Fayl yuborilmadi (#%s) — keyin qayta uriniladi", order["id"])
            return
        if not files:
            logger.error("Buyurtma #%s tayyor, lekin fayl yo'q", order["id"])
            await self.alert(f"nofile:{order['id']}", f"🔴 Buyurtma #{order['id']} tayyor, lekin fayl yo'q.")
            return
        await self.store.update_order(order["id"], delivered=1, tg_files=json.dumps(tg_files))

    async def _notify(self, tg_id: int, key: str, **kw) -> None:
        lang = ((await self.store.user(tg_id)) or {}).get("lang")
        try:
            await self.bot.send_message(tg_id, t(lang, key, **kw), parse_mode="HTML")
        except Exception:
            logger.warning("Mijozga xabar yuborilmadi: %s", tg_id)
