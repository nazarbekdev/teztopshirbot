"""Buyurtma oqimi: savollar → tasdiq → balansdan yechish → navbatga."""

import html
import logging
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton as IB, Message

from .. import templates_ui, ui
from ..details import SKIP_DETAILS, needs_details
from ..catalog import SERVICES, STUDENT_KEYS, build_params, choice_label, money, pick
from ..i18n import t

router = Router()
logger = logging.getLogger(__name__)


class Flow(StatesGroup):
    collecting = State()
    confirming = State()


def _kb(step, lang: str, can_skip_all: bool):
    rows = []
    if step.kind == "choice":
        buttons = [IB(text=label if isinstance(label, str) else pick(label, lang), callback_data=f"c:{value}")
                   for value, label in step.choices]
        per_row = 1 if any(len(b.text) > 14 for b in buttons) else 3
        for i in range(0, len(buttons), per_row):
            rows.append(buttons[i:i + per_row])
    if step.optional:
        rows.append([IB(text=t(lang, "btn_skip"), callback_data="skip")])
        if can_skip_all:
            rows.append([IB(text=t(lang, "btn_skip_all"), callback_data="skipall")])
    rows.append([ui.cancel_button(lang)])
    return ui.inline(*rows)


def _profile_text(profile: dict, service, lang: str) -> str:
    labels = {s.key: pick(s.lbl, lang) for s in service.steps if s.target == "student"}
    return "\n".join(f"• {html.escape(labels[k])}: <b>{html.escape(str(v))}</b>"
                     for k, v in profile.items() if k in labels and v)


async def _ask(target: Message, state: FSMContext, store, api, lang: str, user_id: int) -> None:
    """Keyingi savolni beradi: kerak bo'lmagan qadamlarni (saqlangan titul ma'lumoti bor) o'tkazib yuboradi."""
    data = await state.get_data()
    service = SERVICES[data["slug"]]
    answers, i = data["answers"], data["i"]
    while i < len(service.steps):
        step = service.steps[i]
        if step.kind == "profile":
            profile = await store.profile(user_id)
            shown = _profile_text(profile, service, lang) if profile else ""
            if shown and "_use_profile" not in answers:
                await state.update_data(i=i)
                await target.answer(
                    t(lang, "profile_found", profile=shown), parse_mode="HTML",
                    reply_markup=ui.inline(
                        [IB(text=t(lang, "btn_use_profile"), callback_data="prof:yes", style="success")],
                        [IB(text=t(lang, "btn_new_profile"), callback_data="prof:new")],
                        [ui.cancel_button(lang)]))
                return
            i += 1
            continue
        if step.target == "student" and (answers.get("_use_profile") or answers.get("_skip_student")):
            i += 1
            continue
        if step.when == "details" and not needs_details(answers.get("topic", "")):
            i += 1
            continue
        if step.kind == "template":
            if await _open_templates(target, state, store, api, lang, answers):
                await state.update_data(i=i)
                return
            # Shablonlar olinmadi: qadam o'tkaziladi, hamkor standart shablonni qo'llaydi
            answers = {**answers, step.key: ""}
            await state.update_data(answers=answers)
            i += 1
            continue
        break
    await state.update_data(i=i)
    if i >= len(service.steps):
        await _confirm(target, state, store, lang, user_id)
        return
    step = service.steps[i]
    first_student = step.target == "student" and (i == 0 or service.steps[i - 1].target != "student")
    await target.answer(pick(step.p, lang), parse_mode="HTML", reply_markup=_kb(step, lang, first_student))


@router.message(F.text.in_(ui.SERVICE_LABELS))
async def start_flow(message: Message, state: FSMContext, store, api, lang):
    slug = ui.SERVICE_LABELS[message.text]
    service = SERVICES[slug]
    await state.clear()
    await state.set_state(Flow.collecting)
    await state.update_data(slug=slug, i=0, answers={})
    await message.answer(
        t(lang, "flow_intro", emoji=service.emoji, title=pick(service.title, lang), price=ui.price_line(slug, lang),
          note=pick(service.note, lang), eta=pick(service.eta, lang)),
        parse_mode="HTML")
    await _ask(message, state, store, api, lang, message.from_user.id)


async def _advance(target: Message, state: FSMContext, store, api, lang: str, user_id: int, updates: dict) -> None:
    data = await state.get_data()
    await state.update_data(answers={**data["answers"], **updates}, i=data["i"] + 1)
    await _ask(target, state, store, api, lang, user_id)


