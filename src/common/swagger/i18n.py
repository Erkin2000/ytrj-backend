"""Узбекская версия OpenAPI-документации.

Русские строки в коде (summary, description, теги, описания полей, примеры)
остаются источником. Для узбекской схемы готовая OpenAPI-структура обходится
целиком, и каждая строка, совпадающая с ключом словаря ``UZ``, заменяется
переводом. Непереведённые строки остаются русскими — их находит
``untranslated(spec)``; при добавлении новой ручки допишите перевод в ``UZ``.
"""

from __future__ import annotations

import copy
import re
from typing import Any

DESCRIPTION_UZ = """
**Jamgʻarma** moliyalashtirish platformasining backend qismi (YTRJ-EP).

FastAPI asosidagi modulli monolit. Joriy modullar:

- **auth** — YIA Portal (SSO) va parol orqali kirish, rotatsiyali JWT access/refresh, sessiyalar;
- **rbac** — modullar boʻyicha rollar va ruxsatlar (Create / Read / Update / Delete / Approve), server tomonida tekshiruv;
- **account** — foydalanuvchilar, holatlar, scope (bank), oxirgi kirish va sessiyalar;
- **application** — arizalar: qoralama → KATM skoringi → Jamgʻarma → Kengash → bank → yakunlash.

Barcha javoblar yagona formatda: `{"success": bool, "message": str, "data": ...}`.
Avtorizatsiya: `Authorization: Bearer <access_token>` sarlavhasi.

Hujjat tili chap yuqoridagi tanlovda almashtiriladi (Русский / Oʻzbek).
"""


