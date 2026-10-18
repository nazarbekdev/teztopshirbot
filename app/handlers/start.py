"""Til tanlash, shartlarga rozilik, /start, yordam."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import subscription, ui
from ..catalog import ORDER, SERVICES, pick
from ..i18n import LANGS, t

router = Router()


def contact_of(settings, lang: str) -> str:
    return f"@{settings.support_username}" if settings.support_username else t(lang, "admin_word")


def welcome_text(name: str, lang: str) -> str:
    lines = [f"{SERVICES[s].emoji} {pick(SERVICES[s].title, lang)} — <b>{ui.price_line(s, lang)}</b>" for s in ORDER]
    return t(lang, "welcome", name=name, services="\n".join(lines))


async def show_menu(message: Message, user_name: str, lang: str) -> None:
    await message.answer(welcome_text(user_name, lang), parse_mode="HTML", reply_markup=ui.main_menu(lang))


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, store, settings, alert, lang):
    await state.clear()
    if not lang:
        await message.answer(t(None, "lang_prompt"), reply_markup=ui.lang_keyboard())
        return
    user = await store.user(message.from_user.id)
    if user.get("consent_version") != ui.CONSENT_VERSION:
        await message.answer(t(lang, "consent_intro"), parse_mode="HTML", reply_markup=ui.consent_keyboard(lang))
        return
    if not await subscription.is_member(message.bot, settings, message.from_user.id, alert):
        await message.answer(t(lang, "sub_required"), parse_mode="HTML",
                             reply_markup=ui.subscribe_keyboard(lang, settings.required_channel))
        return
    await show_menu(message, message.from_user.full_name, lang)


@router.message(F.text.in_(ui.LANG_TEXTS))
async def change_lang(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(t(None, "lang_prompt"), reply_markup=ui.lang_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def lang_chosen(callback: CallbackQuery, state: FSMContext, store, settings, alert):
    code = callback.data.split(":")[1]
    if code not in LANGS:
        await callback.answer()
        return
    await state.clear()
    await store.set_lang(callback.from_user.id, code)
    await callback.answer(t(code, "lang_changed"))
    await callback.message.edit_reply_markup(reply_markup=None)
    user = await store.user(callback.from_user.id)
    if user.get("consent_version") != ui.CONSENT_VERSION:
        await callback.message.answer(t(code, "consent_intro"), parse_mode="HTML", reply_markup=ui.consent_keyboard(code))
    elif not await subscription.is_member(callback.bot, settings, callback.from_user.id, alert):
        # Tilni almashtirish a'zo bo'lmaganga menyu ochib bermasligi kerak
        await callback.message.answer(t(code, "sub_required"), parse_mode="HTML",
                                      reply_markup=ui.subscribe_keyboard(code, settings.required_channel))
    else:
        await show_menu(callback.message, callback.from_user.full_name, code)


def _full_text(lang: str, settings) -> str:
    return t(lang, "consent_full", version=ui.CONSENT_VERSION, contact=contact_of(settings, lang))


@router.callback_query(F.data == "sub:check")
async def sub_check(callback: CallbackQuery, store, settings, alert):
    lang = (await store.user(callback.from_user.id)).get("lang") or "uz"
    subscription.forget(callback.from_user.id)
    if not await subscription.is_member(callback.bot, settings, callback.from_user.id, alert):
        await callback.answer(t(lang, "not_member"), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await show_menu(callback.message, callback.from_user.full_name, lang)


@router.callback_query(F.data == "consent:full")
async def consent_full(callback: CallbackQuery, store, settings):
    lang = (await store.user(callback.from_user.id)).get("lang") or "uz"
    await callback.answer()
    await callback.message.answer(_full_text(lang, settings), parse_mode="HTML",
                                  reply_markup=ui.consent_keyboard(lang, with_full=False))


@router.callback_query(F.data == "consent:yes")
async def consent_yes(callback: CallbackQuery, store, settings, alert):
    lang = (await store.user(callback.from_user.id)).get("lang") or "uz"
    await store.accept_consent(callback.from_user.id, ui.CONSENT_VERSION)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    if not await subscription.is_member(callback.bot, settings, callback.from_user.id, alert):
        await callback.message.answer(t(lang, "sub_required"), parse_mode="HTML",
                                      reply_markup=ui.subscribe_keyboard(lang, settings.required_channel))
        return
    await show_menu(callback.message, callback.from_user.full_name, lang)


@router.message(Command("privacy"))
async def privacy(message: Message, store, settings, lang):
    lang = lang or "uz"
    user = await store.user(message.from_user.id)
    accepted = user.get("consent_version") == ui.CONSENT_VERSION
    await message.answer(_full_text(lang, settings), parse_mode="HTML",
                         reply_markup=None if accepted else ui.consent_keyboard(lang, with_full=False))


@router.message(Command("menu"))
async def menu(message: Message, state: FSMContext, lang):
    await state.clear()
    await message.answer(t(lang, "menu_home"), reply_markup=ui.main_menu(lang))


@router.message(F.text.in_(ui.HELP_TEXTS))
@router.message(Command("help"))
async def help_(message: Message, state: FSMContext, settings, lang):
    await state.clear()
    await message.answer(t(lang, "help", contact=contact_of(settings, lang)), parse_mode="HTML")
