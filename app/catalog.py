"""
Xizmatlar katalogi: mijoz narxi va savollar ketma-ketligi (uch tilda).

Savollar tartibi asosiy OsonTopshir botidagi bilan bir xil: avval HUJJAT TILI, keyin
(kurs ishi/mustaqil ish/referatda) saqlangan ma'lumotlar yoki titul ma'lumotlari, so'ng
fan, mavzu, hajm va qo'shimcha maydonlar. Hamkor API qo'llamaydigan narsa (shablon tanlash,
qo'lda reja) bu botda yo'q.

NARX — mijoz narxi (so'm). Hamkor narxi alohida (`GET /credits`); bu yerdagi narx har doim
undan kamida 10% yuqori (`tests/test_catalog.py`). Narx hajmga QARAMAYDI, faqat kurs ishida
bet oralig'iga qarab 3 pog'ona.

Parametr qiymatlari hamkor API qoidalariga mos (`partner-docs`):
  kurs_ishi   pages 20-30 / 30-40 / 40-50 (katta hajm hamkorda `allow_large_pages` bilan)
  mustaqil_ish/referat   pages 10/15/20
  taqdimot    slides 10/15/20/25/30
  test        questions 10..30
  krossvord   word_count 10..30
"""

from dataclasses import dataclass

from .details import needs_details
from .i18n import LANG_NAMES, pick

CURRENCY = {"uz": "so'm", "ru": "сум", "en": "UZS"}


def money(value: int, lang: str = "uz") -> str:
    return f"{value:,}".replace(",", " ") + " " + pick(CURRENCY, lang)


@dataclass(frozen=True)
class Step:
    key: str                                   # params kaliti (target="student" bo'lsa student ichida)
    p: dict                                    # savol matni {uz, ru, en}
    lbl: dict                                  # tasdiq ekranidagi nomi
    kind: str = "text"                         # text | choice | profile
    choices: tuple = ()                        # (qiymat, tugma matni yoki {uz,ru,en})
    optional: bool = False
    lo: int = 1
    hi: int = 300
    target: str = "params"                     # params | student
    numeric: bool = False                      # choice qiymati songa aylanadi
    when: str = ""                             # shartli qadam: "details" — mavzu o'z joyi haqida bo'lsagina so'raladi


@dataclass(frozen=True)
class Service:
    slug: str
    emoji: str
    title: dict
    note: dict
    eta: dict
    steps: tuple
    price: int | dict                          # int yoki {hajm qiymati: narx} (hajm kaliti — price_key)
    price_key: str = "pages"
    profile: bool = False                      # titul ma'lumotlari saqlanadi va qayta ishlatiladi

    def price_for(self, answers: dict) -> int:
        if isinstance(self.price, dict):
            return self.price.get(answers.get(self.price_key), min(self.price.values()))
        return self.price

    @property
    def min_price(self) -> int:
        return min(self.price.values()) if isinstance(self.price, dict) else self.price

    @property
    def is_tiered(self) -> bool:
        return isinstance(self.price, dict)


def _d(uz, ru, en) -> dict:
    return {"uz": uz, "ru": ru, "en": en}


def choice_label(step: Step, value, lang: str) -> str:
    for v, label in step.choices:
        if str(v) == str(value):
            return label if isinstance(label, str) else pick(label, lang)
    return str(value)


def _nums(values) -> tuple:
    return tuple((str(v), str(v)) for v in values)


