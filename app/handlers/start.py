from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from .. import ui
from ..catalog import ORDER, SERVICES, money

router = Router()

SUPPORT = "Savol yoki muammo bo'lsa, shu yerga yozing: {contact}"


def welcome(name: str) -> str:
    lines = [f"👋 Salom, <b>{name}</b>!", "",
             "Men kurs ishi, taqdimot, referat va boshqa hujjatlarni tez tayyorlab beraman.", "",
             "<b>Xizmatlar va narxlar:</b>"]
    for slug in ORDER:
        s = SERVICES[slug]
        lines.append(f"{s.emoji} {s.title} — <b>{money(s.price)}</b>")
    lines += ["", "Pastdagi menyudan xizmatni tanlang 👇"]
    return "\n".join(lines)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, store):
    await state.clear()
    await store.touch_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    await message.answer(welcome(message.from_user.full_name), parse_mode="HTML", reply_markup=ui.main_menu())


@router.message(Command("menu"))
async def menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Asosiy menyu", reply_markup=ui.main_menu())


@router.message(F.text == ui.HELP)
@router.message(Command("help"))
async def help_(message: Message, state: FSMContext, settings):
    await state.clear()
    contact = f"@{settings.support_username}" if getattr(settings, "support_username", "") else "administrator"
    await message.answer(
        "ℹ️ <b>Yordam</b>\n\n"
        "• Xizmatni menyudan tanlang, savollarga javob bering — qolganini o'zim bajaraman.\n"
        "• To'lov balansdan yechiladi. Balansni <b>💰 Balans</b> orqali Click yoki karta bilan to'ldirasiz.\n"
        "• Buyurtma xato bilan tugasa, pul balansingizga avtomatik qaytadi.\n\n"
        + SUPPORT.format(contact=contact),
        parse_mode="HTML",
    )
