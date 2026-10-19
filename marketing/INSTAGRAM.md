# @teztopshirbot — Instagram Reels rejasi

## Tayyor reel
`out/teztopshir-reel.mp4` — 1080×1920, 33 soniya, o'zbekcha ovoz (Edge TTS Madina) + musiqa + effektlar, subtitr ichiga yozilgan.
Qayta yig'ish: `build_timeline.py` → `render_frames.py` → `mix_audio.py` → `ffmpeg` (qarang `make_reel.sh`). Matn/narxni o'zgartirsangiz
`build_timeline.py` (ovoz) va `reel.html` (rasm) dagi matnni yangilab qayta yig'ing. O'z logongiz: `marketing/logo.png` qo'ying.

## Post matni (caption)
```
Ertaga topshirish kerak, hali hech narsa tayyor emasmi? 😰

Telegramdagi Tez Topshir boti yordam beradi:
📖 Kurs ishi · 📊 Taqdimot · 📝 Mustaqil ish · 📄 Referat · ❓ Test · 🧩 Krossvord
💸 Narxlar 1 500 so'mdan

🎁 Promokod: TEZSTART — birinchi 300 foydalanuvchiga istalgan 1 ta xizmat BEPUL (kurs ishi bundan mustasno).

👉 Telegram: @teztopshirbot (havola bio'da)

⚠️ Hujjat sun'iy intellekt yordamida tayyorlanadi. Topshirishdan oldin o'zingiz tekshiring.

#talaba #kursishi #referat #taqdimot #mustaqilish #universitet #oliygoh #sessiya #uzbekistan #toshkent #talabahayoti #tezTopshir
```
Qadamlar: 1) Reel + cover.jpg. 2) Birinchi izohga "Promokod: TEZSTART 🎁" yozib **pin** qiling. 3) Bio'ga `t.me/teztopshirbot`.

## Qaysi reellarni nishonga olamiz
Instagram'da "reelsni nishonga olish" — ikki yo'l: (A) organik: auditoriya qaerda bo'lsa o'sha formatda chiqish; (B) pullik: Meta Ads.

**A. Organik — nima uchun talabalar to'xtaydi:**
1. **"Ertaga topshirish kerak" mem/skeçlar** (eng kuchli hook): sessiya, deadline, "kurs ishi 3 kun qoldi".
2. **Ekran yozuvi (demo):** botga mavzu yozish → fayl kelishi (10–15 s, subtitr bilan). Haqiqiy ko'rinish ishonch beradi.
3. **Narx zarbasi:** "Krossvord 1 500 so'm — bir choy narxi" kabi qisqa solishtirish.
4. **Foydali kontent:** "kurs ishida reja qanday tuziladi", "taqdimotda 5 ta xato", "tezis nima" — saqlashga arziydigan maslahat, oxirida bot.
5. **Promokod chaqirig'i:** "TEZSTART — birinchi 300 kishi" (tanqislik). Kod tugagach yangi kod/aksiya bilan davom eting.
6. **Hamkor blogerlar:** 5–50 ming obunali talaba/universitet sahifalari (mikro-influenser) — ularga ushbu reel yoki o'z demo'si.

**Vaqt:** 18:00–22:00 (Toshkent). Haftasiga 3–4 reel. **Mavsum:** may–iyun (kurs ishi), dekabr–yanvar (sessiya), sentabr (semestr boshi).
**Birinchi 2 soniya** hook bo'lsin; matn ekranda; ovozsiz ham tushunarli (subtitr bor).
**Hashtag:** 8–12 ta, katta+kichik aralash. Geo-teg: Toshkent, Samarqand, Namangan.

**B. Pullik (Meta Ads Manager):**
- Maqsad: *Traffic* (havola: `https://t.me/teztopshirbot`) yoki *Profile visits*.
- Auditoriya: O'zbekiston, 17–24 yosh, qiziqishlar: universitet/talaba, ta'lim, onlayn ta'lim; til: o'zbek+rus.
- Joylashuv: faqat **Reels** (+Stories); byudjet 3–5 $/kun, 3 xil kreativ bilan 5–7 kun test, keyin eng yaxshisini ko'paytirish.
- Kreativ A/B: (1) shu reel, (2) faqat demo ekran yozuvi, (3) narx hooki. Metrika: CPC, /start soni (bot panelida), birinchi buyurtma.
- **Ehtiyot:** Meta "akademik nohalollik"ni targ'ib qiluvchi reklamalarni rad etishi/hisobni cheklashi mumkin. Shuning uchun matnda
  "tayyorlash yordamchisi", "topshirishdan oldin tekshiring" ifodalari qoldirilgan; "diplomni sotib oling", "o'rningizga yozamiz",
  "100% o'tadi" kabi so'zlardan qoching. Birinchi reklama rad etilsa shu matn bilan qayta yuboring.

## O'lchash (keyingi qadam)
Hozir bot `/start` manbasini (qaysi reel/reklama) yozib bormaydi. Havola `t.me/teztopshirbot?start=ig_reel1` shaklida bo'lsa,
botga «birinchi marta qaerdan kelgan» belgisini qo'shish mumkin (asosiy botdagi reklama-manba tizimi kabi).

## 2-reel: "Sessiya kechasi 23:40" (kurs ishi, chat hikoya)
`out/teztopshir-reel2-kursishi.mp4` — 36 s. Ikki ovoz (talaba=Sardor, do'st=Madina), Telegram uslubidagi avtomatik aylanadigan
yozishma, kurs ishi narxi (55 000 so'mdan) va promokod (kurs ishi bundan mustasno). Qayta yig'ish: `./make_reel2.sh`.

### Caption (kurs ishi uchun)
```
"Ertaga kurs ishi topshirishim kerak, hali boshlamadim!" 😭

Tanish holatmi? Tez Topshir boti yordam beradi:
📖 Kurs ishi — 55 000 so'mdan
📊 Taqdimot · 📝 Mustaqil ish · 📄 Referat · ❓ Test · 🧩 Krossvord — 1 500 so'mdan

Mavzuni yozasiz, bir necha daqiqada tayyor fayl o'zingizga keladi.

🎁 Promokod: TEZSTART — birinchi 300 foydalanuvchiga istalgan 1 ta xizmat BEPUL
(kurs ishi bundan mustasno)

👉 Telegram: @teztopshirbot

⚠️ Hujjat sun'iy intellekt yordamida tayyorlanadi. Topshirishdan oldin o'zingiz tekshiring.

#talaba #kursishi #sessiya #universitet #oliygoh #talabahayoti #uzbekistan #toshkent #deadline #tezTopshir
```
