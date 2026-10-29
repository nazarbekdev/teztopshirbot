from app.catalog import ORDER, SERVICES, build_params, money, progress_text

# Hamkor (OsonTopshir) narxlari — `GET /credits` dagi standart qiymatlar
PARTNER_COST = {"kurs_ishi": 25_000, "taqdimot": 3_000, "taqdimot_pro": 8_000, "mustaqil_ish": 4_000,
                "referat": 4_000, "test": 1_500, "krossvord": 1_000, "maqola": 8_000}
# Hamkor narxidan kamida 10% yuqori. Egasi (ikkala bot ham uniki) 2026-10-18 da mustaqil ish/referatni
# 4 500 ga (hamkor 4 000 → marja 12,5%) tushirdi: haqiqiy LLM tannarxi hamkor narxidan ancha past.
MIN_MARGIN = 0.10


def all_prices(service):
    return list(service.price.values()) if service.is_tiered else [service.price]


def test_har_xizmat_hamkor_narxidan_qimmat():
    for slug in ORDER:
        for price in all_prices(SERVICES[slug]):
            assert price >= PARTNER_COST[slug] * (1 + MIN_MARGIN), f"{slug}: {price}"


def test_kurs_ishi_pogonalari():
    s = SERVICES["kurs_ishi"]
    assert s.price == {"20-30": 55_000, "30-40": 65_000, "40-50": 75_000}
    assert [s.price_for({"pages": p}) for p in ("20-30", "30-40", "40-50")] == [55_000, 65_000, 75_000]
    assert s.min_price == 55_000 and s.is_tiered


def test_barcha_xizmatlar_hamkor_royxatida():
    assert set(ORDER) == set(PARTNER_COST) == set(SERVICES)


def test_tanlov_qiymatlari_hamkor_qoidalariga_mos():
    allowed = {
        ("taqdimot", "slides"): {10, 15, 20, 25, 30},
        ("mustaqil_ish", "pages"): {10, 15, 20},
        ("referat", "pages"): {10, 15, 20},
        ("test", "questions"): {10, 15, 20, 25, 30},
        ("krossvord", "word_count"): {10, 15, 20, 25, 30},
    }
    for (slug, key), values in allowed.items():
        step = next(s for s in SERVICES[slug].steps if s.key == key)
        assert {int(v) for v, _ in step.choices} == values
    pages = next(s for s in SERVICES["kurs_ishi"].steps if s.key == "pages")
    assert {v for v, _ in pages.choices} == {"20-30", "30-40", "40-50"}


def test_savollar_tartibi_asosiy_bot_bilan_bir_xil():
    """Hujjat tili — har doim birinchi (maqolada uslub birinchi, chunki uslub savol shaklini belgilaydi)."""
    for slug in ORDER:
        if slug == "maqola":
            assert SERVICES[slug].steps[0].key == "style"
        else:
            assert SERVICES[slug].steps[0].key == "language"
    keys = lambda slug: [s.key for s in SERVICES[slug].steps if s.kind != "profile" and s.target == "params"]
    assert keys("taqdimot") == ["language", "subject", "topic", "notes", "template", "slides", "presenter", "supervisor"]
    assert keys("test") == ["language", "subject", "topic", "questions"]
    assert keys("krossvord") == ["language", "subject", "topic", "word_count"]
    assert keys("mustaqil_ish") == ["language", "subject", "topic", "pages"]
    assert keys("kurs_ishi") == ["language", "subject", "topic", "plan_mode", "plan_cfg", "plan", "plan", "extra_instructions",
                                 "case_data", "has_diagrams", "has_images", "has_footnotes", "pages"]
    assert keys("maqola") == ["style", "language", "topic", "pages", "pages", "field", "user_data", "notes"]


def test_student_alohida_obyekt_va_bosh_maydon_tushadi():
    p = build_params(SERVICES["referat"], {"topic": "Mavzu uzun", "subject": "Fan", "pages": 10,
                                           "language": "uz", "full_name": "Ali", "university": "", "_use_profile": True})
    assert p["student"] == {"full_name": "Ali"}
    assert "full_name" not in p and "_use_profile" not in p


def test_krossvord_fani_mavzuga_qoshiladi():
    p = build_params(SERVICES["krossvord"], {"language": "uz", "subject": "Geografiya", "topic": "Daryolar", "word_count": 10})
    assert p == {"language": "uz", "topic": "Daryolar (Geografiya)", "word_count": 10}


def test_pul_formati_tilga_qarab():
    assert money(55_000, "uz") == "55 000 so'm"
    assert money(55_000, "ru") == "55 000 сум"
    assert money(55_000, "en") == "55 000 UZS"


def test_boshlangich_narxlar():
    prices = {slug: SERVICES[slug].min_price for slug in ORDER}
    assert prices == {"taqdimot": 4_500, "taqdimot_pro": 9_000, "kurs_ishi": 55_000, "mustaqil_ish": 4_500,
                      "referat": 4_500, "test": 2_500, "krossvord": 1_500, "maqola": 9_000}