LANG_STEP = Step(
    "language",
    _d("🌐 Hujjat qaysi tilda bo'lsin?", "🌐 На каком языке подготовить документ?", "🌐 Which language should the document be in?"),
    _d("Hujjat tili", "Язык документа", "Document language"),
    kind="choice", choices=tuple(LANG_NAMES.items()),
)
PROFILE_STEP = Step("_profile", _d("", "", ""), _d("", "", ""), kind="profile")
TEMPLATE_STEP = Step("template", _d("", "", ""), _d("Shablon", "Шаблон", "Template"), kind="template")
# Asosiy botdagi savol (faqat mavzu talabaning o'z joyi haqida bo'lsa); javob API'ning `notes` maydoniga ketadi
DETAILS_STEP = Step(
    "notes",
    _d("📍 Bu mavzu <b>sizning joyingiz</b> haqida. Taqdimot aynan u haqida bo'lishi uchun qisqa yozing: shahar/tuman, "
       "mahalla yoki tashkilot nomi, bilganlaringiz.\n\n<i>Masalan: Samarqand sh., \"Registon\" mahallasi, 1200 xonadon, "
       "maktab va bozor bor</i>\n\nUmumiy yozilsin desangiz — <b>-</b> yuboring.",
       "📍 Эта тема о <b>вашем месте</b>. Чтобы презентация была именно о нём, напишите коротко: город/район, махалля "
       "или организация, что знаете.\n\n<i>Например: г. Самарканд, махалля «Регистан», 1200 домов, есть школа и рынок</i>\n\n"
       "Если нужно в общем виде — отправьте <b>-</b>.",
       "📍 This topic is about <b>your own place</b>. So the presentation is about it, briefly write the city/district, "
       "neighbourhood or organisation and what you know.\n\nIf you want it general — send <b>-</b>."),
    _d("Qo'shimcha ma'lumot", "Дополнительно", "Details"), optional=True, hi=500, when="details",
)
SUBJECT = Step(
    "subject",
    _d("📚 <b>Fan nomi</b>ni yozing (masalan: Menejment):", "📚 Напишите <b>название предмета</b> (например: Менеджмент):",
       "📚 Enter the <b>subject</b> (e.g. Management):"),
    _d("Fan", "Предмет", "Subject"), lo=2, hi=100,
)
TOPIC = Step(
    "topic",
    _d("✍️ <b>Mavzu</b>ni yozing (5–300 belgi):", "✍️ Напишите <b>тему</b> (5–300 символов):", "✍️ Write the <b>topic</b> (5–300 characters):"),
    _d("Mavzu", "Тема", "Topic"), lo=5, hi=300,
)
TOPIC_SHORT = Step(
    "topic",
    _d("✍️ <b>Mavzu</b>ni yozing (3–300 belgi):", "✍️ Напишите <b>тему</b> (3–300 символов):", "✍️ Write the <b>topic</b> (3–300 characters):"),
    _d("Mavzu", "Тема", "Topic"), lo=3, hi=300,
)


def _student(key: str, uz: str, ru: str, en: str, lbl: tuple) -> Step:
    return Step(key, _d(uz, ru, en), _d(*lbl), optional=True, hi=150, target="student")


FULL_NAME = _student("full_name", "👤 <b>Ism-familiyangiz</b> (titul varag'i uchun):", "👤 Ваши <b>имя и фамилия</b> (для титульного листа):",
                     "👤 Your <b>full name</b> (for the title page):", ("Ism-familiya", "Имя и фамилия", "Full name"))
UNIVERSITY = _student("university", "🏛 <b>Universitet</b> nomi:", "🏛 Название <b>университета</b>:", "🏛 <b>University</b> name:",
                      ("Universitet", "Университет", "University"))
FACULTY = _student("faculty", "🏫 <b>Fakultet</b>:", "🏫 <b>Факультет</b>:", "🏫 <b>Faculty</b>:", ("Fakultet", "Факультет", "Faculty"))
KAFEDRA = _student("kafedra", "🏢 <b>Kafedra</b>:", "🏢 <b>Кафедра</b>:", "🏢 <b>Department</b>:", ("Kafedra", "Кафедра", "Department"))
DIRECTION = _student("direction", "🎯 <b>Ta'lim yo'nalishi</b>:", "🎯 <b>Направление обучения</b>:", "🎯 <b>Field of study</b>:",
                     ("Yo'nalish", "Направление", "Field of study"))
GROUP = _student("group", "👥 <b>Guruh</b>:", "👥 <b>Группа</b>:", "👥 <b>Group</b>:", ("Guruh", "Группа", "Group"))
SUPERVISOR = _student("supervisor", "🧑‍🏫 <b>Ilmiy rahbar</b>:", "🧑‍🏫 <b>Научный руководитель</b>:", "🧑‍🏫 <b>Supervisor</b>:",
                      ("Ilmiy rahbar", "Руководитель", "Supervisor"))
CITY = _student("city", "🏙 <b>Shahar</b>:", "🏙 <b>Город</b>:", "🏙 <b>City</b>:", ("Shahar", "Город", "City"))

# Kurs ishi pog'onalari: narx bet oralig'iga qarab
KURS_PRICES = {"20-30": 55_000, "30-40": 65_000, "40-50": 75_000}


