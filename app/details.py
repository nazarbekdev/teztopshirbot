"""
«Mavzu talabaning O'Z joyi haqidami» tekshiruvi — asosiy botdagi `needs_details` bilan bir xil qoida
(`bot/handlers/presentation/common.py`).

Nega kerak: "Bizning mahalla", "Мой город" kabi mavzuda joy nomi yo'q; model o'zi shahar tanlab, boshqa
joy haqida yozib yuborgan (1 yulduzli baho). Shunday mavzuda taqdimotdan oldin bitta aniqlashtiruvchi
savol beriladi, javob API'ning `notes` maydoniga ketadi.
"""

import re

PERSONAL_TOKENS = frozenset({
    "mening", "bizning", "mahallam", "mahallamiz", "maktabim", "maktabimiz",
    "oilam", "oilamiz", "shahrim", "shahrimiz", "qishlogim", "qishlogimiz",
    "tumanim", "tumanimiz", "viloyatim", "viloyatimiz", "yurtim", "yurtimiz",
    "kollejim", "kollejimiz", "litseyim", "universitetim", "korxonamiz",
    "мой", "моя", "моё", "мое", "мои", "наш", "наша", "наше", "наши",
    "моего", "нашего", "my", "our",
})
SKIP_DETAILS = {"-", "—", "yo'q", "yoq", "нет", "no", "skip"}


def needs_details(topic: str) -> bool:
    words = re.findall(r"\w+", (topic or "").lower().replace("'", "").replace("ʻ", "").replace("‘", ""))
    return any(w in PERSONAL_TOKENS for w in words)
