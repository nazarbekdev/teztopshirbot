# TezTopshirBot (@teztopshirbot)

OsonTopshir **hamkor API** ustidagi yupqa Telegram frontend: hujjatlarni o'zi yaratmaydi,
buyurtmani `api.osontopshir.uz/partner/v1` ga yuboradi. Baza alohida (SQLite), mijozlar va
balanslar OsonTopshir botidan butunlay ajratilgan.

```
Mijoz → bot (savollar, balans) → buyurtma navbati → hamkor API → fayl → mijozga
```

## Ishga tushirish

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env     # BOT_TOKEN, PARTNER_API_KEY, ADMIN_IDS ni to'ldiring
.venv/bin/python main.py
.venv/bin/python -m pytest
```

**Avval `ot_test_...` kalit bilan sinang:** kredit yechilmaydi, hujjat o'rniga qisqa namuna
fayl keladi. `ot_live_...` ga o'tishdan oldin hamkor kabinetida kredit sotib oling
(https://developers.osontopshir.uz/dashboard) — kreditlar xizmat bo'yicha alohida.

## Narx

Mijoz narxi `app/catalog.py` da. U hamkor narxidan kamida 20% yuqori bo'lishi shart
(`tests/test_catalog.py`). Hamkor narxlari: kurs ishi 25 000, taqdimot 3 000, mustaqil ish /
referat 4 000, test 1 500, krossvord 1 000 (aniq qiymat `/admin` da, `GET /credits` dan).

## To'lov

- **Karta:** mijoz chek yuboradi → adminlarga tugmali xabar → tasdiqlansa balans to'ladi.
- **Click:** `.env` da `CLICK_*` va `PUBLIC_URL`. Click kabinetida Prepare/Complete manzillari:
  `{PUBLIC_URL}/click/prepare`, `{PUBLIC_URL}/click/complete`.

## Ishonchlilik qoidalari

- Pul buyurtma yaratilganda yechiladi, xato/bekor bo'lsa **bir marta** qaytadi (`refunded` bayrog'i).
- Hamkorga yuborish `Idempotency-Key: tez-<id>` bilan: qayta urinishda kredit ikki marta yechilmaydi.
- Hamkorda bir vaqtda 10 tagacha faol buyurtma mumkin — biz `MAX_ACTIVE_ORDERS` (8) dan oshirmaymiz.
- Hamkor krediti tugasa: buyurtma bajarilmaydi, mijozga pul qaytadi, adminga ogohlantirish ketadi.
- Fayl yetkazilmasa yo'qolmaydi — keyingi aylanishda qayta uriniladi (hamkorda 7 kun saqlanadi).
- FSM holati xotirada (MemoryStorage): bot qayta ishga tushsa tugallanmagan savol-javoblar uziladi,
  lekin berilgan buyurtmalar va balans bazada.
