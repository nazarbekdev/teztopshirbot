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

Mijoz narxi `app/catalog.py` da. Kichik xizmatlarda (taqdimot, mustaqil ish, referat, test, krossvord) narx asosiy bot uslubida hajmga qarab: boshlang'ich narx eng kichik hajmga, har pog'ona **+1 000 so'm**; kurs ishi 55 / 65 / 75 ming. U hamkor narxidan kamida 10% yuqori bo'lishi shart
(`tests/test_catalog.py`). Hamkor narxlari: kurs ishi 25 000, taqdimot 3 000, mustaqil ish /
referat 4 000, test 1 500, krossvord 1 000 (aniq qiymat `/admin` da, `GET /credits` dan).

## To'lov

- **Karta:** mijoz chek yuboradi → adminlarga tugmali xabar → tasdiqlansa balans to'ladi.
- **Click:** `.env` da `CLICK_*` va `PUBLIC_URL`. Click kabinetida Prepare/Complete manzillari:
  `{PUBLIC_URL}/click/prepare`, `{PUBLIC_URL}/click/complete`.

## Til, rozilik va holat

- Birinchi `/start` da til tanlanadi (uz/ru/en), keyin maxfiylik shartlariga **rozilik** (`/privacy` da to'liq matn,
  versiya `ui.CONSENT_VERSION`). Ikkalasi bo'lmaguncha boshqa hech narsa ishlamaydi (`app/middleware.py`).
  Matnni o'zgartirsangiz versiyani oshiring — hamma qayta rozilik beradi.
- Matnlar `app/i18n.py` da; `tests/test_i18n.py` har kalit uch tilda va `{}` joylari mos ekanini tekshiradi.
- FSM holati **SQLite'da** (`app/fsm_storage.py`): bot qayta ishga tushsa ham foydalanuvchi savol-javobi uzilmaydi.
- Kurs ishi / mustaqil ish / referatda titul ma'lumotlari saqlanadi va keyingi buyurtmada taklif qilinadi.

## Kanalga a'zolik va promokod

- `REQUIRED_CHANNEL=@kanal`: `/start` va barcha amallar kanal a'zoligini talab qiladi (adminlar ozod). **Bot kanalda admin bo'lishi shart.**
  Tekshiruv xato bersa (bot admin emas va h.k.) foydalanuvchi bloklanmaydi, adminga soatiga bir ogohlantirish ketadi (`app/subscription.py`).
- **Promokod:** kanalda e'lon qilinadi, botda «🎁 Promokod» (yoki `/promo`) orqali kiritiladi → **bitta bepul buyurtma** huquqi (kupon).
  Xizmatlar ro'yxati, eng ko'p ishlatish soni va muddat panelda (`/promos`) belgilanadi. Bir foydalanuvchi bir kodni bir marta
  kiritadi; bir vaqtda bitta faol kupon. Bepul buyurtma xato bilan tugasa, pul emas, **kupon qaytadi**. Kurs ishi aksiyaga kirmaydi.

## Admin: chek tasdiqlash

Karta to'lovi kartasida uchta tugma: **Tasdiqlash**, **Rad etish**, **Summani tahrirlash** (mijoz noto'g'ri
summa yozgan bo'lsa admin chekdagi haqiqiy summani kiritadi; balansga o'sha summa tushadi, mijozga farq
tushuntiriladi, asl summa `payments.original_amount` da qoladi).

## Web admin panel

Bot bilan bir jarayonda (aiohttp), `PANEL_HOST:PANEL_PORT` (standart `127.0.0.1:8082`) da ishlaydi; internetga
nginx + HTTPS orqali chiqariladi (`PANEL_URL=https://...` bo'lsa cookie `Secure` bo'ladi). `ADMIN_IDS` bo'sh bo'lsa panel yoqilmaydi.

- **Kirish parolsiz — Telegram orqali:** `/login` → «Telegram'da tasdiqlash» → botda IP va brauzer ko'rsatiladi → **Ruxsat**.
  Sessiyani faqat so'rovni boshlagan brauzer oladi (cookie'dagi sir), token bazada xesh, 12 soat, POST'lar CSRF bilan,
  kirish urinishlari cheklangan (`app/panel/auth.py`).
- **Sahifalar:** bosh sahifa (statistika, hamkor kreditlari va marja), buyurtmalar (filtr, tafsilot, pulni qaytarish),
  foydalanuvchilar (qidiruv, balansni qo'lda o'zgartirish — sabab majburiy), to'lovlar (chek rasmi, tasdiqlash / rad /
  summani tahrirlash), audit jurnali.
- Pul amallari botdagi bilan **bir xil yo'l**: `app/payments.py` va `Store` (qayta bosishdan himoyalangan), har biri `admin_audit` ga yoziladi.

## Ishonchlilik qoidalari

- Pul buyurtma yaratilganda yechiladi, xato/bekor bo'lsa **bir marta** qaytadi (`refunded` bayrog'i).
- Hamkorga yuborish `Idempotency-Key: tez-<id>` bilan: qayta urinishda kredit ikki marta yechilmaydi.
- Hamkor hisobida `max_active_orders` = 80; biz `MAX_ACTIVE_ORDERS` (80) dan oshirmaymiz, bitta foydalanuvchi `PER_USER_ACTIVE` (5) tagacha.
- Holat bitta `GET /orders` so'rovi bilan kuzatiladi (80 ta faol buyurtmani alohida so'rash daqiqasiga ~500 so'rov bo'lardi).
- Hamkor krediti tugasa: buyurtma bajarilmaydi, mijozga pul qaytadi, adminga ogohlantirish ketadi.
- Fayl yetkazilmasa yo'qolmaydi — keyingi aylanishda qayta uriniladi (hamkorda 7 kun saqlanadi).