@router.message(Flow.collecting, F.text & ~F.text.startswith("/") & ~F.text.in_(ui.MENU_TEXTS))
async def on_text(message: Message, state: FSMContext, store, api, lang):
    data = await state.get_data()
    step = SERVICES[data["slug"]].steps[data["i"]]
    if step.kind != "text":
        await message.answer(t(lang, "pick_button"))
        return
    text = " ".join((message.text or "").split())
    if step.when == "details" and text.lower() in SKIP_DETAILS:
        text = ""                                      # «-» — umumiy yozilsin
    elif not step.lo <= len(text) <= step.hi:
        await message.answer(t(lang, "bad_length", lo=step.lo, hi=step.hi, n=len(text)))
        return
    await _advance(message, state, store, api, lang, message.from_user.id, {step.key: text})


@router.callback_query(Flow.collecting, F.data.startswith("c:"))
async def on_choice(callback: CallbackQuery, state: FSMContext, store, api, lang):
    data = await state.get_data()
    step = SERVICES[data["slug"]].steps[data["i"]]
    value = callback.data[2:]
    if step.kind != "choice" or value not in {str(v) for v, _ in step.choices}:
        await callback.answer(t(lang, "stale_choice"), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await _advance(callback.message, state, store, api, lang, callback.from_user.id,
                   {step.key: int(value) if step.numeric else value})


@router.callback_query(Flow.collecting, F.data.in_({"skip", "skipall"}))
async def on_skip(callback: CallbackQuery, state: FSMContext, store, api, lang):
    data = await state.get_data()
    step = SERVICES[data["slug"]].steps[data["i"]]
    if not step.optional:
        await callback.answer(t(lang, "required"), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    updates = {step.key: ""}
    if callback.data == "skipall":
        updates["_skip_student"] = True
    await _advance(callback.message, state, store, api, lang, callback.from_user.id, updates)


@router.callback_query(Flow.collecting, F.data.in_({"prof:yes", "prof:new"}))
async def on_profile(callback: CallbackQuery, state: FSMContext, store, api, lang):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    updates: dict = {"_use_profile": callback.data == "prof:yes"}
    if callback.data == "prof:yes":
        updates.update(await store.profile(callback.from_user.id))
    await _advance(callback.message, state, store, api, lang, callback.from_user.id, updates)


async def _open_templates(target: Message, state: FSMContext, store, api, lang: str, answers: dict) -> bool:
    """Shablon karuselini ochadi. API/rasm xatosida False — chaqiruvchi qadamni o'tkazib yuboradi."""
    try:
        listing = await api.templates(answers.get("subject", ""), answers.get("topic", ""))
        tpl = templates_ui.compact(listing)
        if not tpl["order"]:
            return False
    except Exception as e:
        logger.warning("Shablonlar ro'yxati olinmadi: %s", e)
        return False
    doc_lang = answers.get("language", lang)
    await target.answer(t(doc_lang, "tpl_select"), parse_mode="HTML")
    message_id = await templates_ui.open_carousel(target, store, api, tpl, doc_lang)
    if message_id is None:
        return False
    await state.update_data(tpl=tpl, tpl_msg=message_id)
    return True


async def _current_template_step(state: FSMContext):
    data = await state.get_data()
    step = SERVICES[data["slug"]].steps[data["i"]]
    return data, (step if step.kind == "template" and data.get("tpl") else None)


@router.callback_query(Flow.collecting, F.data.startswith("tn:"))
async def tpl_nav(callback: CallbackQuery, state: FSMContext, store, api, lang):
    data, step = await _current_template_step(state)
    try:
        idx = int(callback.data[3:]) % len(data["tpl"]["order"]) if step else None
    except ValueError:
        idx = None
    if idx is None:
        await callback.answer(t(lang, "tpl_stale"), show_alert=True)
        return
    await callback.answer()
    await templates_ui.show(callback.message, store, api, data["tpl"], idx, data["answers"].get("language", lang))


@router.callback_query(Flow.collecting, F.data.startswith("ts:"))
async def tpl_select(callback: CallbackQuery, state: FSMContext, store, api, lang):
    data, step = await _current_template_step(state)
    order = data["tpl"]["order"] if step else []
    try:
        template_id = order[int(callback.data[3:])]
    except (ValueError, IndexError):
        await callback.answer(t(lang, "tpl_stale"), show_alert=True)
        return
    await callback.answer()
    try:
        await callback.message.delete()                # tanlangach karusel o'chiriladi (asosiy botdagidek)
    except Exception:
        await callback.message.edit_reply_markup(reply_markup=None)
    await _advance(callback.message, state, store, api, lang, callback.from_user.id, {step.key: template_id})


def _summary(slug: str, answers: dict, lang: str, tpl: dict | None = None) -> str:
    lines = []
    for step in SERVICES[slug].steps:
        value = answers.get(step.key)
        if step.kind == "profile" or value in (None, ""):
            continue
        if step.kind == "template":
            name = templates_ui.name_of(tpl, value, answers.get("language", lang)) if tpl else value
            lines.append(f"• {html.escape(pick(step.lbl, lang))}: <b>{html.escape(name)}</b>")
            continue
        # Tugmadagi «15 slayd — 5 500 so'm» dan narx qismi olib tashlanadi (narx pastda alohida ko'rsatiladi)
        shown = choice_label(step, value, lang).split(" — ")[0] if step.kind == "choice" else value
        lines.append(f"• {html.escape(pick(step.lbl, lang))}: <b>{html.escape(str(shown))}</b>")
    return "\n".join(lines)


async def _confirm(target: Message, state: FSMContext, store, lang: str, user_id: int) -> None:
    data = await state.get_data()
    service = SERVICES[data["slug"]]
    price = service.price_for(data["answers"])
    balance = await store.balance(user_id)
    await state.set_state(Flow.confirming)
    text = t(lang, "confirm_screen", emoji=service.emoji, title=pick(service.title, lang),
             summary=_summary(data["slug"], data["answers"], lang, data.get("tpl")), price=money(price, lang), balance=money(balance, lang))
    voucher = await store.active_voucher(user_id)
    free = [[IB(text=t(lang, "btn_free"), callback_data="free", style="success")]] \
        if voucher and data["slug"] in voucher["services"] else []
    if free:
        text += t(lang, "voucher_note")
    if balance >= price:
        kb = ui.inline(*free, [IB(text=t(lang, "btn_order"), callback_data="ok", style="primary" if free else "success")],
                       [ui.cancel_button(lang)])
    else:
        need = price - balance
        text += t(lang, "short_by", need=money(need, lang))
        kb = ui.inline(*free, [IB(text=t(lang, "btn_topup_short"), callback_data=f"topup:{need}", style="primary")],
                       [ui.cancel_button(lang)])
    await target.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(Flow.confirming, F.data == "ok")
async def on_ok(callback: CallbackQuery, state: FSMContext, store, settings, lang):
    data = await state.get_data()
    # Holatni darhol tozalaymiz: ikki marta bosilgan tugma ikkinchi buyurtma yaratmasin.
    await state.clear()
    slug = data["slug"]
    service = SERVICES[slug]
    uid = callback.from_user.id
    result = await store.place_order(uid, slug, build_params(service, data["answers"]),
                                     service.price_for(data["answers"]), max_active=settings.per_user_active)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    if result == "limit":
        await callback.message.answer(t(lang, "too_many_active", n=settings.per_user_active))
        return
    if result is None:
        await callback.message.answer(t(lang, "balance_low"))
        return
    if service.profile:
        await store.save_profile(uid, {k: data["answers"].get(k) for k in STUDENT_KEYS})
    await callback.message.answer(
        t(lang, "order_accepted", id=result, emoji=service.emoji, title=pick(service.title, lang),
          eta=pick(service.eta, lang)),
        parse_mode="HTML", reply_markup=ui.main_menu(lang))


@router.callback_query(Flow.confirming, F.data == "free")
async def on_free(callback: CallbackQuery, state: FSMContext, store, settings, lang):
    data = await state.get_data()
    await state.clear()
    slug = data["slug"]
    service = SERVICES[slug]
    uid = callback.from_user.id
    voucher = await store.active_voucher(uid)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    if not voucher or slug not in voucher["services"]:
        await callback.message.answer(t(lang, "free_gone"))
        return
    result = await store.place_free_order(uid, slug, build_params(service, data["answers"]), voucher["id"],
                                          max_active=settings.per_user_active)
    if result == "limit":
        await callback.message.answer(t(lang, "too_many_active", n=settings.per_user_active))
        return
    if result is None:
        await callback.message.answer(t(lang, "free_gone"))
        return
    if service.profile:
        await store.save_profile(uid, {k: data["answers"].get(k) for k in STUDENT_KEYS})
    await callback.message.answer(
        t(lang, "order_accepted", id=result, emoji=service.emoji, title=pick(service.title, lang),
          eta=pick(service.eta, lang)),
        parse_mode="HTML", reply_markup=ui.main_menu(lang))


@router.callback_query(F.data == "cancel")
async def on_cancel(callback: CallbackQuery, state: FSMContext, lang):
    await state.clear()
    await callback.answer(t(lang, "cancelled_toast"))
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(t(lang, "cancelled"), reply_markup=ui.main_menu(lang))
