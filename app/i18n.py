"""
Uch tilli matnlar (uz / ru / en). Foydalanuvchi tili `users.lang` da saqlanadi va
birinchi `/start` da bir marta so'raladi. Admin xabarlari faqat o'zbekcha.

Qoida: har kalit uchta tilda bo'lishi shart (`tests/test_i18n.py` tekshiradi) va
`{}` joylari uchala tilda bir xil bo'lishi kerak.
"""

LANGS = ("uz", "ru", "en")
DEFAULT = "uz"
LANG_NAMES = {"uz": "🇺🇿 O'zbekcha", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}

TEXTS: dict[str, dict[str, str]] = {
    # ── til va rozilik ───────────────────────────────────────────────────
    "lang_prompt": {
        "uz": "🌐 Tilni tanlang / Выберите язык / Choose language",
        "ru": "🌐 Tilni tanlang / Выберите язык / Choose language",
        "en": "🌐 Tilni tanlang / Выберите язык / Choose language",
    },
    "lang_changed": {
        "uz": "✅ Til o'zgartirildi.",
        "ru": "✅ Язык изменён.",
        "en": "✅ Language changed.",
    },
    "consent_intro": {
        "uz": ("🔒 <b>Maxfiylik va foydalanish shartlari</b>\n\n"
               "Botdan foydalanish uchun qisqa shartlar bilan tanishing:\n"
               "• Siz yozgan mavzu va ma'lumotlar hujjatni tayyorlash uchun ishlatiladi.\n"
               "• Hujjatni sun'iy intellekt tayyorlaydi — topshirishdan oldin o'zingiz tekshirasiz.\n"
               "\n"
               "To'liq matnni o'qib chiqing, so'ng rozilik bildiring."),
        "ru": ("🔒 <b>Конфиденциальность и условия использования</b>\n\n"
               "Перед использованием бота ознакомьтесь с краткими условиями:\n"
               "• Тема и данные, которые вы указываете, используются для подготовки документа.\n"
               "• Документ готовит искусственный интеллект — перед сдачей вы проверяете его сами.\n"
               "\n"
               "Прочитайте полный текст и подтвердите согласие."),
        "en": ("🔒 <b>Privacy & terms of use</b>\n\n"
               "Before using the bot, please read the short terms:\n"
               "• The topic and details you enter are used to prepare the document.\n"
               "• The document is prepared by artificial intelligence — you review it yourself before submitting.\n"
               "\n"
               "Read the full text, then confirm your consent."),
    },
    "btn_full": {"uz": "📄 To'liq matn", "ru": "📄 Полный текст", "en": "📄 Full text"},
    "btn_agree": {"uz": "✅ Roziman", "ru": "✅ Согласен", "en": "✅ I agree"},
    "consent_full": {
        "uz": ("📄 <b>Maxfiylik siyosati va foydalanish shartlari</b> (v{version})\n\n"
               "<b>1. Qanday ma'lumot saqlanadi</b>\n"
               "Telegram ID, ism, username, tanlagan til; siz kiritgan buyurtma ma'lumotlari (mavzu, fan, "
               "hujjat tili va ixtiyoriy ravishda ism, universitet, fakultet, guruh, rahbar kabi titul varag'i "
               "ma'lumotlari); balans va to'lov yozuvlari (summa, usul, karta to'lovida chek rasmi).\n\n"
               "<b>2. Nima uchun</b>\n"
               "Hujjatni tayyorlash va yetkazish, to'lovlarni hisobga olish, muammoni hal qilish va "
               "firibgarlikdan himoya qilish uchun.\n\n"
               "<b>3. Qayta ishlash va uchinchi tomonlar</b>\n"
               "• Hujjatni tayyorlash uchun siz kiritgan mavzu va ma'lumotlar sun'iy intellekt xizmatlari yordamida qayta ishlanadi.\n"
               "• Fayllar Telegram orqali yetkaziladi.\n"
               "• Click to'lovida karta ma'lumotlaringizni biz ko'rmaymiz — ular to'lov tizimida qoladi.\n"
               "• Ma'lumotlaringiz sotilmaydi va reklama uchun uchinchi shaxslarga berilmaydi.\n\n"
               "<b>4. Saqlash muddati</b>\n"
               "Buyurtma va to'lov yozuvlari hisob-kitob uchun saqlanadi. O'chirishni so'rasangiz, "
               "administrator ko'rib chiqadi; qonun yoki hisob talab qilgan yozuvlar saqlanib qolishi mumkin.\n\n"
               "<b>5. Hujjat va javobgarlik</b>\n"
               "Hujjat sun'iy intellekt yordamida tayyorlanadi va xato yoki noaniqlik bo'lishi mumkin. "
               "Uni topshirishdan oldin tekshirish, shuningdek ta'lim muassasangizning akademik halollik "
               "qoidalariga rioya qilish sizning mas'uliyatingizda. Natija (baho, originallik yoki plagiat "
               "tekshiruvi) ko'p omilga bog'liq va oldindan va'da qilinmaydi.\n\n"
               "<b>6. To'lov va qaytarish</b>\n"
               "To'lov balansga tushadi va buyurtma narxi undan yechiladi. Buyurtma xato bilan tugasa, "
               "summa balansingizga avtomatik qaytadi. Balansdagi mablag'ni naqd qaytarish administrator "
               "bilan kelishiladi.\n\n"
               "<b>7. Aloqa</b>\n"
               "Savol va so'rovlar uchun: {contact}.\n\n"
               "Roziman tugmasini bosish orqali shu shartlarni qabul qilasiz."),
        "ru": ("📄 <b>Политика конфиденциальности и условия использования</b> (v{version})\n\n"
               "<b>1. Какие данные хранятся</b>\n"
               "Telegram ID, имя, username, выбранный язык; данные заказа, которые вы вводите (тема, предмет, "
               "язык документа и, по желанию, имя, университет, факультет, группа, руководитель для титульного "
               "листа); записи о балансе и платежах (сумма, способ, фото чека при оплате картой).\n\n"
               "<b>2. Зачем</b>\n"
               "Чтобы подготовить и доставить документ, учитывать платежи, решать проблемы и защищать от мошенничества.\n\n"
               "<b>3. Обработка и третьи стороны</b>\n"
               "• Для подготовки документа введённые вами тема и данные обрабатываются с помощью сервисов искусственного интеллекта.\n"
               "• Файлы доставляются через Telegram.\n"
               "• При оплате через Click мы не видим данные вашей карты — они остаются в платёжной системе.\n"
               "• Ваши данные не продаются и не передаются третьим лицам для рекламы.\n\n"
               "<b>4. Срок хранения</b>\n"
               "Записи о заказах и платежах хранятся для учёта. Если вы попросите удалить данные, администратор "
               "рассмотрит запрос; записи, которые требуются по закону или для учёта, могут сохраниться.\n\n"
               "<b>5. Документ и ответственность</b>\n"
               "Документ готовится с помощью искусственного интеллекта и может содержать ошибки или неточности. "
               "Проверка перед сдачей и соблюдение правил академической честности вашего учебного заведения — "
               "ваша ответственность. Результат (оценка, оригинальность, проверка на плагиат) зависит от многих факторов и заранее не обещается.\n\n"
               "<b>6. Оплата и возврат</b>\n"
               "Оплата зачисляется на баланс, стоимость заказа списывается с него. Если заказ завершился ошибкой, "
               "сумма автоматически вернётся на баланс. Возврат остатка наличными согласуется с администратором.\n\n"
               "<b>7. Контакты</b>\n"
               "По вопросам и запросам: {contact}.\n\n"
               "Нажимая «Согласен», вы принимаете эти условия."),
        "en": ("📄 <b>Privacy policy & terms of use</b> (v{version})\n\n"
               "<b>1. What data is stored</b>\n"
               "Telegram ID, name, username, chosen language; the order details you enter (topic, subject, "
               "document language and, optionally, name, university, faculty, group, supervisor for the title "
               "page); balance and payment records (amount, method, receipt photo for card payments).\n\n"
               "<b>2. Why</b>\n"
               "To prepare and deliver the document, keep payment records, resolve problems and prevent fraud.\n\n"
               "<b>3. Processing and third parties</b>\n"
               "• To prepare the document, the topic and details you enter are processed using artificial intelligence services.\n"
               "• Files are delivered through Telegram.\n"
               "• For Click payments we never see your card details — they stay with the payment system.\n"
               "• Your data is not sold and not shared with third parties for advertising.\n\n"
               "<b>4. Retention</b>\n"
               "Order and payment records are kept for accounting. If you ask for deletion, the administrator "
               "will review the request; records required by law or accounting may be retained.\n\n"
               "<b>5. The document and responsibility</b>\n"
               "The document is prepared with the help of artificial intelligence and may contain errors or "
               "inaccuracies. Checking it before submission and following your institution's academic integrity "
               "rules is your responsibility. The outcome (grade, originality, plagiarism check) depends on many factors and is not promised in advance.\n\n"
               "<b>6. Payment and refunds</b>\n"
               "Payments are credited to your balance and the order price is deducted from it. If an order fails, "
               "the amount returns to your balance automatically. Cash refunds of the balance are arranged with the administrator.\n\n"
               "<b>7. Contact</b>\n"
               "Questions and requests: {contact}.\n\n"
               "By pressing “I agree” you accept these terms."),
    },
    "consent_needed": {
        "uz": "Davom etish uchun avval shartlarga rozilik bildiring 👇",
        "ru": "Чтобы продолжить, сначала подтвердите согласие с условиями 👇",
        "en": "To continue, please accept the terms first 👇",
    },
    # ── asosiy menyu ─────────────────────────────────────────────────────
    "welcome": {
        "uz": ("👋 Salom, <b>{name}</b>!\n\nMen kurs ishi, taqdimot, referat va boshqa hujjatlarni tez tayyorlab beraman.\n\n"
               "<b>Xizmatlar va narxlar:</b>\n{services}\n\nPastdagi menyudan xizmatni tanlang 👇"),
        "ru": ("👋 Привет, <b>{name}</b>!\n\nЯ быстро готовлю курсовые, презентации, рефераты и другие документы.\n\n"
               "<b>Услуги и цены:</b>\n{services}\n\nВыберите услугу в меню ниже 👇"),
        "en": ("👋 Hello, <b>{name}</b>!\n\nI quickly prepare coursework, presentations, essays and other documents.\n\n"
               "<b>Services and prices:</b>\n{services}\n\nPick a service from the menu below 👇"),
    },
    "from_price": {"uz": "{price} dan", "ru": "от {price}", "en": "from {price}"},
    "menu_placeholder": {"uz": "Xizmatni tanlang 👇", "ru": "Выберите услугу 👇", "en": "Choose a service 👇"},
    "menu_home": {"uz": "🏠 Asosiy menyu", "ru": "🏠 Главное меню", "en": "🏠 Main menu"},
    "btn_balance": {"uz": "💰 Balans", "ru": "💰 Баланс", "en": "💰 Balance"},
    "btn_orders": {"uz": "📦 Buyurtmalarim", "ru": "📦 Мои заказы", "en": "📦 My orders"},
    "btn_help": {"uz": "ℹ️ Yordam", "ru": "ℹ️ Помощь", "en": "ℹ️ Help"},
    "btn_lang": {"uz": "🌐 Til", "ru": "🌐 Язык", "en": "🌐 Language"},
    "help": {
        "uz": ("ℹ️ <b>Yordam</b>\n\n• Xizmatni menyudan tanlang, savollarga javob bering — qolganini o'zim bajaraman.\n"
               "• To'lov balansdan yechiladi. Balansni <b>💰 Balans</b> orqali to'ldirasiz.\n"
               "• Buyurtma xato bilan tugasa, pul balansingizga avtomatik qaytadi.\n"
               "• Tayyor fayllarni <b>📦 Buyurtmalarim</b> dan qayta yuklab olish mumkin.\n\n"
               "Savol yoki muammo bo'lsa: {contact}\n🔒 Shartlar: /privacy"),
        "ru": ("ℹ️ <b>Помощь</b>\n\n• Выберите услугу в меню, ответьте на вопросы — остальное сделаю я.\n"
               "• Оплата списывается с баланса. Пополнить баланс можно через <b>💰 Баланс</b>.\n"
               "• Если заказ завершится ошибкой, деньги автоматически вернутся на баланс.\n"
               "• Готовые файлы можно скачать повторно в <b>📦 Мои заказы</b>.\n\n"
               "Вопросы и проблемы: {contact}\n🔒 Условия: /privacy"),
        "en": ("ℹ️ <b>Help</b>\n\n• Choose a service from the menu and answer the questions — I'll do the rest.\n"
               "• The price is deducted from your balance. Top it up via <b>💰 Balance</b>.\n"
               "• If an order fails, the money returns to your balance automatically.\n"
               "• You can re-download finished files in <b>📦 My orders</b>.\n\n"
               "Questions or problems: {contact}\n🔒 Terms: /privacy"),
    },
    "admin_word": {"uz": "administrator", "ru": "администратор", "en": "the administrator"},
    # ── buyurtma oqimi ───────────────────────────────────────────────────
    "flow_intro": {
        "uz": "{emoji} <b>{title}</b> — {price}\n📦 {note} · ⏱ taxminan {eta}\n\nBir necha savolga javob bering.",
        "ru": "{emoji} <b>{title}</b> — {price}\n📦 {note} · ⏱ примерно {eta}\n\nОтветьте на несколько вопросов.",
        "en": "{emoji} <b>{title}</b> — {price}\n📦 {note} · ⏱ about {eta}\n\nPlease answer a few questions.",
    },
    "pick_button": {"uz": "Iltimos, yuqoridagi tugmalardan birini tanlang 👆", "ru": "Пожалуйста, выберите одну из кнопок выше 👆", "en": "Please choose one of the buttons above 👆"},
    "bad_length": {
        "uz": "Uzunligi {lo}–{hi} belgi bo'lishi kerak (hozir {n}). Qayta yozing.",
        "ru": "Длина должна быть {lo}–{hi} символов (сейчас {n}). Напишите ещё раз.",
        "en": "Length must be {lo}–{hi} characters (now {n}). Please write again.",
    },
    "stale_choice": {"uz": "Bu tanlov endi amal qilmaydi", "ru": "Этот выбор больше не действует", "en": "This choice is no longer valid"},
    "required": {"uz": "Bu savol majburiy", "ru": "Этот вопрос обязателен", "en": "This question is required"},
    "btn_skip": {"uz": "⏭ O'tkazib yuborish", "ru": "⏭ Пропустить", "en": "⏭ Skip"},
    "btn_skip_all": {"uz": "⏭ Qolganini o'tkazib yuborish", "ru": "⏭ Пропустить остальное", "en": "⏭ Skip the rest"},
    "btn_cancel": {"uz": "❌ Bekor qilish", "ru": "❌ Отмена", "en": "❌ Cancel"},
    "cancelled": {
        "uz": "Bekor qilindi. Menyudan boshqa xizmatni tanlashingiz mumkin.",
        "ru": "Отменено. Вы можете выбрать другую услугу в меню.",
        "en": "Cancelled. You can pick another service from the menu.",
    },
    "cancelled_toast": {"uz": "Bekor qilindi", "ru": "Отменено", "en": "Cancelled"},
    "profile_found": {
        "uz": "💾 <b>Saqlangan ma'lumotlaringiz:</b>\n{profile}\n\nShularni ishlataymi?",
        "ru": "💾 <b>Ваши сохранённые данные:</b>\n{profile}\n\nИспользовать их?",
        "en": "💾 <b>Your saved details:</b>\n{profile}\n\nUse them?",
    },
    "btn_use_profile": {"uz": "✅ Ha, ishlatilsin", "ru": "✅ Да, использовать", "en": "✅ Yes, use them"},
    "btn_new_profile": {"uz": "✏️ Yangilash", "ru": "✏️ Обновить", "en": "✏️ Update"},
    "confirm_screen": {
        "uz": "{emoji} <b>{title}</b>\n\n{summary}\n\n💵 Narxi: <b>{price}</b>\n💰 Balansingiz: {balance}",
        "ru": "{emoji} <b>{title}</b>\n\n{summary}\n\n💵 Цена: <b>{price}</b>\n💰 Ваш баланс: {balance}",
        "en": "{emoji} <b>{title}</b>\n\n{summary}\n\n💵 Price: <b>{price}</b>\n💰 Your balance: {balance}",
    },
    "short_by": {
        "uz": "\n\n⚠️ Yetmaydi: yana <b>{need}</b> kerak.",
        "ru": "\n\n⚠️ Не хватает: нужно ещё <b>{need}</b>.",
        "en": "\n\n⚠️ Not enough: you need <b>{need}</b> more.",
    },
    "btn_order": {"uz": "✅ Buyurtma berish", "ru": "✅ Заказать", "en": "✅ Place order"},
    "btn_topup_short": {"uz": "💳 Balansni to'ldirish", "ru": "💳 Пополнить баланс", "en": "💳 Top up balance"},
    "order_accepted": {
        "uz": "✅ <b>Buyurtma #{id} qabul qilindi</b>\n\n{emoji} {title} — taxminan {eta}. Tayyor bo'lishi bilan shu yerga yuboraman.",
        "ru": "✅ <b>Заказ #{id} принят</b>\n\n{emoji} {title} — примерно {eta}. Как только будет готово, пришлю сюда.",
        "en": "✅ <b>Order #{id} accepted</b>\n\n{emoji} {title} — about {eta}. I'll send it here as soon as it's ready.",
    },
    "balance_low": {
        "uz": "⚠️ Balans yetarli emas. 💰 Balans orqali to'ldiring.",
        "ru": "⚠️ Недостаточно средств. Пополните через 💰 Баланс.",
        "en": "⚠️ Insufficient balance. Top up via 💰 Balance.",
    },
    "too_many_active": {
        "uz": "⏳ Sizda hozir {n} ta buyurtma tayyorlanmoqda — bu eng ko'pi. Biri tugagach yangisini bering.",
        "ru": "⏳ У вас уже готовится {n} заказов — это максимум. Дождитесь завершения одного из них.",
        "en": "⏳ You already have {n} orders in progress — that's the maximum. Please wait for one to finish.",
    },
    # ── balans ───────────────────────────────────────────────────────────
    "balance_screen": {
        "uz": "💰 <b>Balansingiz: {amount}</b>\n\nBuyurtma narxi balansdan yechiladi.",
        "ru": "💰 <b>Ваш баланс: {amount}</b>\n\nСтоимость заказа списывается с баланса.",
        "en": "💰 <b>Your balance: {amount}</b>\n\nThe order price is deducted from your balance.",
    },
    "btn_topup": {"uz": "➕ Balansni to'ldirish", "ru": "➕ Пополнить баланс", "en": "➕ Top up balance"},
    "topup_howmuch": {"uz": "💳 <b>Qancha to'ldirasiz?</b>{hint}", "ru": "💳 <b>На какую сумму пополнить?</b>{hint}", "en": "💳 <b>How much would you like to add?</b>{hint}"},
    "topup_hint": {"uz": "\nKerakli summa: <b>{need}</b>", "ru": "\nНужная сумма: <b>{need}</b>", "en": "\nAmount needed: <b>{need}</b>"},
    "btn_other_amount": {"uz": "✏️ Boshqa summa", "ru": "✏️ Другая сумма", "en": "✏️ Other amount"},
    "type_amount": {"uz": "Summani yozing ({lo} – {hi}):", "ru": "Напишите сумму ({lo} – {hi}):", "en": "Enter the amount ({lo} – {hi}):"},
    "amount_range": {
        "uz": "Summa {lo} dan {hi} gacha bo'lishi kerak. Qayta yozing.",
        "ru": "Сумма должна быть от {lo} до {hi}. Напишите ещё раз.",
        "en": "The amount must be between {lo} and {hi}. Please enter it again.",
    },
    "choose_method": {
        "uz": "💵 To'ldirish summasi: <b>{amount}</b>\nTo'lov usulini tanlang:",
        "ru": "💵 Сумма пополнения: <b>{amount}</b>\nВыберите способ оплаты:",
        "en": "💵 Top-up amount: <b>{amount}</b>\nChoose a payment method:",
    },
    "no_methods": {
        "uz": "To'lov usullari hozircha sozlanmagan. Administratorga murojaat qiling.",
        "ru": "Способы оплаты пока не настроены. Обратитесь к администратору.",
        "en": "Payment methods aren't set up yet. Please contact the administrator.",
    },
    "btn_click": {"uz": "🔵 Click (avtomatik)", "ru": "🔵 Click (автоматически)", "en": "🔵 Click (automatic)"},
    "btn_card": {"uz": "💳 Karta orqali (chek)", "ru": "💳 Картой (чек)", "en": "💳 By card (receipt)"},
    "btn_pay": {"uz": "💳 To'lash", "ru": "💳 Оплатить", "en": "💳 Pay"},
    "click_screen": {
        "uz": "🔵 <b>Click orqali to'lash</b>\nSumma: <b>{amount}</b>\n\nTo'lov tasdiqlangach balansingiz avtomatik to'ladi.",
        "ru": "🔵 <b>Оплата через Click</b>\nСумма: <b>{amount}</b>\n\nПосле подтверждения платежа баланс пополнится автоматически.",
        "en": "🔵 <b>Pay with Click</b>\nAmount: <b>{amount}</b>\n\nYour balance will be topped up automatically once the payment is confirmed.",
    },
    "card_screen": {
        "uz": ("💳 <b>Karta orqali to'lash</b>\n\nSumma: <b>{amount}</b>\nKarta: <code>{card}</code>\n{holder}"
               "\nO'tkazgach <b>chek rasmini</b> shu yerga yuboring. Administrator tekshirib, balansni to'ldiradi."),
        "ru": ("💳 <b>Оплата картой</b>\n\nСумма: <b>{amount}</b>\nКарта: <code>{card}</code>\n{holder}"
               "\nПосле перевода отправьте сюда <b>фото чека</b>. Администратор проверит и пополнит баланс."),
        "en": ("💳 <b>Pay by card</b>\n\nAmount: <b>{amount}</b>\nCard: <code>{card}</code>\n{holder}"
               "\nAfter the transfer, send the <b>receipt photo</b> here. The administrator will check it and top up your balance."),
    },
    "card_holder": {"uz": "Qabul qiluvchi: {name}\n", "ru": "Получатель: {name}\n", "en": "Recipient: {name}\n"},
    "receipt_ok": {
        "uz": "✅ Chek qabul qilindi. Administrator tekshirgach, balansingiz to'ladi va sizga xabar beraman.",
        "ru": "✅ Чек принят. Когда администратор проверит, баланс пополнится, и я сообщу вам.",
        "en": "✅ Receipt received. Once the administrator checks it, your balance will be topped up and I'll let you know.",
    },
    "receipt_not_photo": {
        "uz": "Iltimos, chek <b>rasmini</b> yuboring (fayl emas, rasm).",
        "ru": "Пожалуйста, отправьте <b>фото</b> чека (не файл, а фото).",
        "en": "Please send the receipt as a <b>photo</b> (not a file).",
    },
    "pay_approved": {
        "uz": "✅ To'lovingiz tasdiqlandi: <b>+{amount}</b>. Balansingiz to'ldi.",
        "ru": "✅ Ваш платёж подтверждён: <b>+{amount}</b>. Баланс пополнен.",
        "en": "✅ Your payment is confirmed: <b>+{amount}</b>. Your balance has been topped up.",
    },
    "pay_approved_edited": {
        "uz": "✅ To'lovingiz tasdiqlandi. Chekdagi summa sizniki ({asked}) bilan mos kelmadi, shuning uchun <b>+{amount}</b> hisobga olindi.",
        "ru": "✅ Платёж подтверждён. Сумма в чеке не совпала с указанной вами ({asked}), поэтому зачислено <b>+{amount}</b>.",
        "en": "✅ Your payment is confirmed. The amount on the receipt didn't match the one you entered ({asked}), so <b>+{amount}</b> was credited.",
    },
    "pay_rejected": {
        "uz": "❌ To'lovingiz tasdiqlanmadi. Chek noto'g'ri bo'lsa, qayta yuboring yoki administratorga yozing.",
        "ru": "❌ Ваш платёж не подтверждён. Если чек неверный, отправьте заново или напишите администратору.",
        "en": "❌ Your payment was not confirmed. If the receipt was wrong, send it again or contact the administrator.",
    },
    "click_paid": {
        "uz": "🎉 To'lov muvaffaqiyatli: <b>+{amount}</b>. Balansingiz to'ldi.",
        "ru": "🎉 Оплата прошла: <b>+{amount}</b>. Баланс пополнен.",
        "en": "🎉 Payment successful: <b>+{amount}</b>. Your balance has been topped up.",
    },
    # ── kanalga a'zolik va promokod ──────────────────────────────────────
    "sub_required": {
        "uz": ("📢 <b>Botdan foydalanish uchun kanalimizga a'zo bo'ling</b>\n\n"
               "Kanalda yangiliklar va <b>🎁 bepul xizmat beradigan promokodlar</b> e'lon qilinadi.\n\n"
               "A'zo bo'lgach «✅ A'zo bo'ldim» tugmasini bosing 👇"),
        "ru": ("📢 <b>Чтобы пользоваться ботом, подпишитесь на наш канал</b>\n\n"
               "В канале публикуются новости и <b>🎁 промокоды на бесплатные услуги</b>.\n\n"
               "После подписки нажмите «✅ Я подписался» 👇"),
        "en": ("📢 <b>Please subscribe to our channel to use the bot</b>\n\n"
               "The channel posts news and <b>🎁 promo codes for free services</b>.\n\n"
               "After subscribing, press “✅ I've subscribed” 👇"),
    },
    "btn_channel": {"uz": "📢 Kanalga o'tish", "ru": "📢 Перейти в канал", "en": "📢 Open channel"},
    "btn_subscribed": {"uz": "✅ A'zo bo'ldim", "ru": "✅ Я подписался", "en": "✅ I've subscribed"},
    "not_member": {"uz": "Hali kanalga a'zo emassiz", "ru": "Вы ещё не подписаны на канал", "en": "You haven't subscribed to the channel yet"},
    "btn_promo": {"uz": "🎁 Promokod", "ru": "🎁 Промокод", "en": "🎁 Promo code"},
    "promo_ask": {
        "uz": "🎁 <b>Promokod</b>\n\nKanalimizdagi promokodni yozing:",
        "ru": "🎁 <b>Промокод</b>\n\nНапишите промокод из нашего канала:",
        "en": "🎁 <b>Promo code</b>\n\nEnter the promo code from our channel:",
    },
    "promo_ok": {
        "uz": ("🎉 <b>Promokod qabul qilindi!</b>\n\nQuyidagi xizmatlardan <b>istalgan bittasi bepul</b> (hajmi ahamiyatsiz):\n{services}\n\n"
               "Xizmatni tanlang va tasdiqlash ekranida «🎁 Bepul olish» tugmasini bosing."),
        "ru": ("🎉 <b>Промокод принят!</b>\n\nИз этих услуг <b>любая одна — бесплатно</b> (объём не важен):\n{services}\n\n"
               "Выберите услугу и на экране подтверждения нажмите «🎁 Получить бесплатно»."),
        "en": ("🎉 <b>Promo code accepted!</b>\n\n<b>Any one</b> of these services is <b>free</b> (any size):\n{services}\n\n"
               "Choose a service and press “🎁 Get it free” on the confirmation screen."),
    },
    "promo_invalid": {"uz": "❌ Bunday promokod yo'q yoki o'chirilgan. Kodni tekshirib, qayta yozing.", "ru": "❌ Такого промокода нет или он отключён. Проверьте код и напишите ещё раз.", "en": "❌ This promo code doesn't exist or is disabled. Check it and try again."},
    "promo_expired": {"uz": "⌛ Bu promokod muddati tugagan.", "ru": "⌛ Срок действия этого промокода истёк.", "en": "⌛ This promo code has expired."},
    "promo_limit": {"uz": "😔 Bu promokod bo'yicha bepul xizmatlar tugab bo'ldi.", "ru": "😔 Бесплатные услуги по этому промокоду закончились.", "en": "😔 The free services for this promo code have run out."},
    "promo_used": {"uz": "Siz bu promokodni allaqachon kiritgansiz.", "ru": "Вы уже вводили этот промокод.", "en": "You have already used this promo code."},
    "promo_has_active": {
        "uz": "🎁 Sizda allaqachon bepul buyurtma bor. Avval undan foydalaning, keyin yangi promokod kiritasiz.",
        "ru": "🎁 У вас уже есть бесплатный заказ. Сначала используйте его, затем вводите новый промокод.",
        "en": "🎁 You already have a free order. Use it first, then enter a new promo code.",
    },
    "voucher_note": {"uz": "\n🎁 Sizda <b>bepul buyurtma</b> bor.", "ru": "\n🎁 У вас есть <b>бесплатный заказ</b>.", "en": "\n🎁 You have a <b>free order</b>."},
    "btn_free": {"uz": "🎁 Bepul olish", "ru": "🎁 Получить бесплатно", "en": "🎁 Get it free"},
    "free_gone": {"uz": "Bepul buyurtma huquqi topilmadi yoki ishlatilgan.", "ru": "Право на бесплатный заказ не найдено или уже использовано.", "en": "The free order was not found or has already been used."},
    # ── buyurtmalar ──────────────────────────────────────────────────────
    "no_orders": {"uz": "Hali buyurtmangiz yo'q. Menyudan xizmatni tanlang 👇", "ru": "У вас ещё нет заказов. Выберите услугу в меню 👇", "en": "You have no orders yet. Choose a service from the menu 👇"},
    "orders_title": {"uz": "📦 <b>So'nggi buyurtmalaringiz</b>\n", "ru": "📦 <b>Ваши последние заказы</b>\n", "en": "📦 <b>Your recent orders</b>\n"},
    "btn_download": {"uz": "📥 #{id} ni yuklab olish", "ru": "📥 Скачать #{id}", "en": "📥 Download #{id}"},
    "dl_missing": {"uz": "Bu buyurtma topilmadi.", "ru": "Заказ не найден.", "en": "Order not found."},
    "dl_not_ready": {"uz": "Bu buyurtma hali tayyor emas.", "ru": "Этот заказ ещё не готов.", "en": "This order isn't ready yet."},
    "dl_expired": {
        "uz": "⌛ Bu fayl saqlash muddati (7 kun) tugagani uchun yuklab bo'lmaydi.",
        "ru": "⌛ Файл больше недоступен: срок хранения (7 дней) истёк.",
        "en": "⌛ This file is no longer available: the 7-day storage period has ended.",
    },
    "dl_error": {
        "uz": "Faylni hozir olib bo'lmadi. Birozdan so'ng qayta urinib ko'ring.",
        "ru": "Сейчас не удалось получить файл. Попробуйте чуть позже.",
        "en": "Couldn't fetch the file right now. Please try again shortly.",
    },
    "st_queued": {"uz": "⏳ Navbatda", "ru": "⏳ В очереди", "en": "⏳ Queued"},
    "st_submitted": {"uz": "⚙️ Tayyorlanmoqda", "ru": "⚙️ Готовится", "en": "⚙️ In progress"},
    "st_processing": {"uz": "⚙️ Tayyorlanmoqda", "ru": "⚙️ Готовится", "en": "⚙️ In progress"},
    "st_succeeded": {"uz": "✅ Tayyor", "ru": "✅ Готов", "en": "✅ Ready"},
    "st_failed": {"uz": "❌ Xato (pul qaytarilgan)", "ru": "❌ Ошибка (деньги возвращены)", "en": "❌ Failed (refunded)"},
    "st_canceled": {"uz": "🚫 Bekor qilingan", "ru": "🚫 Отменён", "en": "🚫 Cancelled"},
    # ── ishchi xabarlari ─────────────────────────────────────────────────
    "delivered": {
        "uz": "✅ <b>{title}</b> tayyor! (buyurtma #{id})",
        "ru": "✅ <b>{title}</b> готов! (заказ #{id})",
        "en": "✅ <b>{title}</b> is ready! (order #{id})",
    },
    "disclaimer": {
        "uz": "\n\n⚠️ Hujjat sun'iy intellekt yordamida tayyorlangan. Topshirishdan oldin o'zingiz diqqat bilan o'qib chiqing va o'quv yurtingizning qoidalariga rioya qiling.",
        "ru": "\n\n⚠️ Документ подготовлен с помощью искусственного интеллекта. Перед сдачей внимательно прочитайте его сами и соблюдайте правила вашего учебного заведения.",
        "en": "\n\n⚠️ This document was prepared with the help of artificial intelligence. Read it carefully before submitting and follow your institution's rules.",
    },
    "fail_unavailable": {
        "uz": "❌ <b>Buyurtma #{id}</b>\nHozir bu xizmat vaqtincha mavjud emas. Pulingiz balansga qaytarildi, birozdan so'ng qayta urinib ko'ring.",
        "ru": "❌ <b>Заказ #{id}</b>\nСейчас эта услуга временно недоступна. Деньги возвращены на баланс, попробуйте чуть позже.",
        "en": "❌ <b>Order #{id}</b>\nThis service is temporarily unavailable. Your money has been returned to your balance — please try again shortly.",
    },
    "fail_down": {
        "uz": "❌ <b>Buyurtma #{id}</b>\nXizmat hozir javob bermayapti. Pulingiz balansga qaytarildi, birozdan so'ng qayta urinib ko'ring.",
        "ru": "❌ <b>Заказ #{id}</b>\nСервис сейчас не отвечает. Деньги возвращены на баланс, попробуйте чуть позже.",
        "en": "❌ <b>Order #{id}</b>\nThe service isn't responding. Your money has been returned to your balance — please try again shortly.",
    },
    "fail_rejected": {
        "uz": "❌ <b>Buyurtma #{id}</b>\nBuyurtmani bajarib bo'lmadi. Pulingiz balansga qaytarildi.",
        "ru": "❌ <b>Заказ #{id}</b>\nЗаказ выполнить не удалось. Деньги возвращены на баланс.",
        "en": "❌ <b>Order #{id}</b>\nThe order couldn't be completed. Your money has been returned to your balance.",
    },
    "fail_generation": {
        "uz": "❌ <b>Buyurtma #{id}</b> tayyorlanmadi. Pulingiz balansga qaytarildi, qayta urinib ko'rishingiz mumkin.",
        "ru": "❌ <b>Заказ #{id}</b> не удалось подготовить. Деньги возвращены на баланс, вы можете попробовать снова.",
        "en": "❌ <b>Order #{id}</b> couldn't be prepared. Your money has been returned to your balance — you can try again.",
    },
}


def t(lang: str | None, key: str, **kw) -> str:
    entry = TEXTS[key]
    text = entry.get(lang if lang in LANGS else DEFAULT) or entry[DEFAULT]
    return text.format(**kw) if kw else text


def pick(mapping: dict[str, str], lang: str | None) -> str:
    """Uch tilli lug'atdan tilga mos qiymat (uz — zaxira)."""
    return mapping.get(lang if lang in LANGS else DEFAULT) or mapping[DEFAULT]


def all_langs(key: str) -> set[str]:
    return set(TEXTS[key].values())
