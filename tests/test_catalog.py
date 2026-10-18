from app.catalog import ORDER, SERVICES, build_params, money

# Hamkor (OsonTopshir) narxlari — `GET /credits` dagi standart qiymatlar
PARTNER_COST = {"kurs_ishi": 25_000, "taqdimot": 3_000, "mustaqil_ish": 4_000,
                "referat": 4_000, "test": 1_500, "krossvord": 1_000}
MIN_MARGIN = 0.20  # hamkor narxidan kamida 20% yuqori (to'lov komissiyasi va xato buyurtmalarni qoplash uchun)


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
    """Hujjat tili — har doim birinchi; keyin fan, mavzu, hajm."""
    for slug in ORDER:
        assert SERVICES[slug].steps[0].key == "language"
    keys = lambda slug: [s.key for s in SERVICES[slug].steps if s.kind != "profile" and s.target == "params"]
    assert keys("taqdimot") == ["language", "subject", "topic", "slides", "presenter", "supervisor"]
    assert keys("test") == ["language", "subject", "topic", "questions"]
    assert keys("krossvord") == ["language", "subject", "topic", "word_count"]
    assert keys("mustaqil_ish") == ["language", "subject", "topic", "pages"]
    assert keys("kurs_ishi") == ["language", "subject", "topic", "pages"]


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
