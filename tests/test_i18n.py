import re

from app.catalog import SERVICES
from app.i18n import LANGS, TEXTS


def placeholders(text: str) -> set[str]:
    return set(re.findall(r"\{(\w+)\}", text))


def test_har_kalit_uch_tilda_va_joylari_bir_xil():
    for key, entry in TEXTS.items():
        assert set(entry) == set(LANGS), f"{key}: tillar to'liq emas"
        base = placeholders(entry["uz"])
        for lang in LANGS:
            assert placeholders(entry[lang]) == base, f"{key}[{lang}]: {{}} joylari mos emas"
            assert entry[lang].strip(), f"{key}[{lang}] bo'sh"


def test_katalogdagi_matnlar_uch_tilda():
    for service in SERVICES.values():
        for field in (service.title, service.note, service.eta):
            assert set(field) == set(LANGS)
        for step in service.steps:
            if step.kind == "profile":
                continue
            assert set(step.p) == set(LANGS) and set(step.lbl) == set(LANGS), step.key
            for _, label in step.choices:
                assert isinstance(label, str) or set(label) == set(LANGS)


def test_holat_nomlari_barcha_statuslar_uchun():
    for status in ("queued", "submitted", "processing", "succeeded", "failed", "canceled"):
        assert f"st_{status}" in TEXTS


def test_maxfiylik_matni_haqiqatga_mos_iboralarni_saqlaydi():
    """Matnda bo'lmasligi kerak bo'lgan va'dalar (kafolat) yo'q, bo'lishi shart bo'lganlar bor."""
    for lang in LANGS:
        text = TEXTS["consent_full"][lang].lower()
        assert "7" in text                      # hamkorda fayl 7 kun saqlanadi
        assert "{contact}" in TEXTS["consent_full"][lang]
    uz = TEXTS["consent_full"]["uz"].lower()
    assert "kafolatlanmaydi" in uz