def test_kichik_xizmatlarda_har_pogona_1000_qoshiladi():
    """Asosiy bot uslubi: hajm bir pog'ona oshsa +1 000 so'm; boshlang'ich narx — eng kichik hajm."""
    expected = {
        "taqdimot": {10: 4_500, 15: 5_500, 20: 6_500, 25: 7_500, 30: 8_500},
        "mustaqil_ish": {10: 4_500, 15: 5_500, 20: 6_500},
        "referat": {10: 4_500, 15: 5_500, 20: 6_500},
        "test": {10: 2_500, 15: 3_500, 20: 4_500, 25: 5_500, 30: 6_500},
        "krossvord": {10: 1_500, 15: 2_500, 20: 3_500, 25: 4_500, 30: 5_500},
    }
    for slug, table in expected.items():
        s = SERVICES[slug]
        assert s.price == table, slug
        for size, price in table.items():
            assert s.price_for({s.price_key: size}) == price


def test_tanlov_tugmalarida_narx_korinadi_va_qiymat_son():
    step = next(st for st in SERVICES["taqdimot"].steps if st.key == "slides")
    labels = {v: label for v, label in step.choices}
    assert labels["15"]["uz"] == "15 slayd — 5 500 so'm"
    assert labels["15"]["ru"] == "15 слайдов — 5 500 сум"
    assert labels["30"]["en"] == "30 slides — 8 500 UZS"
    assert step.numeric


def test_narx_kaliti_har_tanlov_qiymatiga_mos():
    for slug in ORDER:
        s = SERVICES[slug]
        if not s.is_tiered:
            continue                            # maqola narxi hajmga qaramaydi — alohida tekshiriladi
        step = next(st for st in s.steps if st.key == s.price_key)
        values = {int(v) if step.numeric else v for v, _ in step.choices}
        assert values == set(s.price), slug


def test_maqola_uslubga_qarab_hajm_va_soha():
    s = SERVICES["maqola"]
    assert s.is_tiered and s.price == {"universitet": 9_000, "imrad": 12_000, "oak": 14_000}
    assert [s.price_for({"style": v}) for v in ("universitet", "imrad", "oak")] == [9_000, 12_000, 14_000]
    pages_steps = [st for st in s.steps if st.key == "pages"]
    assert len(pages_steps) == 2
    uni = next(st for st in pages_steps if st.when == "style_uni")
    adv = next(st for st in pages_steps if st.when == "style_adv")
    assert {v for v, _ in uni.choices} == {"5", "7"}
    assert {v for v, _ in adv.choices} == {"7", "10"}
    field = next(st for st in s.steps if st.key == "field")
    assert field.when == "style_adv" and len(field.choices) == 20
    assert {v for v, _ in field.choices} == {
        "ped", "psy", "eco", "phil_lang", "phil_lit", "hist", "philos", "law", "soc", "pol",
        "tech", "it", "math", "chem", "bio", "med", "agro", "geo", "art", "sport",
    }


def test_maqola_universitet_uslubida_soha_va_malumot_sorlmaydi():
    p = build_params(SERVICES["maqola"], {"language": "uz", "topic": "Mavzu uzun yetarlicha",
                                          "style": "universitet", "pages": "5", "field": "it",
                                          "user_data": "bu kerak emas", "notes": ""})
    assert p == {"language": "uz", "topic": "Mavzu uzun yetarlicha", "style": "universitet", "pages": "5"}


def test_progress_text_navbatda_va_bosqichma_bosqich_ilgarilaydi():
    import time

    queued = {"service": "taqdimot_pro", "status": "queued", "created_at": int(time.time())}
    text = progress_text(queued, "uz")
    assert "Navbatda" in text and "░░░░░" in text          # 5 bosqich, hali boshlanmagan

    processing = {"service": "taqdimot_pro", "status": "processing", "created_at": int(time.time())}
    text2 = progress_text(processing, "uz")
    assert "▓" in text2 and "Navbatda" not in text2

    far_in_future = {"service": "taqdimot_pro", "status": "processing", "created_at": int(time.time()) - 10_000}
    text3 = progress_text(far_in_future, "ru")
    assert "▓▓▓▓▓" in text3                                # vaqt o'tib ketgan — oxirgi bosqichda to'xtaydi


def test_progress_text_notanish_xizmatda_standart_bosqichlar():
    order = {"service": "noma'lum_xizmat", "status": "processing", "created_at": int(__import__("time").time())}
    text = progress_text(order, "uz")
    assert "░" in text or "▓" in text


def test_maqola_imrad_uslubida_soha_va_malumot_yuboriladi():
    p = build_params(SERVICES["maqola"], {"language": "uz", "topic": "Mavzu uzun yetarlicha",
                                          "style": "imrad", "pages": "7", "field": "it",
                                          "user_data": "5 ta respondent", "notes": "jadval kerak"})
    assert p == {"language": "uz", "topic": "Mavzu uzun yetarlicha", "style": "imrad", "pages": "7",
                "field": "it", "user_data": "5 ta respondent", "notes": "jadval kerak"}
