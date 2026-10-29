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
    when: str = ""                             # shartli qadam (qarang `is_active`): details | plan_auto | plan_manual | case


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


def is_active(step: "Step", answers: dict) -> bool:
    """
    Shartli qadam hozir so'ralishi kerakmi.
      details      mavzu talabaning o'z joyi haqida (aniqlashtiruvchi savol)
      plan_auto    reja avtomatik tuzilsin deb tanlangan
      plan_manual  o'z rejasini yozmoqchi
      case         «korxona ma'lumotini kiritish» tugmasi bosilgan
      style_uni    maqola uslubi — universitet (5/7 bet)
      style_adv    maqola uslubi — imrad yoki oak (7/10 bet, soha va foydalanuvchi ma'lumoti so'raladi)
    """
    when = step.when
    if not when:
        return True
    if when == "details":
        return needs_details(answers.get("topic", ""))
    if when == "plan_auto":
        return answers.get("plan_mode") == "auto"
    if when == "plan_manual":
        return answers.get("plan_mode") == "manual"
    if when == "case":
        return bool(answers.get("_case"))
    if when == "style_uni":
        return answers.get("style", "universitet") == "universitet"
    if when == "style_adv":
        return answers.get("style") in ("imrad", "oak")
    raise ValueError(f"noma'lum shart: {when}")


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

KURS_LANGS = (("uz", "🇺🇿 O'zbek"), ("ru", "🇷🇺 Русский"), ("en", "🇬🇧 English"), ("kz", "🇰🇿 Қазақша"),
              ("tr", "🇹🇷 Türkçe"), ("tj", "🇹🇯 Тоҷикӣ"), ("kaa", "🏳 Qaraqalpaq"))
KURS_LANG_STEP = Step("language", LANG_STEP.p, LANG_STEP.lbl, kind="choice", choices=KURS_LANGS)

