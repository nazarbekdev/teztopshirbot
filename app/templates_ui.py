"""
Taqdimot shablonlari karuseli — asosiy botdagi (`presentation/common.py`) bilan bir xil ko'rinish:
bitta xabarda rasm, ◀ ✅ ▶ va raqamlar; fan/mavzuga mos soha shablonlari birinchi turadi.

Shablonlar va rasmlar hamkor API'dan (`GET /templates`, `/preview`). Rasm Telegram'ga BIR MARTA
yuklanadi va `file_id` bazada saqlanadi (`tpl_files`): har foydalanuvchi uchun 70 ta PNG qayta
yuklanmaydi. API javob bermasa shablon qadami o'tkazib yuboriladi (hamkor standart shablonni oladi).
"""

import logging

from aiogram.types import BufferedInputFile, InlineKeyboardButton as IB, InputMediaPhoto, Message

from . import ui
from .i18n import pick, t

logger = logging.getLogger(__name__)


def compact(listing: dict) -> dict:
    """FSM'ga sig'adigan ixcham shakl: tartib + har shablon nomi va yo'nalishi."""
    info = {}
    for tpl in listing["data"]:
        d = tpl.get("direction")
        info[tpl["id"]] = {"n": tpl["name"], "d": ({"e": d["emoji"], "n": d["name"]} if d else None)}
    return {"order": [tpl["id"] for tpl in listing["data"]], "info": info}


def name_of(tpl: dict, template_id: str, lang: str) -> str:
    item = tpl["info"].get(template_id)
    return pick(item["n"], lang) if item else template_id


def caption(tpl: dict, idx: int, lang: str) -> str:
    template_id = tpl["order"][idx]
    item = tpl["info"][template_id]
    lines = [f"🎨 <b>{pick(item['n'], lang)}</b>"]
    if item["d"]:
        lines.append(t(lang, "tpl_badge", emoji=item["d"]["e"], name=pick(item["d"]["n"], lang)))
    lines.append(f"<i>{t(lang, 'tpl_hint', pos=idx + 1, total=len(tpl['order']))}</i>")
    return "\n".join(lines)


def keyboard(tpl: dict, idx: int, lang: str):
    total = len(tpl["order"])
    rows = [[IB(text="◀️", callback_data=f"tn:{(idx - 1) % total}"),
             IB(text=t(lang, "btn_select"), callback_data=f"ts:{idx}", style="success"),
             IB(text="▶️", callback_data=f"tn:{(idx + 1) % total}")]]
    cols = 5 if total <= 25 else 6
    for start in range(0, total, cols):
        rows.append([IB(text=f"·{i + 1}·" if i == idx else str(i + 1), callback_data=f"tn:{i}")
                     for i in range(start, min(start + cols, total))])
    return ui.inline(*rows)


async def _photo(store, api, template_id: str, *, fresh: bool = False):
    """Keshdagi file_id; yo'q bo'lsa API'dan yuklab olingan rasm (yuborilgach file_id saqlanadi)."""
    if not fresh:
        file_id = await store.tpl_file(template_id)
        if file_id:
            return file_id
    return BufferedInputFile(await api.template_preview(template_id), filename=f"{template_id}.png")


def _remember_args(sent) -> str | None:
    photo = getattr(sent, "photo", None)
    return photo[-1].file_id if photo else None


async def open_carousel(target: Message, store, api, tpl: dict, lang: str) -> int | None:
    """Karuselni ochadi; xabar ID'sini qaytaradi. Rasm yuborilmasa None."""
    template_id = tpl["order"][0]
    for fresh in (False, True):
        try:
            sent = await target.answer_photo(photo=await _photo(store, api, template_id, fresh=fresh),
                                             caption=caption(tpl, 0, lang), reply_markup=keyboard(tpl, 0, lang),
                                             parse_mode="HTML")
            file_id = _remember_args(sent)
            if file_id:
                await store.set_tpl_file(template_id, file_id)
            return sent.message_id
        except Exception as e:
            logger.warning("Shablon karuseli ochilmadi (%s, fresh=%s): %s", template_id, fresh, e)
            await store.forget_tpl_file(template_id)
    return None


async def show(callback_message: Message, store, api, tpl: dict, idx: int, lang: str) -> None:
    """Karuselni boshqa shablonga almashtiradi (xabarni tahrirlaydi)."""
    template_id = tpl["order"][idx]
    for fresh in (False, True):
        try:
            result = await callback_message.edit_media(
                media=InputMediaPhoto(media=await _photo(store, api, template_id, fresh=fresh),
                                      caption=caption(tpl, idx, lang), parse_mode="HTML"),
                reply_markup=keyboard(tpl, idx, lang))
            file_id = _remember_args(result) if not isinstance(result, bool) else None
            if file_id:
                await store.set_tpl_file(template_id, file_id)
            return
        except Exception as e:
            logger.warning("Shablon almashmadi (%s, fresh=%s): %s", template_id, fresh, e)
            await store.forget_tpl_file(template_id)
