from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..catalog import SERVICES, money

router = Router()


@router.message(Command("admin"))
async def admin_panel(message: Message, store, settings, api):
    if message.from_user.id not in settings.admin_ids:
        return
    s = await store.stats()
    lines = ["🛠 <b>Admin</b>", "",
             f"👥 Foydalanuvchilar: {s['users']}",
             f"📦 24 soatda buyurtma: {s['orders_24h']} (xato: {s['failed_24h']})",
             f"💵 24 soatda tushum: {money(s['revenue_24h'])}",
             f"💳 Tekshirilmagan chek: {s['pending_cards']}",
             f"🔑 API rejimi: {'TEST' if settings.test_mode else 'LIVE'}", "",
             "<b>Hamkor kreditlari:</b>"]
    try:
        credits = await api.credits()
        for slug, spec in SERVICES.items():
            b = credits.get(slug, {})
            unit = b.get("unit_price")
            margin = f" · marja {money(spec.price - unit)}" if unit else ""
            lines.append(f"{spec.emoji} {spec.title}: <b>{b.get('credits', 0)}</b> kredit"
                         f" (hamkor narxi {money(unit) if unit else '—'}{margin})")
    except Exception as e:
        lines.append(f"⚠️ Kreditlarni olib bo'lmadi: {e}")
    await message.answer("\n".join(lines), parse_mode="HTML")