TOPIC_KURS = Step(
    "topic",
    _d("Kurs ishi mavzusini to'liq yozing (kamida 10 belgi):", "Введите полную тему курсовой работы (минимум 10 символов):",
       "Enter the full topic of the coursework (at least 10 characters):"),
    _d("Mavzu", "Тема", "Topic"), lo=10, hi=300,
)
SUBJECT_KURS = Step(
    "subject",
    _d("Kurs ishi bajariladigan fan nomini yozing:", "Введите название предмета для курсовой работы:", "Enter the subject name for the coursework:"),
    _d("Fan", "Предмет", "Subject"), lo=4, hi=100,
)
PLAN_MODE = Step(
    "plan_mode",
    _d("📋 Kurs ishi rejasi qanday bo'lsin?", "📋 Каким будет план курсовой работы?", "📋 How would you like the coursework plan?"),
    _d("Reja", "План", "Plan"), kind="choice",
    choices=(("manual", _d("📝 Tayyor rejam bor", "📝 У меня готовый план", "📝 I have a ready plan")),
             ("auto", _d("🤖 Avtomatik generatsiya", "🤖 Автогенерация плана", "🤖 Auto-generate plan"))),
)
PLAN_CFG = Step(
    "plan_cfg",
    _d("Bob va bo'lim sonini tanlang:", "Выберите количество глав и разделов:", "Select the number of chapters and sections:"),
    _d("Tuzilma", "Структура", "Structure"), kind="choice", when="plan_auto",
    choices=tuple((v, _d(f"{v[0]} bob / {v[2]} bo'lim", f"{v[0]} гл. / {v[2]} разд.", f"{v[0]} ch. / {v[2]} sec."))
                  for v in ("2_2", "2_3", "3_2", "3_3")),
)
PLAN_PREVIEW = Step("plan", _d("", "", ""), _d("Reja", "План", "Plan"), kind="plan", when="plan_auto", hi=4000)
PLAN_TEXT = Step(
    "plan",
    _d("📝 Kurs ishi rejangizni yuboring.\n\nNamuna:\n<code>1-bob. Nazariy asoslar\n1.1 Tushuncha va ta'riflar\n1.2 Tarixiy rivojlanish\n"
       "2-bob. Tahlil\n2.1 Holat tahlili\n2.2 Muammolar</code>",
       "📝 Отправьте план вашей курсовой работы.\n\nПример:\n<code>Глава 1. Теоретические основы\n1.1 Понятия и определения\n"
       "1.2 История развития\nГлава 2. Анализ\n2.1 Анализ состояния\n2.2 Проблемы</code>",
       "📝 Send your coursework plan.\n\nExample:\n<code>Chapter 1. Theoretical foundations\n1.1 Concepts and definitions\n"
       "1.2 Historical development\nChapter 2. Analysis\n2.1 State analysis\n2.2 Problems</code>"),
    _d("Reja", "План", "Plan"), when="plan_manual", lo=10, hi=4000,
)
EXTRA = Step(
    "extra_instructions",
    _d("📝 Qo'shimcha talablaringiz bormi?\n\n<i>Masalan: \"statistik jadvallar ko'proq bo'lsin\", \"O'zbekiston tajribasiga e'tibor bering\", "
       "\"kod bloklari Python da bo'lsin\"</i>",
       "📝 Есть ли дополнительные требования?\n\n<i>Например: «добавьте больше таблиц», «акцент на опыте Узбекистана», «код на Python»</i>",
       "📝 Any additional requirements?\n\n<i>E.g.: \"add more tables\", \"focus on Uzbekistan's experience\", \"code blocks in Python\"</i>"),
    _d("Qo'shimcha talablar", "Доп. требования", "Extra requirements"), optional=True, hi=1000,
)
CASE_DATA = Step(
    "case_data",
    _d("📊 <b>Amaliy qism uchun HAQIQIY korxona ma'lumoti</b>\n\nKorxona nomi va yillar bo'yicha raqamlarni yuboring. Masalan:\n"
       "<i>Korxona: «Toshkent Tekstil» MChJ\n2022: tushum 120 mln, debitorlik 18 mln, kreditorlik 14 mln\n2023: tushum 150 mln, debitorlik 27 mln, "
       "kreditorlik 16 mln</i>\n\nAmaliy bobdagi barcha raqamlar FAQAT shu ma'lumotdan (va undan hisoblangan ko'rsatkichlardan) olinadi — hech narsa "
       "to'qilmaydi. Yubormasangiz, amaliy qism ochiq <b>«shartli misol»</b> sifatida yoziladi.",
       "📊 <b>РЕАЛЬНЫЕ данные предприятия для практической части</b>\n\nПришлите название предприятия и цифры по годам. Например:\n"
       "<i>Компания: ООО «Ташкент Текстиль»\n2022: выручка 120 млн, дебиторская 18 млн, кредиторская 14 млн\n2023: выручка 150 млн, "
       "дебиторская 27 млн, кредиторская 16 млн</i>\n\nВсе цифры практической главы берутся ТОЛЬКО из этих данных (и показателей, рассчитанных "
       "по ним) — ничего не выдумывается. Если не пришлёте, практическая часть будет написана как открыто <b>«условный пример»</b>.",
       "📊 <b>REAL company data for the practical part</b>\n\nSend the company name and figures by year. For example:\n"
       "<i>Company: Tashkent Textile LLC\n2022: revenue 120m, receivables 18m, payables 14m\n2023: revenue 150m, receivables 27m, payables 16m</i>\n\n"
       "Every figure in the practical chapter comes ONLY from this data (and ratios computed from it) — nothing is invented. If you skip it, the "
       "practical part is written as an openly <b>\"conditional example\"</b>."),
    _d("Korxona ma'lumoti", "Данные предприятия", "Company data"), optional=True, hi=4000, when="case",
)
YES_NO = (("yes", _d("✅ Ha", "✅ Да", "✅ Yes")), ("no", _d("❌ Yo'q", "❌ Нет", "❌ No")))
HAS_DIAGRAMS = Step(
    "has_diagrams",
    _d("📊 Kurs ishida grafik va diagrammalar bo'lsinmi?\n\n<i>Ha — jadvallar, bar diagrammalar, grafiklar qo'shiladi\nYo'q — faqat matn</i>",
       "📊 Включить графики и диаграммы в курсовую?\n\n<i>Да — таблицы, bar-диаграммы, графики\nНет — только текст</i>",
       "📊 Include charts and diagrams in the coursework?\n\n<i>Yes — tables, bar charts, graphs\nNo — text only</i>"),
    _d("Grafik va diagrammalar", "Графики и диаграммы", "Charts and diagrams"), kind="choice", choices=YES_NO,
)
HAS_IMAGES = Step(
    "has_images",
    _d("🖼 Rasm (sxema) joylashtirilsinmi?\n\n<i>Ha — jarayon sxemalari va tuzilma rasmlari izoh va tahlil bilan qo'shiladi\nYo'q — rasmsiz</i>",
       "🖼 Вставлять рисунки (схемы)?\n\n<i>Да — схемы процессов и структур с подписью и анализом\nНет — без рисунков</i>",
       "🖼 Include figures (schemes)?\n\n<i>Yes — process and structure diagrams with captions and analysis\nNo — without figures</i>"),
    _d("Rasmlar (sxema)", "Рисунки (схемы)", "Figures"), kind="choice", choices=YES_NO,
)
HAS_FOOTNOTES = Step(
    "has_footnotes",
    _d("📎 Snoskalar (izohlar) kerakmi?\n\n<i>Ha — ilmiy snoskalar qo'shiladi\nYo'q — faqat matn</i>",
       "📎 Нужны ли сноски (ссылки)?\n\n<i>Да — научные сноски\nНет — только текст</i>",
       "📎 Should footnotes be included?\n\n<i>Yes — academic footnotes\nNo — text only</i>"),
    _d("Snoskalar", "Сноски", "Footnotes"), kind="choice", choices=YES_NO,
)

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


