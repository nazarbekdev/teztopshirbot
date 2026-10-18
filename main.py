"""@teztopshirbot — OsonTopshir hamkor API ustidagi yupqa Telegram frontend."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from app import config
from app.api import PartnerClient
from app.click_server import make_app
from app.db import Store
from app.fsm_storage import SqliteStorage
from app.handlers import admin, balance, order, orders, start
from app.middleware import Onboarding
from app.worker import Worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger("teztopshir")


async def main() -> None:
    settings = config.load()
    if not settings.bot_token or not settings.api_key:
        raise SystemExit("BOT_TOKEN va PARTNER_API_KEY .env da bo'lishi shart")

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    store = await Store(settings.db_path).open()
    api = PartnerClient(settings.api_base, settings.api_key)

    async def notify_admins(text: str, photo: str | None = None, markup=None) -> None:
        for admin_id in settings.admin_ids:
            try:
                if photo:
                    await bot.send_photo(admin_id, photo, caption=text, reply_markup=markup)
                else:
                    await bot.send_message(admin_id, text, reply_markup=markup)
            except Exception:
                logger.warning("Adminga xabar ketmadi: %s", admin_id)

    async def alert(key: str, text: str) -> None:
        """Ogohlantirish: bir xil kalit soatiga bir martadan ko'p yuborilmaydi."""
        if not await store.alert_due(key):
            return
        if settings.ops_channel:
            try:
                await bot.send_message(settings.ops_channel, text)
                return
            except Exception:
                logger.warning("OPS kanaliga yuborilmadi")
        await notify_admins(text)

    # FSM holati bazada: bot qayta ishga tushsa foydalanuvchining savol-javobi yo'qolmaydi
    dp = Dispatcher(storage=SqliteStorage(store))
    dp.workflow_data.update(store=store, settings=settings, api=api, notify_admins=notify_admins)
    dp.message.outer_middleware(Onboarding())
    dp.callback_query.outer_middleware(Onboarding())
    for module in (start, order, orders, balance, admin):
        dp.include_router(module.router)

    worker = Worker(store, api, bot, settings.max_active, alert)
    tasks = [asyncio.create_task(worker.run())]

    runner = None
    if settings.click_enabled:
        runner = web.AppRunner(make_app(store, settings, bot))
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", settings.click_port).start()
        logger.info("Click qabul qiluvchisi: :%s", settings.click_port)
    else:
        logger.info("Click sozlanmagan — faqat karta orqali to'lov")

    logger.info("Ishga tushdi (API rejimi: %s)", "TEST" if settings.test_mode else "LIVE")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        for t in tasks:
            t.cancel()
        if runner:
            await runner.cleanup()
        await api.close()
        await store.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
