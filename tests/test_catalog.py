from app.catalog import ORDER, SERVICES, build_params

# Hamkor (OsonTopshir) narxlari — `GET /credits` dagi standart qiymatlar
PARTNER_COST = {"kurs_ishi": 25_000, "taqdimot": 3_000, "mustaqil_ish": 4_000,
                "referat": 4_000, "test": 1_500, "krossvord": 1_000}
MIN_MARGIN = 0.20  # hamkor narxidan kamida 20% yuqori (to'lov komissiyasi va xato buyurtmalarni qoplash uchun)


def test_har_xizmat_hamkor_narxidan_qimmat():
    for slug in ORDER:
        price, cost = SERVICES[slug].price, PARTNER_COST[slug]
        assert price >= cost * (1 + MIN_MARGIN), f"{slug}: {price} ≤ hamkor narxi {cost} + 20%"


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


def test_kurs_ishi_sahifasi_qat_iy():
    p = build_params(SERVICES["kurs_ishi"], {"topic": "Mavzu uzun", "subject": "Fan", "language": "uz"})
    assert p["pages"] == "20-30"


def test_student_alohida_obyekt_va_bosh_maydon_tushadi():
    p = build_params(SERVICES["referat"], {"topic": "Mavzu uzun", "subject": "Fan", "pages": 10,
                                           "language": "uz", "full_name": "Ali", "university": ""})
    assert p["student"] == {"full_name": "Ali"}
    assert "full_name" not in p


def test_yolg_iz_maydon_yuborilmaydi():
    p = build_params(SERVICES["taqdimot"], {"topic": "Mavzu uzun", "slides": 15, "language": "uz", "presenter": ""})
    assert "presenter" not in p
