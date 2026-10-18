"""
«Amaliy qism uchun HAQIQIY korxona ma'lumoti» tozalash — hamkor API (`partner/catalog.py::_case_data`) va asosiy bot
(`utils/case_data.py::clean`) bilan BIR XIL qoida: raqamsiz yoki «yo'q» kabi javob ma'lumot emas. API shu qoida bilan
yaroqsiz ma'lumotni rad etadi (400), shuning uchun bot uni buyurtmadan OLDIN tekshiradi.
"""

import re

MAX_CHARS = 4000
MIN_USEFUL_CHARS = 25

_NO_DATA = re.compile(r"^\W*(yo['‘’ʻ`]?q|нет|no|none|yok|йўқ|ҳеҷ|жоқ|[-–—]+)\W*$", re.IGNORECASE)


def clean(text: str | None) -> str:
    t = re.sub(r"[ \t]+", " ", (text or "").replace("\r", "")).strip()
    t = re.sub(r"\n{3,}", "\n\n", t)[:MAX_CHARS]
    if len(t) < MIN_USEFUL_CHARS or _NO_DATA.match(t) or not re.search(r"\d", t):
        return ""
    return t
