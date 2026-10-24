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
- **application** — arizalar: qoralama → KATM skoringi → bank → Kengash → talab hujjati → mablagʻ ajratish.

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
    "Создание, заполнение, отправка и отслеживание заявки.": (
        "Arizani yaratish, toʻldirish, yuborish va kuzatish."
    ),
    "Поиск, скоринг, направление в Совет, финансирование.": (
        "Qidiruv, skoring, Kengashga yoʻnaltirish, moliyalashtirish."
    ),
    "Приём и результат по заявкам своего банка.": (
        "Oʻz banki arizalarini qabul qilish va natija kiritish."
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
    "Все данные заявителя заполнены — можно создавать заявку.": (
        "Ariza beruvchining barcha maʼlumotlari toʻldirilgan — ariza yaratish mumkin."
    ),
    "Поля профиля, которые нужно дополнить перед подачей заявки.": (
        "Ariza berishdan oldin toʻldirilishi kerak boʻlgan profil maydonlari."
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
    "Администратор": "Administrator",
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
    "YIA SSO (только заявители): обмен code на токены, профиль определяется или создаётся": (
        "YIA SSO (faqat ariza beruvchilar): code ni tokenlarga almashtirish, "
        "profil aniqlanadi yoki yaratiladi"
    ),
    "Фронтенд передаёт сюда `code`, `state` и `error` из query-параметров redirect_uri. "
    "`code` одноразовый и живёт 60 секунд — вызывать сразу после редиректа.": (
        "Frontend bu yerga redirect_uri query-parametrlaridagi `code`, `state` va `error`ni "
        "uzatadi. `code` bir martalik va 60 soniya amal qiladi — redirektdan soʻng darhol chaqiring."
    ),
    "YIA SSO (тест, только заявители): вход с ручными данными — при SSO_MOCK=True": (
        "YIA SSO (test, faqat ariza beruvchilar): qoʻlda kiritilgan maʼlumotlar bilan kirish — "
        "SSO_MOCK=True boʻlganda"
    ),
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
    "Создание внутреннего пользователя (логин + пароль + роль)": (
        "Ichki foydalanuvchi yaratish (login + parol + rol)"
    ),
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
    "ИП и ООО — все 9 банков; самозанятым — только Microcreditbank, Xalq banki и Agrobank.": (
        "YaTT va MChJ — barcha 9 ta bank; oʻzini oʻzi band qilganlar uchun — "
        "faqat Microcreditbank, Xalq banki va Agrobank."
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
    "Мои заявки: номер, дата, банк, статус": "Mening arizalarim: raqam, sana, bank, holat",
    "ИП Алиев": "YaTT Aliyev",
    "Алиев Али Алиевич": "Aliyev Ali Aliyevich",
    "Подать заявку: создаётся номер и черновик (DRAFT)": (
        "Ariza berish: raqam va qoralama (DRAFT) yaratiladi"
    ),
    "Карточка заявки: данные, место деятельности, фото, этапы": (
        "Ariza kartochkasi: maʼlumotlar, faoliyat joyi, suratlar, bosqichlar"
    ),
    "Редактирование черновика: тип субъекта, юр. наименование, банк": (
        "Qoralamani tahrirlash: subyekt turi, yuridik nomi, bank"
    ),
    "При смене типа субъекта банк, не подходящий новому типу, сбрасывается.": (
        "Subyekt turi oʻzgarganda yangi turga mos kelmaydigan bank bekor qilinadi."
    ),
    "Удаление черновика": "Qoralamani oʻchirish",
    "Место осуществления деятельности (не текущее местоположение!)": (
        "Faoliyat amalga oshiriladigan joy (joriy joylashuv emas!)"
    ),
    "Отправка заявки невозможна без confirmed=true.": (
        "confirmed=true boʻlmasa arizani yuborib boʻlmaydi."
    ),
    "Ташкент": "Toshkent",
    "Прикрепить фотографию (максимум 4; JPG/PNG/WEBP)": (
        "Surat biriktirish (koʻpi bilan 4 ta; JPG/PNG/WEBP)"
    ),
    "Удалить фотографию черновика": "Qoralama suratini oʻchirish",
    "Файл фотографии (только для тех, кто имеет доступ к заявке)": (
        "Surat fayli (faqat arizaga kirish huquqi borlar uchun)"
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
    "Пользователь подтвердил, что это место деятельности, а не текущее местоположение.": (
        "Foydalanuvchi bu faoliyat joyi ekanini, joriy joylashuv emasligini tasdiqladi."
    ),
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
    "Внести результат скоринга вручную (режим manual)": (
        "Skoring natijasini qoʻlda kiritish (manual rejimi)"
    ),
    "Направить заявку в Совет (BANK_APPROVED → COUNCIL_REVIEW)": (
        "Arizani Kengashga yoʻnaltirish (BANK_APPROVED → COUNCIL_REVIEW)"
    ),
    "Зафиксировать выделение ресурсов (после документа «Требование подтверждено»)": (
        "Mablagʻ ajratilganini qayd etish («Talab tasdiqlangan» hujjatidan keyin)"
    ),
    "Завершить заявку (RESOURCE_ALLOCATION → COMPLETED)": (
        "Arizani yakunlash (RESOURCE_ALLOCATION → COMPLETED)"
    ),
    "Результат проверки требований Фонда. Нужен только при result=PASSED.": (
        "Jamgʻarma talablari tekshiruvi natijasi. Faqat result=PASSED boʻlganda kerak."
    ),
    "Просроченная задолженность > 90 дней": "Muddati oʻtgan qarzdorlik > 90 kun",
    "Ручное внесение результата KATM (режим manual или после техошибки).": (
        "KATM natijasini qoʻlda kiritish (manual rejimi yoki texnik xatodan keyin)."
    ),
    "Кому направить. Пусто — всем активным членам Совета.": (
        "Kimga yoʻnaltirish. Boʻsh — barcha faol Kengash aʼzolariga."
    ),
    # ---------- applications: bank ----------
    "Заявки банка: новые / на рассмотрении / завершённые": (
        "Bank arizalari: yangi / koʻrib chiqilmoqda / yakunlangan"
    ),
    "Раздел рабочего окна": "Ish oynasi boʻlimi",
    "ООО «Навруз»": "«Navroʻz» MChJ",
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