def _kurs_pages() -> Step:
    labels = tuple(
        (rng, _d(f"{rng} bet — {money(price, 'uz')}", f"{rng} стр. — {money(price, 'ru')}", f"{rng} pages — {money(price, 'en')}"))
        for rng, price in KURS_PRICES.items()
    )
    return Step("pages", _d("📄 Necha bet bo'lsin?", "📄 Сколько страниц?", "📄 How many pages?"),
                _d("Hajm", "Объём", "Length"), kind="choice", choices=labels)


def _count(key: str, uz: str, ru: str, en: str, lbl: tuple, values, **kw) -> Step:
    return Step(key, _d(uz, ru, en), _d(*lbl), kind="choice", choices=_nums(values), numeric=True, **kw)


def ladder(base: int, values) -> dict:
    """Asosiy bot uslubi: har pog'ona +1 000 so'm (birinchi qiymat — boshlang'ich narx)."""
    return {v: base + 1_000 * i for i, v in enumerate(values)}


def _priced(step: Step, prices: dict, unit: tuple) -> Step:
    """Tanlov tugmalariga narxni qo'shadi: «15 slayd — 5 500 so'm». Qiymat (son) o'zgarmaydi."""
    choices = tuple(
        (str(v), _d(*(f"{v} {unit[i]} — {money(prices[int(v)], lang)}" for i, lang in enumerate(("uz", "ru", "en")))))
        for v, _ in step.choices
    )
    return Step(step.key, step.p, step.lbl, kind="choice", choices=choices, numeric=True)


SIMPLE_PRICES = ladder(4_500, (10, 15, 20))            # mustaqil ish va referat
SLIDE_PRICES = ladder(4_500, (10, 15, 20, 25, 30))
TEST_PRICES = ladder(2_500, (10, 15, 20, 25, 30))
CROSSWORD_PRICES = ladder(1_500, (10, 15, 20, 25, 30))

PAGES_SIMPLE = _priced(
    _count("pages", "📄 Necha bet?", "📄 Сколько страниц?", "📄 How many pages?", ("Hajm (bet)", "Объём (стр.)", "Length (pages)"), (10, 15, 20)),
    SIMPLE_PRICES, ("bet", "стр.", "pages"))

