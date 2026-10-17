"""Buyurtma oqimi: savollar → tasdiq → balansdan yechish → navbatga."""

import html
import re

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton as IB, Message

from .. import ui
from ..catalog import SERVICES, STATUS_LABEL, build_params, money

router = Router()


class Flow(StatesGroup):
    collecting = State()
    confirming = State()


def _kb(step, with_skip: bool):
    rows = []
    if step.kind == "choice":
        buttons = [IB(text=text, callback_data=f"c:{value}") for value, text in step.choices]
        for i in range(0, len(buttons), 3 if len(buttons) > 3 else len(buttons)):
            rows.append(buttons[i:i + 3])
    if step.optional:
        rows.append([IB(text="⏭ O'tkazib yuborish", callback_data="skip")])
    rows.append([ui.cancel_button()])
    return ui.inline(*rows)


async def _ask(target: Message, state: FSMContext) -> None:
    data = await state.get_data()
    service = SERVICES[data["slug"]]
    i = data["i"]
    step = service.steps[i]
    await target.answer(f"<i>({i + 1}/{len(service.steps)})</i>\n{step.prompt}",
                        parse_mode="HTML", reply_markup=_kb(step, step.optional))


@router.message(F.text.in_(ui.SERVICE_LABELS))
async def start_flow(message: Message, state: FSMContext):
    slug = ui.SERVICE_LABELS[message.text]
    service = SERVICES[slug]
    await state.clear()
    await state.set_state(Flow.collecting)
    await state.update_data(slug=slug, i=0, answers={})
    await message.answer(
        f"{service.emoji} <b>{service.title}</b> — {money(service.price)}\n"
        f"📦 {service.note} · ⏱ taxminan {service.eta}\n\nBir necha savolga javob bering.",
        parse_mode="HTML",
    )
    await _ask(message, state)


async def _advance(target: Message, state: FSMContext, store, key: str, value) -> None:
    data = await state.get_data()
    answers = {**data["answers"], key: value}
    i = data["i"] + 1
    service = SERVICES[data["slug"]]
    await state.update_data(answers=answers, i=i)
    if i < len(service.steps):
        await _ask(target, state)
    else:
        await _confirm(target, state, store)


@router.message(Flow.collecting, F.text & ~F.text.startswith("/") & ~F.text.in_(ui.MENU_TEXTS))
async def on_text(message: Message, state: FSMContext, store):
    data = await state.get_data()
    step = SERVICES[data["slug"]].steps[data["i"]]
    if step.kind == "choice":
        await message.answer("Iltimos, yuqoridagi tugmalardan birini tanlang 👆")
        return
    text = " ".join((message.text or "").split())
    if not step.lo <= len(text) <= step.hi:
        await message.answer(f"Uzunligi {step.lo}–{step.hi} belgi bo'lishi kerak (hozir {len(text)}). Qayta yozing.")
        return
    await _advance(message, state, store, step.key, text)


@router.callback_query(Flow.collecting, F.data.startswith("c:"))
async def on_choice(callback: CallbackQuery, state: FSMContext, store):
    data = await state.get_data()
    step = SERVICES[data["slug"]].steps[data["i"]]
    value = callback.data[2:]
    if step.kind != "choice" or value not in {v for v, _ in step.choices}:
        await callback.answer("Bu tanlov endi amal qilmaydi", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await _advance(callback.message, state, store, step.key, int(value) if step.numeric else value)


@router.callback_query(Flow.collecting, F.data == "skip")
async def on_skip(callback: CallbackQuery, state: FSMContext, store):
    data = await state.get_data()
    step = SERVICES[data["slug"]].steps[data["i"]]
    if not step.optional:
        await callback.answer("Bu savol majburiy", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await _advance(callback.message, state, store, step.key, "")


def _summary(slug: str, answers: dict) -> str:
    service = SERVICES[slug]
    lines = []
    for step in service.steps:
        value = answers.get(step.key)
        if value in (None, ""):
            continue
        name = re.sub(r"<[^>]+>", "", step.prompt).split("\n")[0].strip(" :?")
        shown = dict(step.choices).get(str(value), value) if step.kind == "choice" else value
        lines.append(f"• {html.escape(name)}: <b>{html.escape(str(shown))}</b>")
    return "\n".join(lines)


async def _confirm(target: Message, state: FSMContext, store) -> None:
    data = await state.get_data()
    service = SERVICES[data["slug"]]
    balance = await store.balance(target.chat.id)
    await state.set_state(Flow.confirming)
    text = (f"{service.emoji} <b>{service.title}</b>\n\n{_summary(data['slug'], data['answers'])}\n\n"
            f"💵 Narxi: <b>{money(service.price)}</b>\n💰 Balansingiz: {money(balance)}")
    if balance >= service.price:
        kb = ui.inline([IB(text="✅ Buyurtma berish", callback_data="ok", style="success")], [ui.cancel_button()])
    else:
        need = service.price - balance
        text += f"\n\n⚠️ Yetmaydi: yana <b>{money(need)}</b> kerak."
        kb = ui.inline([IB(text="💳 Balansni to'ldirish", callback_data=f"topup:{need}", style="primary")],
                       [ui.cancel_button()])
    await target.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(Flow.confirming, F.data == "ok")
async def on_ok(callback: CallbackQuery, state: FSMContext, store):
    data = await state.get_data()
    # Holatni darhol tozalaymiz: ikki marta bosilgan tugma ikkinchi buyurtma yaratmasin.
    await state.clear()
    slug = data["slug"]
    service = SERVICES[slug]
    order_id = await store.place_order(callback.from_user.id, slug, build_params(service, data["answers"]),
                                       service.price)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    if order_id is None:
        await callback.message.answer("⚠️ Balans yetarli emas. 💰 Balans orqali to'ldiring.")
        return
    await callback.message.answer(
        f"✅ <b>Buyurtma #{order_id} qabul qilindi</b>\n\n"
        f"{service.emoji} {service.title} — taxminan {service.eta}. Tayyor bo'lishi bilan shu yerga yuboraman.",
        parse_mode="HTML", reply_markup=ui.main_menu(),
    )


@router.callback_query(F.data == "cancel")
async def on_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Bekor qilindi")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Bekor qilindi. Menyudan boshqa xizmatni tanlashingiz mumkin.", reply_markup=ui.main_menu())


@router.message(F.text == ui.ORDERS)
async def my_orders(message: Message, state: FSMContext, store):
    await state.clear()
    rows = await store.user_orders(message.from_user.id)
    if not rows:
        await message.answer("Hali buyurtmangiz yo'q. Menyudan xizmatni tanlang 👇")
        return
    lines = ["📦 <b>So'nggi buyurtmalaringiz</b>\n"]
    for o in rows:
        s = SERVICES.get(o["service"])
        lines.append(f"#{o['id']} {s.emoji if s else ''} {s.title if s else o['service']} — "
                     f"{STATUS_LABEL.get(o['status'], o['status'])}")
    await message.answer("\n".join(lines), parse_mode="HTML")
