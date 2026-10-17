"""
Xizmatlar katalogi: mijoz narxi va savollar ketma-ketligi.

NARX — mijozga ko'rsatiladigan narx (so'm). Hamkor (OsonTopshir) narxi
alohida va u `GET /credits` da keladi; bu yerdagi narx har doim undan yuqori
bo'lishi shart (`tests/test_catalog.py` shuni tekshiradi). Narx hajmga
QARAMAYDI — hamkor API'da ham shunday, shuning uchun hajm tepasi yopiq.

Parametr qiymatlari hamkor API qoidalariga mos (`partner-docs`):
  kurs_ishi    pages faqat 20-30
  mustaqil_ish/referat   pages 10/15/20
  taqdimot     slides 10/15/20/25/30
  test         questions 10..30
  krossvord    word_count 10..30
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Step:
    key: str                              # params kaliti (target="student" bo'lsa student ichida)
    prompt: str
    kind: str = "text"                    # text | choice
    choices: tuple[tuple[str, str], ...] = ()   # (qiymat, tugma matni)
    optional: bool = False
    lo: int = 1
    hi: int = 300
    target: str = "params"                # params | student
    numeric: bool = False                 # choice qiymati songa aylanadi


LANG = (("uz", "🇺🇿 O'zbekcha"), ("ru", "🇷🇺 Русский"), ("en", "🇬🇧 English"))


def _nums(values) -> tuple[tuple[str, str], ...]:
    return tuple((str(v), str(v)) for v in values)


@dataclass(frozen=True)
class Service:
    slug: str
    emoji: str
    title: str
    price: int
    eta: str
    steps: tuple[Step, ...]
    note: str = ""


_TOPIC = Step("topic", "✍️ <b>Mavzuni</b> yozing (5–300 belgi):", lo=5, hi=300)
_SUBJECT = Step("subject", "📚 <b>Fan nomini</b> yozing (masalan: Menejment):", lo=2, hi=100)
_LANG = Step("language", "🌐 Qaysi tilda tayyorlaymiz?", kind="choice", choices=LANG)

SERVICES: dict[str, Service] = {
    "taqdimot": Service(
        "taqdimot", "📊", "Taqdimot", 4_500, "1–3 daqiqa",
        (
            _TOPIC,
            Step("slides", "🎞 Nechta slayd?", kind="choice", choices=_nums((10, 15, 20, 25, 30)), numeric=True),
            _LANG,
            Step("presenter", "👤 Birinchi slaydga <b>ismingizni</b> yozaymi?", optional=True, hi=100),
        ),
        "PPTX va PDF fayl",
    ),
    "kurs_ishi": Service(
        "kurs_ishi", "📖", "Kurs ishi", 39_000, "5–15 daqiqa",
        (
            _TOPIC, _SUBJECT, _LANG,
            Step("full_name", "👤 <b>Ism-familiyangiz</b> (titul varag'i uchun):", optional=True, hi=150, target="student"),
            Step("university", "🏛 <b>Universitet</b> nomi:", optional=True, hi=150, target="student"),
            Step("faculty", "🏫 <b>Fakultet</b>:", optional=True, hi=150, target="student"),
            Step("group", "👥 <b>Guruh</b>:", optional=True, hi=150, target="student"),
            Step("supervisor", "🧑‍🏫 <b>Ilmiy rahbar</b>:", optional=True, hi=150, target="student"),
        ),
        "DOCX, 20–30 bet",
    ),
    "mustaqil_ish": Service(
        "mustaqil_ish", "📝", "Mustaqil ish", 5_500, "2–6 daqiqa",
        (
            _TOPIC, _SUBJECT,
            Step("pages", "📄 Necha bet?", kind="choice", choices=_nums((10, 15, 20)), numeric=True),
            _LANG,
            Step("full_name", "👤 <b>Ism-familiyangiz</b> (titul varag'i uchun):", optional=True, hi=150, target="student"),
            Step("university", "🏛 <b>Universitet</b> nomi:", optional=True, hi=150, target="student"),
        ),
        "DOCX, 20 betgacha",
    ),
    "referat": Service(
        "referat", "📄", "Referat", 5_500, "2–6 daqiqa",
        (
            _TOPIC, _SUBJECT,
            Step("pages", "📄 Necha bet?", kind="choice", choices=_nums((10, 15, 20)), numeric=True),
            _LANG,
            Step("full_name", "👤 <b>Ism-familiyangiz</b> (titul varag'i uchun):", optional=True, hi=150, target="student"),
            Step("university", "🏛 <b>Universitet</b> nomi:", optional=True, hi=150, target="student"),
        ),
        "DOCX, 20 betgacha",
    ),
    "test": Service(
        "test", "❓", "Test", 2_500, "1–3 daqiqa",
        (
            Step("topic", "✍️ Test <b>mavzusini</b> yozing:", lo=3, hi=300),
            Step("questions", "🔢 Nechta savol?", kind="choice", choices=_nums((10, 15, 20, 25, 30)), numeric=True),
            _LANG,
        ),
        "DOCX: savollar va javoblar kaliti",
    ),
    "krossvord": Service(
        "krossvord", "🧩", "Krossvord", 1_900, "1–2 daqiqa",
        (
            Step("topic", "✍️ Krossvord <b>mavzusini</b> yozing:", lo=3, hi=300),
            Step("word_count", "🔢 Nechta so'z?", kind="choice", choices=_nums((10, 15, 20, 25, 30)), numeric=True),
            _LANG,
        ),
        "PDF",
    ),
}

ORDER = ("taqdimot", "kurs_ishi", "mustaqil_ish", "referat", "test", "krossvord")

STATUS_LABEL = {
    "queued": "⏳ Navbatda",
    "submitted": "⚙️ Tayyorlanmoqda",
    "processing": "⚙️ Tayyorlanmoqda",
    "succeeded": "✅ Tayyor",
    "failed": "❌ Xato (pul qaytarilgan)",
    "canceled": "🚫 Bekor qilingan",
}


def money(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " so'm"


def build_params(service: Service, answers: dict) -> dict:
    """Mijoz javoblaridan hamkor API `params` obyekti. Bo'sh ixtiyoriy maydonlar tushiriladi."""
    params: dict = {}
    student: dict = {}
    for step in service.steps:
        value = answers.get(step.key)
        if value in (None, ""):
            continue
        (student if step.target == "student" else params)[step.key] = value
    if student:
        params["student"] = student
    if service.slug == "kurs_ishi":
        params["pages"] = "20-30"
    return params