SERVICES: dict[str, Service] = {
    "taqdimot": Service(
        "taqdimot", "📊", _d("Taqdimot", "Презентация", "Presentation"),
        _d("PPTX va PDF fayl", "Файлы PPTX и PDF", "PPTX and PDF files"),
        _d("1–3 daqiqa", "1–3 минуты", "1–3 minutes"),
        (
            LANG_STEP, SUBJECT, TOPIC, DETAILS_STEP, TEMPLATE_STEP,
            _priced(_count("slides", "🎞 Nechta slayd?", "🎞 Сколько слайдов?", "🎞 How many slides?", ("Slaydlar", "Слайды", "Slides"), (10, 15, 20, 25, 30)),
                    SLIDE_PRICES, ("slayd", "слайдов", "slides")),
            Step("presenter", _d("👤 Taqdimotchi ismini kiriting:\n\n<i>Masalan: Azizbek Alijonov</i>",
                                 "👤 Введите имя докладчика:\n\n<i>Например: Азизбек Алижонов</i>",
                                 "👤 Enter the presenter's name:\n\n<i>Example: Azizbek Alijonov</i>"),
                 _d("Taqdimotchi", "Докладчик", "Presenter"), optional=True, hi=100),
            Step("supervisor", _d("👨‍🏫 Rahbar (ustoz) ismini kiriting:\n\n<i>Masalan: Prof. Azizbek Alijonov</i>",
                                  "👨‍🏫 Введите имя руководителя (преподавателя):\n\n<i>Например: Проф. Азизбек Алижонов</i>",
                                  "👨‍🏫 Enter the supervisor's (teacher's) name:\n\n<i>Example: Prof. Azizbek Alijonov</i>"),
                 _d("Rahbar", "Руководитель", "Supervisor"), optional=True, hi=100),
        ),
        SLIDE_PRICES, price_key="slides",
    ),
    "kurs_ishi": Service(
        "kurs_ishi", "📖", _d("Kurs ishi", "Курсовая работа", "Coursework"),
        _d("DOCX, 20–50 bet", "DOCX, 20–50 стр.", "DOCX, 20–50 pages"),
        _d("5–15 daqiqa", "5–15 минут", "5–15 minutes"),
        (LANG_STEP, PROFILE_STEP, FULL_NAME, UNIVERSITY, FACULTY, KAFEDRA, DIRECTION, GROUP, SUPERVISOR, CITY,
         SUBJECT, TOPIC, _kurs_pages()),
        KURS_PRICES, profile=True,
    ),
    "mustaqil_ish": Service(
        "mustaqil_ish", "📝", _d("Mustaqil ish", "Самостоятельная работа", "Independent work"),
        _d("DOCX, 20 betgacha", "DOCX, до 20 стр.", "DOCX, up to 20 pages"),
        _d("2–6 daqiqa", "2–6 минут", "2–6 minutes"),
        (LANG_STEP, PROFILE_STEP, FULL_NAME, UNIVERSITY, FACULTY, SUPERVISOR, SUBJECT, TOPIC, PAGES_SIMPLE),
        SIMPLE_PRICES, profile=True,
    ),
    "referat": Service(
        "referat", "📄", _d("Referat", "Реферат", "Essay"),
        _d("DOCX, 20 betgacha", "DOCX, до 20 стр.", "DOCX, up to 20 pages"),
        _d("2–6 daqiqa", "2–6 минут", "2–6 minutes"),
        (LANG_STEP, PROFILE_STEP, FULL_NAME, UNIVERSITY, FACULTY, SUPERVISOR, SUBJECT, TOPIC, PAGES_SIMPLE),
        SIMPLE_PRICES, profile=True,
    ),
    "test": Service(
        "test", "❓", _d("Test", "Тест", "Test"),
        _d("DOCX: savollar va javoblar kaliti", "DOCX: вопросы и ключ ответов", "DOCX: questions and answer key"),
        _d("1–3 daqiqa", "1–3 минуты", "1–3 minutes"),
        (LANG_STEP, SUBJECT, TOPIC_SHORT,
         _priced(_count("questions", "🔢 Nechta savol?", "🔢 Сколько вопросов?", "🔢 How many questions?", ("Savollar", "Вопросы", "Questions"), (10, 15, 20, 25, 30)),
                 TEST_PRICES, ("ta savol", "вопросов", "questions"))),
        TEST_PRICES, price_key="questions",
    ),
    "krossvord": Service(
        "krossvord", "🧩", _d("Krossvord", "Кроссворд", "Crossword"),
        _d("PDF", "PDF", "PDF"),
        _d("1–2 daqiqa", "1–2 минуты", "1–2 minutes"),
        (LANG_STEP, SUBJECT, TOPIC_SHORT,
         _priced(_count("word_count", "🔢 Nechta so'z?", "🔢 Сколько слов?", "🔢 How many words?", ("So'zlar", "Слова", "Words"), (10, 15, 20, 25, 30)),
                 CROSSWORD_PRICES, ("ta so'z", "слов", "words"))),
        CROSSWORD_PRICES, price_key="word_count",
    ),
}

ORDER = ("taqdimot", "kurs_ishi", "mustaqil_ish", "referat", "test", "krossvord")
STUDENT_KEYS = ("full_name", "university", "faculty", "kafedra", "direction", "group", "supervisor", "city")


def title(slug: str, lang: str) -> str:
    return pick(SERVICES[slug].title, lang)


def build_params(service: Service, answers: dict) -> dict:
    """Mijoz javoblaridan hamkor API `params` obyekti. Bo'sh ixtiyoriy maydonlar tushiriladi."""
    params: dict = {}
    student: dict = {}
    for step in service.steps:
        if step.kind == "profile":
            continue
        if step.when == "details" and not needs_details(answers.get("topic", "")):
            continue                                   # shartli qadam so'ralmagan — eski javob ham ketmaydi
        value = answers.get(step.key)
        if value in (None, ""):
            continue
        (student if step.target == "student" else params)[step.key] = value
    if student:
        params["student"] = student
    if service.slug == "krossvord" and params.get("subject"):
        # Hamkor API'da krossvord uchun `subject` yo'q: fan mavzuga qo'shiladi
        params["topic"] = f"{params['topic']} ({params['subject']})"
    if service.slug == "krossvord":
        params.pop("subject", None)
    return params