# ── maqola: uch uslub (universitet/IMRAD/OAK) — hamkor API bilan bir xil dvigatel ────────────
STYLE_STEP = Step(
    "style",
    _d("📰 Qaysi uslubda yozilsin?", "📰 В каком стиле написать?", "📰 Which style should it be written in?"),
    _d("Uslub", "Стиль", "Style"), kind="choice",
    choices=(
        ("universitet", _d("🎓 Universitet (oddiy ilmiy maqola)", "🎓 Университетский (обычная научная статья)", "🎓 University (plain academic article)")),
        ("imrad", _d("🧪 IMRAD (sarlavhali, [1] havolali)", "🧪 IMRAD (с подзаголовками, ссылки [1])", "🧪 IMRAD (headed, [1]-style citations)")),
        ("oak", _d("🏛 OAK (jurnal namunasi)", "🏛 ВАК (образец журнала)", "🏛 HAC (journal-style)")),
    ),
)
MAQOLA_PAGES_UNI = Step(
    "pages", _d("📄 Necha bet bo'lsin?", "📄 Сколько страниц?", "📄 How many pages?"),
    _d("Hajm", "Объём", "Length"), kind="choice", when="style_uni", numeric=True,
    choices=tuple((str(v), _d(f"{v} bet", f"{v} стр.", f"{v} pages")) for v in (5, 7)),
)
MAQOLA_PAGES_ADV = Step(
    "pages", _d("📄 Necha bet bo'lsin?", "📄 Сколько страниц?", "📄 How many pages?"),
    _d("Hajm", "Объём", "Length"), kind="choice", when="style_adv", numeric=True,
    choices=tuple((str(v), _d(f"{v} bet", f"{v} стр.", f"{v} pages")) for v in (7, 10)),
)
# OAK ixtisosliklari — asosiy botdagi `article/oak/fields.py` bilan bir xil ro'yxat (id, nomi)
ARTICLE_FIELDS = (
    ("ped", _d("Pedagogika", "Педагогика", "Pedagogy")),
    ("psy", _d("Psixologiya", "Психология", "Psychology")),
    ("eco", _d("Iqtisodiyot", "Экономика", "Economics")),
    ("phil_lang", _d("Filologiya (tilshunoslik)", "Филология (языкознание)", "Linguistics")),
    ("phil_lit", _d("Filologiya (adabiyotshunoslik)", "Филология (литературоведение)", "Literary studies")),
    ("hist", _d("Tarix", "История", "History")),
    ("philos", _d("Falsafa", "Философия", "Philosophy")),
    ("law", _d("Yuridik fanlar", "Юридические науки", "Law")),
    ("soc", _d("Sotsiologiya", "Социология", "Sociology")),
    ("pol", _d("Siyosiy fanlar", "Политические науки", "Political science")),
    ("tech", _d("Texnika fanlari", "Технические науки", "Engineering")),
    ("it", _d("Axborot texnologiyalari", "Информационные технологии", "Information technology")),
    ("math", _d("Fizika-matematika", "Физико-математические науки", "Physics and mathematics")),
    ("chem", _d("Kimyo", "Химия", "Chemistry")),
    ("bio", _d("Biologiya", "Биология", "Biology")),
    ("med", _d("Tibbiyot", "Медицина", "Medicine")),
    ("agro", _d("Qishloq xo'jaligi", "Сельское хозяйство", "Agriculture")),
    ("geo", _d("Geografiya", "География", "Geography")),
    ("art", _d("San'atshunoslik", "Искусствоведение", "Art studies")),
    ("sport", _d("Jismoniy tarbiya va sport", "Физическая культура и спорт", "Physical education")),
)
FIELD_STEP = Step(
    "field", _d("🔬 Maqola qaysi sohaga tegishli?", "🔬 К какой области относится статья?", "🔬 Which field does the article belong to?"),
    _d("Soha", "Область", "Field"), kind="choice", when="style_adv", choices=ARTICLE_FIELDS,
)
USER_DATA_STEP = Step(
    "user_data",
    _d("📊 <b>O'z raqam/faktlaringiz</b> bormi (statistika, tadqiqot natijasi)?\n\nBo'lsa yuboring — matn shularga tayanadi, to'qima raqam "
       "ishlatilmaydi. Bo'lmasa — <b>⏭ O'tkazib yuborish</b>.",
       "📊 Есть ли у вас <b>свои цифры/факты</b> (статистика, результаты исследования)?\n\nЕсли есть — пришлите, текст будет опираться на них, "
       "а не на выдуманные цифры. Если нет — <b>⏭ Пропустить</b>.",
       "📊 Do you have your <b>own data/facts</b> (statistics, research results)?\n\nIf so, send them — the text will rely on them instead of "
       "invented numbers. If not — <b>⏭ Skip</b>."),
    _d("Muallifning ma'lumoti", "Данные автора", "Author's data"), optional=True, hi=4000, when="style_adv",
)
MAQOLA_NOTES = Step(
    "notes",
    _d("📝 Qo'shimcha talablaringiz bormi? (ixtiyoriy)", "📝 Есть ли дополнительные требования? (необязательно)",
       "📝 Any additional requirements? (optional)"),
    _d("Qo'shimcha talablar", "Доп. требования", "Extra requirements"), optional=True, hi=1000,
)
MAQOLA_PRICE = 12_000


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
        (KURS_LANG_STEP, PROFILE_STEP, FULL_NAME, UNIVERSITY, FACULTY, KAFEDRA, DIRECTION, GROUP, SUPERVISOR, CITY,
         SUBJECT_KURS, TOPIC_KURS, PLAN_MODE, PLAN_CFG, PLAN_PREVIEW, PLAN_TEXT, EXTRA, CASE_DATA,
         HAS_DIAGRAMS, HAS_IMAGES, HAS_FOOTNOTES, _kurs_pages()),
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
    "maqola": Service(
        "maqola", "📰", _d("Ilmiy maqola", "Научная статья", "Academic article"),
        _d("DOCX", "DOCX", "DOCX"),
        _d("5–10 daqiqa", "5–10 минут", "5–10 minutes"),
        (LANG_STEP, PROFILE_STEP, FULL_NAME, UNIVERSITY, DIRECTION, SUPERVISOR, TOPIC, STYLE_STEP,
         MAQOLA_PAGES_UNI, MAQOLA_PAGES_ADV, FIELD_STEP, USER_DATA_STEP, MAQOLA_NOTES),
        MAQOLA_PRICE, profile=True,
    ),
}

ORDER = ("taqdimot", "kurs_ishi", "mustaqil_ish", "referat", "test", "krossvord", "maqola")
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
        if not is_active(step, answers):
            continue                                   # shartli qadam so'ralmagan — eski javob ham ketmaydi
        value = answers.get(step.key)
        if value in (None, ""):
            continue
        (student if step.target == "student" else params)[step.key] = value
    if student:
        params["student"] = student
    if service.slug == "kurs_ishi":
        for key in ("plan_mode", "plan_cfg"):
            params.pop(key, None)
        if answers.get("plan_mode") == "auto" and answers.get("plan_cfg"):
            bobs, _, bolim = str(answers["plan_cfg"]).partition("_")
            params["bob_count"], params["bolim_per_bob"] = int(bobs), int(bolim)
        for key in ("has_diagrams", "has_images", "has_footnotes"):
            if key in answers:
                params[key] = answers[key] == "yes"        # tugmadagi yes/no → mantiqiy qiymat
    if service.slug == "krossvord" and params.get("subject"):
        # Hamkor API'da krossvord uchun `subject` yo'q: fan mavzuga qo'shiladi
        params["topic"] = f"{params['topic']} ({params['subject']})"
    if service.slug == "krossvord":
        params.pop("subject", None)
    return params