UZ: dict[str, str] = {
    # ---------- теги ----------
    "Авторизация и аутентификация": "Avtorizatsiya va autentifikatsiya",
    "Пользователи": "Foydalanuvchilar",
    "RBAC: роли": "RBAC: rollar",
    "RBAC: права": "RBAC: ruxsatlar",
    "Каталог банков": "Banklar katalogi",
    "Заявки: кабинет заявителя": "Arizalar: ariza beruvchi kabineti",
    "Заявки: рабочее окно Фонда": "Arizalar: Jamgʻarma ish oynasi",
    "Заявки: рабочее окно банка": "Arizalar: bank ish oynasi",
    "Заявки: рабочее окно Совета": "Arizalar: Kengash ish oynasi",
    "YIA Portal SSO, логин/пароль, refresh, профиль.": (
        "YIA Portal SSO, login/parol, refresh, profil."
    ),
    "Super Admin: профили, роли, scope, блокировка, сессии.": (
        "Super Admin: profillar, rollar, scope, bloklash, sessiyalar."
    ),
    "Каталог ролей и матрица разрешений.": "Rollar katalogi va ruxsatlar matritsasi.",
    "Каталог прав платформы.": "Platforma ruxsatlari katalogi.",
    "Банки-партнёры и правила выбора по типу субъекта.": (
        "Hamkor banklar va subyekt turi boʻyicha tanlash qoidalari."
    ),
    "Поиск, скоринг, отказ или направление в Совет.": (
        "Qidiruv, skoring, rad etish yoki Kengashga yoʻnaltirish."
    ),
    "Приём и результат по утверждённым Советом заявкам своего банка.": (
        "Kengash tasdiqlagan oʻz banki arizalarini qabul qilish va natija kiritish."
    ),
    "Решение по направленным заявкам.": "Yoʻnaltirilgan arizalar boʻyicha qaror.",
    # ---------- общие ----------
    "Ошибка валидации.": "Validatsiya xatosi.",
    "Обязательное поле.": "Majburiy maydon.",
    # ---------- auth ----------
    "Вход по логину и паролю — только внутренние роли (Super Admin, Фонд, банк, Совет)": (
        "Login va parol bilan kirish — faqat ichki rollar (Super Admin, Jamgʻarma, bank, Kengash)"
    ),
    "Обновление пары токенов (ротация refresh-токена)": (
        "Token juftligini yangilash (refresh-token rotatsiyasi)"
    ),
    "Выход (отзыв refresh-токена)": "Chiqish (refresh-tokenni bekor qilish)",
    "Завершить все сессии текущего пользователя": (
        "Joriy foydalanuvchining barcha sessiyalarini yakunlash"
    ),
    "Текущий пользователь: профиль, роль, права, scope": (
        "Joriy foydalanuvchi: profil, rol, ruxsatlar, scope"
    ),
    "`profile_complete` / `missing_fields` показывают, какие данные заявителю нужно "
    "дополнить через `PATCH /auth/me`, прежде чем создавать заявку.": (
        "`profile_complete` / `missing_fields` ariza beruvchi ariza yaratishdan oldin "
        "`PATCH /auth/me` orqali qaysi maʼlumotlarni toʻldirishi kerakligini koʻrsatadi."
    ),
    "Дополнить свой профиль: телефон, паспорт, ИНН, email, пол, дата рождения": (
        "Oʻz profilini toʻldirish: telefon, pasport, STIR, email, jins, tugʻilgan sana"
    ),
    "YIA Portal передаёт только Ф.И.О. и ПИНФЛ — эти поля обновляются при входе "
    "и здесь не принимаются (ответ 422). Передавать можно любое подмножество полей; "
    "`null` очищает поле. Пока профиль не заполнен полностью, создать заявку нельзя.": (
        "YIA Portal faqat F.I.Sh. va JShShIRni uzatadi — bu maydonlar kirishda yangilanadi "
        "va bu yerda qabul qilinmaydi (javob 422). Maydonlarning istalgan qismini yuborish "
        "mumkin; `null` maydonni tozalaydi. Profil toʻliq toʻldirilmaguncha ariza yaratib "
        "boʻlmaydi."
    ),
    "Серия и номер паспорта или ID-карты без пробелов.": (
        "Pasport yoki ID-karta seriyasi va raqami, probelsiz."
    ),
    "Дополнение собственного профиля. Ф.И.О. и ПИНФЛ приходят из YIA SSO\n"
    "и здесь не принимаются (лишние поля отклоняются с 422).": (
        "Oʻz profilini toʻldirish. F.I.Sh. va JShShIR YIA SSO dan keladi\n"
        "va bu yerda qabul qilinmaydi (ortiqcha maydonlar 422 bilan rad etiladi)."
    ),
    "Заявитель": "Ariza beruvchi",
    "Смена собственного пароля (закрывает прежние сессии)": (
        "Oʻz parolini oʻzgartirish (avvalgi sessiyalar yopiladi)"
    ),
    "YIA SSO: ссылка на страницу входа портала и подписанный state": (
        "YIA SSO: portal kirish sahifasiga havola va imzolangan state"
    ),
    "Фронтенд сохраняет `state` (sessionStorage) и перенаправляет браузер на `authorize_url`. "
    "Портал вернёт пользователя на `SSO_REDIRECT_URI` с `code` и `state`.": (
        "Frontend `state`ni saqlaydi (sessionStorage) va brauzerni `authorize_url`ga yoʻnaltiradi. "
        "Portal foydalanuvchini `SSO_REDIRECT_URI`ga `code` va `state` bilan qaytaradi."
    ),
    "YIA SSO (все роли): обмен code на токены": "YIA SSO (barcha rollar): code ni tokenlarga almashtirish",
    "YIA SSO (тест): вход с ручными данными — при SSO_MOCK=True": (
        "YIA SSO (test): qoʻlda kiritilgan maʼlumotlar bilan kirish — SSO_MOCK=True boʻlganda"
    ),
    "Как `POST /auth/sso/callback`, но профиль портала задаётся вручную. ПИНФЛ сотрудника, заведённого Super Admin, входит под его учётной записью.": "`POST /auth/sso/callback` kabi, lekin portal profili qoʻlda beriladi. Super Admin qoʻshgan xodimning JShShIRi bilan uning hisobiga kiriladi.",
    "Возврат с YIA Portal → редирект на фронтенд": (
        "YIA Portaldan qaytish → frontendga yoʻnaltirish"
    ),
    "Адрес, зарегистрированный на портале как `SSO_REDIRECT_URI` (и `SSO_REDIRECT_URI_ADMIN` для админки). Отвечает `302` на `SSO_FRONTEND_REDIRECT_URL` — или на `SSO_FRONTEND_REDIRECT_URL_ADMIN`, если вход начат с `site=admin` (сайт берётся из подписанного `state`), — передавая все query-параметры портала (`code`, `state`, `error`) без изменений. Код обменивает фронтенд через `POST /auth/sso/callback` (code живёт 60 секунд).": "Portalda `SSO_REDIRECT_URI` (admin panel uchun esa `SSO_REDIRECT_URI_ADMIN`) sifatida roʻyxatdan oʻtgan manzil. `SSO_FRONTEND_REDIRECT_URL` manziliga — kirish `site=admin` bilan boshlangan boʻlsa, `SSO_FRONTEND_REDIRECT_URL_ADMIN` manziliga (sayt imzolangan `state`dan olinadi) — `302` javobini qaytaradi va portalning barcha query-parametrlarini (`code`, `state`, `error`) oʻzgarishsiz uzatadi. `code`ni frontend `POST /auth/sso/callback` orqali almashtiradi (`code` 60 soniya amal qiladi).",
    "Редирект на SSO_FRONTEND_REDIRECT_URL с query портала": (
        "Portal query-parametrlari bilan SSO_FRONTEND_REDIRECT_URLga yoʻnaltirish"
    ),
    "Фронтенд передаёт сюда `code`, `state` и `error` из query-параметров redirect_uri. `code` одноразовый и живёт 60 секунд — вызывать сразу после редиректа. Заявитель создаётся при первом входе; сотрудник (Фонд, банк, Совет) должен быть заранее заведён Super Admin с его ПИНФЛ.": "Frontend bu yerga redirect_uri query-parametrlaridagi `code`, `state` va `error`ni uzatadi. `code` bir martalik va 60 soniya amal qiladi — redirektdan soʻng darhol chaqiring. Ariza beruvchi birinchi kirishda yaratiladi; xodim (Jamgʻarma, bank, Kengash) esa Super Admin tomonidan JShShIRi bilan oldindan qoʻshilgan boʻlishi kerak.",
    "Создание сотрудника (роль + ПИНФЛ для входа через YIA Portal и/или пароль)": (
        "Xodim yaratish (rol + YIA Portal orqali kirish uchun JShShIR va/yoki parol)"
    ),
    "Сотрудник Фонда, банка или Совета входит через YIA Portal: при входе он "
    "находится по `pinfl` и попадает в кабинет своей роли. `password` нужен только "
    "для входа по логину и паролю; хотя бы одно из полей обязательно. "
    "Смена `pinfl` снимает привязку к учётке портала и закрывает сессии.\n\n"
    "**Админ направления** создаёт сотрудников только своего направления: роль "
    "(и банк) подставляются его собственные, `permissions` — только из его прав. "
    "Без `permissions` выдаются все права, которые создающий может выдать для роли. "
    "`is_direction_admin` назначает только Super Admin.": "Jamgʻarma, bank yoki Kengash xodimi YIA Portal orqali kiradi: kirishda u `pinfl` boʻyicha topiladi va oʻz rolining kabinetiga yoʻnaltiriladi. `password` faqat login va parol bilan kirish uchun kerak; ulardan kamida bittasi majburiy. `pinfl` oʻzgartirilsa, portal hisobiga bogʻlanish bekor qilinadi va sessiyalar yopiladi.\n\n**Yoʻnalish administratori** faqat oʻz yoʻnalishi xodimlarini yaratadi: rol (va bank) avtomatik ravishda uning oʻzinikidan olinadi, `permissions` — faqat oʻz huquqlaridan. `permissions` berilmasa, yaratuvchi ushbu rol uchun bera oladigan barcha huquqlar beriladi. `is_direction_admin`ni faqat Super Admin belgilaydi.",
    "Права, которые текущий пользователь может выдать сотруднику роли": "Joriy foydalanuvchi ushbu rol xodimiga bera oladigan huquqlar",
    "Для формы создания/редактирования сотрудника. Админ направления получает права "
    "своей роли, которые есть у него самого (`role_id` можно не передавать). "
    "Super Admin передаёт `role_id` и получает все права этой роли.": "Xodimni yaratish/tahrirlash shakli uchun. Yoʻnalish administratori oʻz rolidagi, oʻzida mavjud boʻlgan huquqlar roʻyxatini oladi (`role_id` berilmasligi mumkin). Super Admin `role_id`ni beradi va ushbu rolning barcha huquqlarini oladi.",
    "Параметры, с которыми YIA Portal вернул пользователя на redirect_uri.": (
        "YIA Portal foydalanuvchini redirect_uri ga qaytargan parametrlar."
    ),
    "Стабильный идентификатор пользователя портала; по умолчанию mock-<pinfl>": (
        "Portal foydalanuvchisining barqaror identifikatori; sukut boʻyicha mock-<pinfl>"
    ),
    "Тестовый вход вместо YIA Portal (только при SSO_MOCK=True).": (
        "YIA Portal oʻrniga test kirish (faqat SSO_MOCK=True boʻlganda)."
    ),
    # ---------- users ----------
    "Просмотр, поиск и фильтрация пользователей": (
        "Foydalanuvchilarni koʻrish, qidirish va filtrlash"
    ),
    "Каримова Нигора": "Karimova Nigora",
    "Оператор Фонда": "Jamgʻarma operatori",
    "Профиль пользователя": "Foydalanuvchi profili",
    "Изменение пользователя": "Foydalanuvchini oʻzgartirish",
    "Удаление пользователя": "Foydalanuvchini oʻchirish",
    "Перевод в статус «активен» / «заблокирован»": "«Faol» / «bloklangan» holatiga oʻtkazish",
    "Назначение / отзыв роли и привязка scope (банк)": (
        "Rolni tayinlash / bekor qilish va scope (bank) biriktirish"
    ),
    "Сессии пользователя (refresh-токены, последний вход)": (
        "Foydalanuvchi sessiyalari (refresh-tokenlar, oxirgi kirish)"
    ),
    "Завершить все сессии пользователя": "Foydalanuvchining barcha sessiyalarini yakunlash",
    # ---------- rbac ----------
    "Каталог ролей": "Rollar katalogi",
    "Повседневные бизнес-процессы Фонда": "Jamgʻarmaning kundalik biznes-jarayonlari",
    "Создание роли": "Rol yaratish",
    "Роль по ID с матрицей прав": "ID boʻyicha rol va ruxsatlar matritsasi",
    "Изменение роли и её разрешений по модулям": (
        "Rol va uning modullar boʻyicha ruxsatlarini oʻzgartirish"
    ),
    "Удаление роли (не системной и без пользователей)": (
        "Rolni oʻchirish (tizimli boʻlmagan va foydalanuvchisiz)"
    ),
    "Каталог прав (плоский список)": "Ruxsatlar katalogi (yassi roʻyxat)",
    "Просмотр пользователей": "Foydalanuvchilarni koʻrish",
    "Матрица прав по модулям (Create / Read / Update / Delete / Approve)": (
        "Modullar boʻyicha ruxsatlar matritsasi (Create / Read / Update / Delete / Approve)"
    ),
    "Заявки": "Arizalar",
    "Просмотр заявок": "Arizalarni koʻrish",
    # ---------- banks ----------
    "Банки для окна выбора (фильтр по типу субъекта)": (
        "Tanlash oynasi uchun banklar (subyekt turi boʻyicha filtr)"
    ),
    "Тип субъекта: YATT, MCHJ, SELF_EMPLOYED": "Subyekt turi: YATT, MCHJ, SELF_EMPLOYED",
    "АКБ «Микрокредитбанк»": "ATB «Mikrokreditbank»",
    "Добавление банка в каталог": "Katalogga bank qoʻshish",
    "Банк по ID": "ID boʻyicha bank",
    "Изменение банка и правил выбора по типу субъекта": (
        "Bank va subyekt turi boʻyicha tanlash qoidalarini oʻzgartirish"
    ),
    "Деактивация банка (история заявок сохраняется)": (
        "Bankni faolsizlantirish (arizalar tarixi saqlanadi)"
    ),
    # ---------- applications: applicant ----------
    "Алиев Али Алиевич": "Aliyev Ali Aliyevich",
    "Заявка принята и зарегистрирована.": "Ariza qabul qilindi va roʻyxatga olindi.",
    "Банк рассматривает": "Bank koʻrib chiqmoqda",
    "Ответственный сотрудник банка проводит рассмотрение.": (
        "Bankning masʼul xodimi koʻrib chiqmoqda."
    ),
    "Выбор банка заявителем (отдельный шаг черновика).": (
        "Ariza beruvchi tomonidan bank tanlash (qoralamaning alohida qadami)."
    ),
    "Сводка перед отправкой: выбранные параметры и недостающие поля": (
        "Yuborishdan oldingi xulosa: tanlangan parametrlar va yetishmayotgan maydonlar"
    ),
    "Отправить заявку: проверка обязательных полей → SUBMITTED → скоринг": (
        "Arizani yuborish: majburiy maydonlar tekshiruvi → SUBMITTED → skoring"
    ),
    "Индикатор прогресса: этапы done / active / pending / rejected": (
        "Jarayon indikatori: bosqichlar done / active / pending / rejected"
    ),
    "Заявка подана": "Ariza topshirildi",
    "Хронологическая история заявки": "Arizaning xronologik tarixi",
    "Заявка создана": "Ariza yaratildi",
    "Тип предпринимательского субъекта.": "Tadbirkorlik subyekti turi.",
    # ---------- applications: fund ----------
    "Поиск заявок по статусу, банку, дате, типу субъекта, номеру/ФИО": (
        "Arizalarni holat, bank, sana, subyekt turi, raqam/F.I.Sh. boʻyicha qidirish"
    ),
    "Счётчики главного экрана Фонда": "Jamgʻarma bosh ekrani hisoblagichlari",
    "Карточка заявки (полные данные, этапы, документы)": (
        "Ariza kartochkasi (toʻliq maʼlumotlar, bosqichlar, hujjatlar)"
    ),
    "Полные результаты скоринга KATM: по какой проверке и почему": (
        "KATM skoringining toʻliq natijalari: qaysi tekshiruv boʻyicha va nima sababdan"
    ),
    "Повторная обработка после технической ошибки KATM": (
        "KATM texnik xatosidan keyin qayta ishlash"
    ),
    "Кому направить. Пусто — всем активным членам Совета.": (
        "Kimga yoʻnaltirish. Boʻsh — barcha faol Kengash aʼzolariga."
    ),
    # ---------- applications: bank ----------
    "Заявки банка: новые / на рассмотрении / завершённые": (
        "Bank arizalari: yangi / koʻrib chiqilmoqda / yakunlangan"
    ),
    "Раздел рабочего окна": "Ish oynasi boʻlimi",
    "Счётчики рабочего окна банка": "Bank ish oynasi hisoblagichlari",
    "Принять заявку в рассмотрение (SENT_TO_BANK → BANK_REVIEW)": (
        "Arizani koʻrib chiqishga qabul qilish (SENT_TO_BANK → BANK_REVIEW)"
    ),
    "Результат банка: одобрение или отказ с причиной (изменить нельзя)": (
        "Bank natijasi: maʼqullash yoki sabab bilan rad etish (oʻzgartirib boʻlmaydi)"
    ),
    "Обязательна при отказе.": "Rad etishda majburiy.",
    # ---------- applications: council ----------
    "Направленные мне заявки (нерассмотренные — pending_only=true)": (
        "Menga yoʻnaltirilgan arizalar (koʻrib chiqilmaganlar — pending_only=true)"
    ),
    "Счётчики рабочего окна Совета": "Kengash ish oynasi hisoblagichlari",
    "Решение члена Совета: «Согласен» / «Отклоняю» (причина обязательна)": (
        "Kengash aʼzosining qarori: «Roziman» / «Rad etaman» (sabab majburiy)"
    ),
    "Обязательна при «Отклоняю».": "«Rad etaman» da majburiy.",
    "Сайт, с которого начат вход: `yoshlarfondi` — основной (`SSO_CLIENT_ID`, `SSO_REDIRECT_URI`), `admin` — админка (`SSO_CLIENT_ID_ADMIN`, `SSO_REDIRECT_URI_ADMIN`). Сайт подписывается в `state`: `POST /auth/sso/callback` меняет `code` тем же клиентом портала, а `/redirect/from-backend` возвращает браузер на фронт этого сайта.": "Kirish boshlangan sayt: `yoshlarfondi` — asosiy sayt (`SSO_CLIENT_ID`, `SSO_REDIRECT_URI`), `admin` — admin panel (`SSO_CLIENT_ID_ADMIN`, `SSO_REDIRECT_URI_ADMIN`). Sayt `state` ichida imzolanadi: `POST /auth/sso/callback` `code`ni portalning oʻsha mijozi orqali almashtiradi, `/redirect/from-backend` esa brauzerni shu saytning frontendiga qaytaradi.",
    "Фронт, на который вернуть браузер: `yoshlarfondi` — `SSO_FRONTEND_REDIRECT_URL`, `admin` — `SSO_FRONTEND_REDIRECT_URL_ADMIN`. Без параметра сайт берётся из подписанного `state` (тот, что передан в `GET /auth/sso/authorize?site=`). Сам `site` на фронт не пересылается.": "Brauzer qaytariladigan frontend: `yoshlarfondi` — `SSO_FRONTEND_REDIRECT_URL`, `admin` — `SSO_FRONTEND_REDIRECT_URL_ADMIN`. Parametr berilmasa, sayt imzolangan `state`dan olinadi (`GET /auth/sso/authorize?site=` da berilgan sayt). `site`ning oʻzi frontendga uzatilmaydi.",
    "Направить заявку в Совет (FUND_REVIEW → COUNCIL_REVIEW)": "Arizani Kengashga yoʻnaltirish (FUND_REVIEW → COUNCIL_REVIEW)",
    "Отклонить заявку до Совета (FUND_REVIEW → FUND_REJECTED)": "Arizani Kengashgacha rad etish (FUND_REVIEW → FUND_REJECTED)",
    "Причина обязательна и показывается заявителю.": "Sabab majburiy va ariza beruvchiga koʻrsatiladi.",
    "Причина отказа Фонда (видна заявителю).": "Jamgʻarmaning rad etish sababi (ariza beruvchiga koʻrinadi).",
    # ---------- продукты ----------
    "Продукты: управление (Фонд)": "Mahsulotlar: boshqaruv (Jamgʻarma)",
    "Продукты: каталог заявителя": "Mahsulotlar: ariza beruvchi katalogi",
    "Продукты, их банки, сроки приёма, этапы и поля анкеты; публикация.": "Mahsulotlar, ularning banklari, qabul muddatlari, anketa bosqichlari va maydonlari; eʼlon qilish.",
    "Опубликованные продукты, по которым сейчас принимаются заявки.": "Hozir arizalar qabul qilinayotgan eʼlon qilingan mahsulotlar.",
    "Заявка по продукту: ответы на поля этапов, файлы, отправка, отслеживание.": "Mahsulot boʻyicha ariza: bosqich maydonlariga javoblar, fayllar, yuborish, kuzatish.",
    "Молодёжный бизнес": "Yoshlar biznesi",
    "Льготный кредит для молодых предпринимателей.": "Yosh tadbirkorlar uchun imtiyozli kredit.",
    "Продукт с банками, этапами и полями": "Banklar, bosqichlar va maydonlar bilan mahsulot",
    "Сведения о проекте": "Loyiha haqida maʼlumot",
    "Запрашиваемая сумма": "Soʻralayotgan summa",
    "Фото места деятельности": "Faoliyat joyi surati",
    "Передаются только изменяемые поля. `bank_ids` заменяет список банков целиком. Разрешено и при наличии заявок.": "Faqat oʻzgaradigan maydonlar yuboriladi. `bank_ids` banklar roʻyxatini toʻliq almashtiradi. Arizalar mavjud boʻlsa ham ruxsat etiladi.",
    "Удалить продукт без заявок": "Arizasiz mahsulotni oʻchirish",
    "Продукт с заявками удалить нельзя — снимите его с публикации (`archive`).": "Arizalari bor mahsulotni oʻchirib boʻlmaydi — uni eʼlondan oling (`archive`).",
    "Опубликовать продукт (DRAFT / ARCHIVED → PUBLISHED)": "Mahsulotni eʼlon qilish (DRAFT / ARCHIVED → PUBLISHED)",
    "Нужны хотя бы один активный банк, хотя бы один этап и хотя бы одно поле в каждом этапе. Заявители видят продукт в сроках приёма.": "Kamida bitta faol bank, kamida bitta bosqich va har bir bosqichda kamida bitta maydon kerak. Ariza beruvchilar mahsulotni qabul muddatlarida koʻradi.",
    "Снять продукт с публикации (PUBLISHED → ARCHIVED)": "Mahsulotni eʼlondan olish (PUBLISHED → ARCHIVED)",
    "Новые заявки не принимаются, черновики по продукту отправить нельзя.": "Yangi arizalar qabul qilinmaydi, mahsulot boʻyicha qoralamalarni yuborib boʻlmaydi.",
    "Скопировать продукт в новый черновик (с банками, этапами и полями)": "Mahsulotdan yangi qoralamaga nusxa olish (banklar, bosqichlar va maydonlar bilan)",
    "Добавить этап: номер и название на трёх языках": "Bosqich qoʻshish: raqam va uch tildagi nom",
    "Возвращает продукт целиком. Если по продукту уже есть заявки, этапы и поля менять нельзя (`product_locked`): скопируйте продукт (`POST /fund/products/{id}/copy`).": "Mahsulotni toʻliq qaytaradi. Agar mahsulot boʻyicha arizalar boʻlsa, bosqich va maydonlarni oʻzgartirib boʻlmaydi (`product_locked`): mahsulotdan nusxa oling (`POST /fund/products/{id}/copy`).",
    "Изменить номер или название этапа": "Bosqich raqami yoki nomini oʻzgartirish",
    "Удалить этап вместе с его полями": "Bosqichni maydonlari bilan birga oʻchirish",
    "Добавить поле в этап: тип, название на трёх языках, обязательность": "Bosqichga maydon qoʻshish: tur, uch tildagi nom, majburiylik",
    "Типы: STRING (текст), NUMBER (число), DATE (дата), PHONE (+998XXXXXXXXX), EMAIL, PHOTO (JPG/PNG/WEBP), FILE (PDF/DOCX). `max_files` — только для PHOTO и FILE. Возвращает продукт целиком. Если по продукту уже есть заявки, этапы и поля менять нельзя (`product_locked`): скопируйте продукт (`POST /fund/products/{id}/copy`).": "Turlar: STRING (matn), NUMBER (son), DATE (sana), PHONE (+998XXXXXXXXX), EMAIL, PHOTO (JPG/PNG/WEBP), FILE (PDF/DOCX). `max_files` — faqat PHOTO va FILE uchun. Mahsulotni toʻliq qaytaradi. Agar mahsulot boʻyicha arizalar boʻlsa, bosqich va maydonlarni oʻzgartirib boʻlmaydi (`product_locked`): mahsulotdan nusxa oling (`POST /fund/products/{id}/copy`).",
    "Изменить поле: тип, название, обязательность, лимит файлов, порядок": "Maydonni oʻzgartirish: tur, nom, majburiylik, fayllar limiti, tartib",
    "Удалить поле": "Maydonni oʻchirish",
    "Продукты, по которым сейчас принимаются заявки": "Hozir arizalar qabul qilinayotgan mahsulotlar",
    "Продукт с этапами и полями анкеты": "Anketa bosqichlari va maydonlari bilan mahsulot",
    "Мои заявки: номер, продукт, банк, статус": "Mening arizalarim: raqam, mahsulot, bank, holat",
    "Подать заявку по продукту: создаётся номер и черновик (DRAFT)": "Mahsulot boʻyicha ariza berish: raqam va qoralama (DRAFT) yaratiladi",
    "Продукт берётся из `GET /products`: опубликован, в сроках приёма и рассчитан на `subject_type`. Данные заявителя — из профиля (`/auth/me`). Банк — из `banks` продукта, сразу (`bank_id`) или позже (`PUT /applications/{id}/bank`). Дальше заявитель заполняет этапы продукта (`PUT /applications/{id}/stages/{stage_id}`).": "Mahsulot `GET /products` dan olinadi: eʼlon qilingan, qabul muddatida va `subject_type` uchun moʻljallangan. Ariza beruvchi maʼlumotlari — profildan (`/auth/me`). Bank — mahsulotning `banks` roʻyxatidan, darhol (`bank_id`) yoki keyinroq (`PUT /applications/{id}/bank`). Soʻng ariza beruvchi mahsulot bosqichlarini toʻldiradi (`PUT /applications/{id}/stages/{stage_id}`).",
    "Карточка заявки: заявитель, продукт, ответы анкеты, этапы рассмотрения": "Ariza kartochkasi: ariza beruvchi, mahsulot, anketa javoblari, koʻrib chiqish bosqichlari",
    "Редактирование черновика: продукт или тип субъекта": "Qoralamani tahrirlash: mahsulot yoki subyekt turi",
    "Смена продукта очищает ответы анкеты, файлы и выбранный банк. Если выбранный банк не работает с новым типом субъекта, он сбрасывается.": "Mahsulot almashtirilsa, anketa javoblari, fayllar va tanlangan bank tozalanadi. Agar tanlangan bank yangi subyekt turi bilan ishlamasa, u bekor qilinadi.",
    "Удаление черновика (вместе с файлами анкеты)": "Qoralamani oʻchirish (anketa fayllari bilan birga)",
    "Выбор банка из банков продукта": "Mahsulot banklaridan bank tanlash",
    "Банк берётся из `banks` продукта (`GET /products/{id}`): он должен быть активен и работать с типом субъекта заявки. После утверждения Советом заявка автоматически уходит в этот банк.": "Bank mahsulotning `banks` roʻyxatidan olinadi (`GET /products/{id}`): u faol boʻlishi va ariza subyekti turi bilan ishlashi kerak. Kengash tasdiqlagandan soʻng ariza avtomatik ravishda shu bankka yuboriladi.",
    "Сохранить ответы этапа продукта": "Mahsulot bosqichi javoblarini saqlash",
    "`values` — словарь «id поля → значение». Меняются только переданные поля; `null` или пустая строка очищает поле. Проверка по типу: NUMBER — число, DATE — ГГГГ-ММ-ДД, PHONE — +998XXXXXXXXX, EMAIL — адрес почты. Обязательность проверяется при отправке заявки. Файлы полей PHOTO / FILE загружаются через `POST .../fields/{field_id}/files`.": "`values` — «maydon id → qiymat» lugʻati. Faqat yuborilgan maydonlar oʻzgaradi; `null` yoki boʻsh satr maydonni tozalaydi. Tur boʻyicha tekshiruv: NUMBER — son, DATE — YYYY-OO-KK, PHONE — +998XXXXXXXXX, EMAIL — pochta manzili. Majburiylik ariza yuborilganda tekshiriladi. PHOTO / FILE maydonlari fayllari `POST .../fields/{field_id}/files` orqali yuklanadi.",
    "Загрузить файл в поле PHOTO или FILE": "PHOTO yoki FILE maydoniga fayl yuklash",
    "PHOTO — JPG/PNG/WEBP до 5 МБ, FILE — PDF/DOCX до 10 МБ. Не больше `max_files` файлов на поле.": "PHOTO — JPG/PNG/WEBP 5 MB gacha, FILE — PDF/DOCX 10 MB gacha. Har bir maydonga `max_files` tadan koʻp boʻlmagan fayl.",
    "Удалить файл поля из черновика": "Qoralamadan maydon faylini oʻchirish",
    "Скачать файл поля (только для тех, кто имеет доступ к заявке)": "Maydon faylini yuklab olish (faqat arizaga ruxsati borlar uchun)",
    "Недостающие поля — те же ключи, что в `submission-check`: `product_id`, `subject_type`, `bank_id`, `fields.<id поля>` (обязательные поля этапов), `applicant.phone` … После отправки запускается скоринг; при успехе заявка поступает в Фонд (`FUND_REVIEW`), при техошибке KATM остаётся в `SCORING_IN_PROGRESS` до повтора.": "Yetishmayotgan maydonlar — `submission-check` dagi kalitlar: `product_id`, `subject_type`, `bank_id`, `fields.<maydon id>` (bosqichlarning majburiy maydonlari), `applicant.phone` … Yuborilgandan soʻng skoring boshlanadi; muvaffaqiyatli boʻlsa ariza Jamgʻarmaga tushadi (`FUND_REVIEW`), KATM texnik xatosida takrorlashgacha `SCORING_IN_PROGRESS` holatida qoladi.",
    "Продукт из `GET /products`.": "`GET /products` dagi mahsulot.",
    "Банк из `banks` продукта; можно выбрать позже (`PUT /applications/{id}/bank`).": "Mahsulotning `banks` roʻyxatidagi bank; keyinroq tanlash mumkin (`PUT /applications/{id}/bank`).",
    "Смена продукта очищает ответы анкеты и выбранный банк.": "Mahsulot almashtirilsa, anketa javoblari va tanlangan bank tozalanadi.",
    "Только для PHOTO и FILE: сколько файлов можно загрузить.": "Faqat PHOTO va FILE uchun: nechta fayl yuklash mumkin.",
    "Порядок поля внутри этапа.": "Bosqich ichidagi maydon tartibi.",
    "Для каких типов субъекта доступен продукт.": "Mahsulot qaysi subyekt turlari uchun mavjud.",
    "Начало приёма заявок (включительно).": "Arizalarni qabul qilish boshlanishi (shu kun ham).",
    "Конец приёма заявок (включительно).": "Arizalarni qabul qilish tugashi (shu kun ham).",
    "Банки, через которые работает продукт (из каталога банков).": "Mahsulot ishlaydigan banklar (banklar katalogidan).",
    "Полный список банков продукта (заменяет текущий).": "Mahsulot banklarining toʻliq roʻyxati (joriysini almashtiradi).",
    "Номер этапа (порядок).": "Bosqich raqami (tartib).",
    'Значения полей этапа: ключ — id поля, значение — строка; `null` или "" очищает поле.\nМеняются только переданные поля. Файлы (PHOTO / FILE) загружаются отдельно.': 'Bosqich maydonlari qiymatlari: kalit — maydon id, qiymat — satr; `null` yoki "" maydonni tozalaydi. Faqat yuborilgan maydonlar oʻzgaradi. Fayllar (PHOTO / FILE) alohida yuklanadi.',
    "Сайт, с которого начат вход через YIA Portal: у каждого свой клиент портала\nи свой redirect_uri.": "YIA Portal orqali kirish boshlangan sayt: har birining oʻz portal mijozi va oʻz redirect_uri si bor.",
    "Сотрудник входит через YIA Portal (по ПИНФЛ) и/или по логину и паролю:\nнужен хотя бы один из способов.": "Xodim YIA Portal orqali (JShShIR boʻyicha) va/yoki login va parol bilan kiradi: kamida bitta usul kerak.",
    "Ровно три перевода — `ru`, `uz`, `en`, каждый язык один раз. При изменении передаются все три.": "Aynan uchta tarjima — `ru`, `uz`, `en`, har bir til bir marta. Oʻzgartirishda uchalasi ham yuboriladi.",
    "Ровно три перевода — `ru`, `uz`, `en`, каждый язык один раз. При изменении передаются все три. Описание — на всех трёх языках или ни на одном.": "Aynan uchta tarjima — `ru`, `uz`, `en`, har bir til bir marta. Oʻzgartirishda uchalasi ham yuboriladi. Tavsif — uchala tilda yoki birortasida ham emas.",
    "Справочник для конструктора продукта (Фонд) и формы заявки (заявитель): какие типы полей можно добавить в этап, как их заполнять и какие ограничения у файлов. Значения `type` передаются в `field_type` при создании поля.": "Mahsulot konstruktori (Jamgʻarma) va ariza shakli (ariza beruvchi) uchun maʼlumotnoma: bosqichga qanday turdagi maydonlarni qoʻshish mumkin, ularni qanday toʻldirish kerak va fayllarga qanday cheklovlar bor. `type` qiymatlari maydon yaratishda `field_type` ga beriladi.",
    "Типы полей анкеты: названия на ru/uz/en и правила заполнения": "Anketa maydonlari turlari: ru/uz/en dagi nomlar va toʻldirish qoidalari",
    "Телефон": "Telefon",
    "Фото": "Surat",
    "`category_id` обязателен: активная категория из `GET /fund/product-categories`.": "`category_id` majburiy: `GET /fund/product-categories` dagi faol kategoriya.",
    "Все категории продуктов (с числом продуктов)": "Barcha mahsulot kategoriyalari (mahsulotlar soni bilan)",
    "Все продукты (фильтр по статусу и категории, поиск по названию)": "Barcha mahsulotlar (holat va kategoriya boʻyicha filtr, nom boʻyicha qidiruv)",
    "Изменить категорию, названия, описания, типы субъекта, сроки приёма или банки": "Kategoriya, nomlar, tavsiflar, subyekt turlari, qabul muddatlari yoki banklarni oʻzgartirish",
    "Изменить переводы, активность или порядок категории": "Kategoriya tarjimalari, faolligi yoki tartibini oʻzgartirish",
    "Категории продуктов; продукт относится к одной категории.": "Mahsulot kategoriyalari; mahsulot bitta kategoriyaga tegishli.",
    "Категории, в которых сейчас есть продукты для подачи заявки": "Hozir ariza berish mumkin boʻlgan mahsulotlari bor kategoriyalar",
    "Категорию с продуктами удалить нельзя — деактивируйте её или перенесите продукты.": "Mahsulotlari bor kategoriyani oʻchirib boʻlmaydi — uni nofaol qiling yoki mahsulotlarni koʻchiring.",
    "Категория из `GET /fund/product-categories` (активная).": "`GET /fund/product-categories` dagi kategoriya (faol).",
    "Категория из `GET /products/categories`": "`GET /products/categories` dagi kategoriya",
    "Категория по ID": "ID boʻyicha kategoriya",
    "Кредиты для бизнеса": "Biznes uchun kreditlar",
    "Неактивную категорию нельзя выбрать для продукта, а её продукты перестают быть видны заявителям и не принимают заявки.": "Nofaol kategoriyani mahsulot uchun tanlab boʻlmaydi, uning mahsulotlari esa ariza beruvchilarga koʻrinmaydi va arizalar qabul qilmaydi.",
    "Неактивную категорию нельзя выбрать для продукта; её продукты не видны заявителям.": "Nofaol kategoriyani mahsulot uchun tanlab boʻlmaydi; uning mahsulotlari ariza beruvchilarga koʻrinmaydi.",
    "Опубликованные продукты активных категорий в сроках приёма. С `subject_type` — только продукты для этого типа субъекта, с `category_id` — только этой категории. В `banks` — только активные банки продукта.": "Qabul muddatidagi faol kategoriyalarning eʼlon qilingan mahsulotlari. `subject_type` bilan — faqat shu subyekt turi uchun, `category_id` bilan — faqat shu kategoriya mahsulotlari. `banks` da — mahsulotning faqat faol banklari.",
    "Перенос в другую активную категорию.": "Boshqa faol kategoriyaga koʻchirish.",
    "Порядок в списке категорий.": "Kategoriyalar roʻyxatidagi tartib.",
    "Продукты: категории (Фонд)": "Mahsulotlar: kategoriyalar (Jamgʻarma)",
    "Создать категорию: название (и описание) на ru / uz / en": "Kategoriya yaratish: ru / uz / en dagi nom (va tavsif)",
    "Создать продукт (черновик): категория, названия, описания, типы субъекта, сроки, банки": "Mahsulot yaratish (qoralama): kategoriya, nomlar, tavsiflar, subyekt turlari, muddatlar, banklar",
    "Только активные категории; `products_count` — сколько продуктов категории сейчас принимают заявки (с `subject_type` — для этого типа субъекта).": "Faqat faol kategoriyalar; `products_count` — kategoriyaning nechta mahsuloti hozir ariza qabul qilmoqda (`subject_type` bilan — shu subyekt turi uchun).",
    "Удалить категорию без продуктов": "Mahsulotsiz kategoriyani oʻchirish",
    "Без авторизации.": "Avtorizatsiyasiz.",
    "Без авторизации. ИП и ООО — все 9 банков; самозанятым — только Microcreditbank, Xalq banki и Agrobank.": "Avtorizatsiyasiz. YaTT va MChJ uchun — barcha 9 ta bank; oʻzini oʻzi band qilganlarga — faqat Microcreditbank, Xalq banki va Agrobank.",
}

_CYRILLIC = re.compile(r"[А-Яа-яЁё]")


def _translate(node: Any, table: dict[str, str]) -> Any:
    if isinstance(node, str):
        return table.get(node, node)
    if isinstance(node, dict):
        return {key: _translate(value, table) for key, value in node.items()}
    if isinstance(node, list):
        return [_translate(item, table) for item in node]
    return node


def translate_openapi(
    spec: dict, table: dict[str, str] = UZ, description: str | None = None
) -> dict:
    """Возвращает копию OpenAPI-схемы с переведёнными строками."""
    translated = _translate(copy.deepcopy(spec), table)
    if description is not None:
        translated.setdefault("info", {})["description"] = description
    return translated


def untranslated(spec: dict) -> list[tuple[str, str]]:
    """Строки с кириллицей, оставшиеся в схеме (путь, строка) — для самопроверки."""
    found: list[tuple[str, str]] = []

    def walk(node: Any, path: str) -> None:
        if path == ".info.description":
            return  # пишется вручную целиком (содержит слово «Русский» в примечании о языке)
        if isinstance(node, str):
            if _CYRILLIC.search(node):
                found.append((path, node))
        elif isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    walk(spec, "")
    return found
