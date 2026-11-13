"""Пересоздать продукт «Строительство, ремонт и оснащение зданий, сырьё и оборудование»

Revision ID: c8e0a2b4d6f8
Revises: b7d9f1a3c5e7
Create Date: 2026-11-13

Data-миграция (docx products/01_Bino_qurish_tamirlash_xomashyo_uskuna_qarz.docx). Если
продукта с таким русским названием нет (например, его удалили на сервере), он создаётся
заново черновиком (DRAFT) — со всеми этапами, полями, вариантами ответа и условиями показа:

- этап 1: сумма, срок займа, «Цель займа» (CHECKBOX, 6 вариантов), заявление;
- этапы 2–3: общие документы и залог;
- этапы 4–9 показываются только при выбранной цели займа;
- этап 9: «Оборудование или технологии импортируются?» (RADIO Да / Нет), импортные
  документы видны только при «Да».

Категория «Займы и ссуды» ищется по русскому названию; если её нет, она создаётся.
Банки не привязываются: их выбирает Фонд перед публикацией (без банка опубликовать нельзя).
Если продукт с таким названием уже есть, миграция ничего не делает.
Downgrade ничего не делает: продукт удаляется через API Фонда, если по нему нет заявок.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8e0a2b4d6f8"
down_revision: Union[str, Sequence[str], None] = "b7d9f1a3c5e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LANGUAGES = ("ru", "uz", "en")

CATEGORY = {
    "names": ("Займы и ссуды", "Qarzlar va ssudalar", "Loans"),
    "descriptions": (
        "Займы и беспроцентные ссуды Фонда (Положение, глава 3).",
        "Jamgʻarmaning qarzlari va foizsiz ssudalari (Nizom, 3-bob).",
        "Fund loans and interest-free loans (Regulation, chapter 3).",
    ),
    "sort_order": 1,
}

PRODUCT = {
    "names": (
        "Строительство, ремонт и оснащение зданий, сырьё и оборудование",
        "Bino qurish, taʼmirlash va jihozlash, xomashyo va uskuna",
        "Construction, repair and equipping of buildings, raw materials and equipment",
    ),
    "descriptions": (
        "Заём до 10 000 БРВ на строительство, ремонт и оснащение зданий и сооружений, покупку "
        "зданий, сырья для производства, технологий и оборудования. Положение: глава 3, § 2.",
        "Bino va inshootlarni qurish, taʼmirlash va jihozlash, bino, ishlab chiqarish uchun "
        "xomashyo, texnologiya va asbob-uskuna sotib olish uchun 10 ming BHMgacha qarz. "
        "Nizom: 3-bob, 2-§.",
        "Loan of up to 10,000 BCU for construction, repair and equipping of buildings, purchase "
        "of buildings, production raw materials, technology and equipment. "
        "Regulation: chapter 3, § 2.",
    ),
    "allowed_subject_types": ["MCHJ"],
}


def stage(number: int, names: tuple, fields: list, when: tuple | None = None) -> dict:
    """Этап; `when` = (ru-название управляющего поля, (ru-названия вариантов,))."""
    return {"number": number, "names": names, "fields": fields, "when": when}


def field(
    field_type: str,
    names: tuple,
    required: bool = True,
    max_files: int = 1,
    options: tuple = (),
    when: tuple | None = None,
) -> dict:
    """Поле этапа; порядок (`sort_order`) — позиция в списке этапа."""
    return {
        "type": field_type,
        "names": names,
        "required": required,
        "max_files": max_files,
        "options": options,
        "when": when,
    }


STAGES = [
    stage(
        1,
        ("Заявление и сумма", "Ariza va summa", "Application and amount"),
        fields=[
            field(
                "NUMBER",
                ("Запрашиваемая сумма, сум", "Soʻralayotgan summa, soʻm", "Requested amount, UZS"),
            ),
            field("NUMBER", ("Срок займа, месяцев", "Qarz muddati, oy", "Loan term, months")),
            field(
                "CHECKBOX",
                ("Цель займа", "Qarz maqsadi", "Loan purpose"),
                options=(
                    ("Строительство", "Qurilish", "Construction"),
                    ("Ремонт", "Taʼmirlash", "Repair"),
                    ("Оснащение", "Jihozlash", "Equipping"),
                    (
                        "Покупка здания или сооружения",
                        "Bino yoki inshoot sotib olish",
                        "Purchase of a building",
                    ),
                    (
                        "Покупка сырья для производства",
                        "Ishlab chiqarish uchun xomashyo sotib olish",
                        "Purchase of raw materials",
                    ),
                    (
                        "Покупка технологий и оборудования",
                        "Texnologiya va asbob-uskuna sotib olish",
                        "Purchase of technology and equipment",
                    ),
                ),
            ),
            field(
                "FILE",
                (
                    "Заявление в Фонд (с указанием суммы; подпись руководителя, печать при наличии)",
                    "Jamgʻarmaga ariza (soʻralayotgan summa koʻrsatilgan; rahbar imzosi, muhr mavjud boʻlsa)",
                    "Application to the Fund (stating the amount; signed by the head, sealed if applicable)",
                ),
            ),
        ],
    ),
    stage(
        2,
        ("Общие документы", "Umumiy hujjatlar", "General documents"),
        fields=[
            field(
                "FILE",
                (
                    "Письменное согласие на получение Фондом сведений о заявителе из госорганов",
                    "Jamgʻarma davlat organlaridan tashabbuskor haqida maʼlumot olishiga yozma rozilik",
                    "Written consent for the Fund to obtain information about the applicant from state bodies",
                ),
            ),
            field(
                "FILE",
                (
                    "Подтверждение отсутствия аффилированности с Агентством, членами Совета, Фондом и Yoshlar ventures",
                    "Agentlik, Kengash aʼzolari, Jamgʻarma va Yoshlar ventures bilan affillanganlik yoʻqligi tasdigʻi",
                    "Confirmation of no affiliation with the Agency, Council members, the Fund and Yoshlar ventures",
                ),
            ),
            field(
                "FILE",
                (
                    "Учредительные документы (устав, учредительный договор; при одном учредителе — устав)",
                    "Taʼsis hujjatlari (ustav, taʼsis shartnomasi; yagona taʼsischida — ustav)",
                    "Founding documents (charter, founders' agreement; charter only for a sole founder)",
                ),
            ),
            field(
                "FILE",
                (
                    "Свидетельство о государственной регистрации",
                    "Davlat roʻyxatidan oʻtganlik guvohnomasi",
                    "State registration certificate",
                ),
            ),
            field(
                "FILE",
                (
                    "Приказ о назначении руководителя, паспорт или ID-карта руководителя",
                    "Rahbarni tayinlash toʻgʻrisida buyruq, rahbarning pasporti yoki ID-kartasi",
                    "Order appointing the head, head's passport or ID card",
                ),
            ),
            field(
                "FILE",
                (
                    "Решение учредителей о получении займа (если сделка > 25% чистых активов или по уставу)",
                    "Qarz olish boʻyicha taʼsischilar qarori (bitim sof aktivlarning 25% dan oshsa yoki ustav talab qilsa)",
                    "Founders' decision to borrow (if the deal exceeds 25% of net assets or the charter requires)",
                ),
                required=False,
            ),
            field(
                "FILE",
                (
                    "Технико-экономическое обоснование или бизнес-план проекта",
                    "Loyihaning texnik-iqtisodiy asoslanishi yoki biznes-reja",
                    "Feasibility study or business plan of the project",
                ),
            ),
            field(
                "FILE",
                (
                    "Финансовая отчётность за последний отчётный период (формы 1 и 2)",
                    "Oxirgi hisobot davridagi moliyaviy hisobot (1-shakl, 2-shakl)",
                    "Financial statements for the last reporting period (forms 1 and 2)",
                ),
            ),
            field(
                "FILE",
                (
                    "Кадастровый документ или договор аренды помещения по месту деятельности",
                    "Faoliyat joyi binosining kadastr hujjati yoki ijara shartnomasi",
                    "Cadastre document or lease agreement for the business premises",
                ),
            ),
            field(
                "FILE",
                (
                    "Паспорта или ID-карты учредителей-молодёжи (18–30 лет)",
                    "Taʼsischi yosh fuqarolarning pasporti yoki ID-kartasi (18–30 yosh)",
                    "Passports or ID cards of young founders (aged 18–30)",
                ),
                required=False,
                max_files=5,
            ),
            field(
                "FILE",
                (
                    "План трудоустройства: число рабочих мест, не менее 50% — молодёжь",
                    "Ishga joylashtirish rejasi: ish oʻrinlari soni, kamida 50 foizi yoshlar",
                    "Employment plan: number of jobs, at least 50% for young people",
                ),
                required=False,
            ),
            field(
                "FILE",
                (
                    "Показатель рейтинга устойчивости",
                    "Barqarorlik reytingi koʻrsatkichi",
                    "Sustainability rating",
                ),
            ),
            field(
                "FILE",
                (
                    "Справка кредитного бюро «Кредитно-информационный аналитический центр» (КАТМ)",
                    "“Kredit-axborot tahliliy markazi” kredit byurosi maʼlumotnomasi (KATM)",
                    "Credit bureau report of the Credit Information Analytical Centre (KATM)",
                ),
            ),
            field(
                "FILE",
                (
                    "Согласие на получение кредитного отчёта (дата, пользователь и цель)",
                    "Kredit hisobotini olishga rozilik (sana, foydalanuvchi va maqsad koʻrsatilgan)",
                    "Consent to obtain the credit report (date, user and purpose stated)",
                ),
            ),
            field(
                "FILE",
                (
                    "Справка о банковском счёте",
                    "Hisobvaraq toʻgʻrisida maʼlumotnoma",
                    "Bank account certificate",
                ),
            ),
        ],
    ),
    stage(
        3,
        (
            "Залог (не менее 125% суммы займа)",
            "Garov taʼminoti (qarz summasining kamida 125 foizi)",
            "Collateral (at least 125% of the loan)",
        ),
        fields=[
            field(
                "FILE",
                (
                    "Кадастровые документы или технический паспорт недвижимости",
                    "Koʻchmas mulk kadastr hujjatlari yoki texnik pasport",
                    "Cadastre documents or technical passport of the real estate",
                ),
                max_files=3,
            ),
            field(
                "FILE",
                (
                    "Свидетельство о регистрации права на здание и участок или выписка из реестра",
                    "Bino, inshoot va yer uchastkasiga huquq guvohnomasi yoki reestrdan koʻchirma",
                    "Title registration certificate for the building and land or registry extract",
                ),
            ),
            field(
                "FILE",
                (
                    "Решение учредителей о передаче имущества в залог",
                    "Garovga taqdim etish boʻyicha taʼsischilar qarori",
                    "Founders' decision to pledge the property",
                ),
            ),
            field(
                "FILE",
                (
                    "Согласие всех собственников (если залог — общая совместная собственность), нотариально",
                    "Umumiy birgalikdagi mulk garovga berilsa, barcha mulkdorlarning roziligi (notarius orqali)",
                    "Consent of all co-owners if the pledge is joint property (notarised)",
                ),
                required=False,
            ),
            field(
                "FILE",
                (
                    "Отчёт независимого оценщика о рыночной стоимости",
                    "Bozor bahosi boʻyicha mustaqil baholovchining hisoboti",
                    "Independent appraiser's market value report",
                ),
            ),
            field(
                "PHOTO",
                (
                    "Фото залога снаружи и внутри с 4 сторон",
                    "Garovning ichki va tashqi 4 tomonlama fotosuratlari",
                    "Photos of the pledged property inside and outside from 4 sides",
                ),
                max_files=8,
            ),
            field(
                "FILE",
                (
                    "Если залог — транспорт: техпаспорт и страховой полис",
                    "Garov transport vositasi boʻlsa: guvohnoma nusxasi va sugʻurta polisi",
                    "If the pledge is a vehicle: registration certificate and insurance policy",
                ),
                required=False,
                max_files=2,
            ),
        ],
    ),
    stage(
        4,
        ("Для строительства", "Qurilish uchun", "For construction"),
        when=("Цель займа", ("Строительство",)),
        fields=[
            field(
                "FILE",
                (
                    "Право на земельный участок (договор по итогам аукциона, выписка) или кадастр здания",
                    "Yer uchastkasiga huquq (auksion shartnomasi, reestrdan koʻchirma) yoki bino kadastri",
                    "Land right (auction contract, registry extract) or building cadastre",
                ),
                max_files=2,
            ),
            field(
                "FILE",
                (
                    "Проекты объекта строительства",
                    "Qurilish obyekti loyihalari",
                    "Construction project designs",
                ),
                max_files=3,
            ),
            field(
                "FILE",
                (
                    "Проектно-сметная документация и заключение экспертизы",
                    "Loyiha-smeta hujjatlari va ekspertiza xulosasi",
                    "Design and estimate documents with expert opinion",
                ),
                max_files=3,
            ),
            field(
                "FILE",
                (
                    "Сведения о регистрации объекта для начала строительно-монтажных работ",
                    "Qurilish-montaj ishlarini boshlash uchun obyekt roʻyxatdan oʻtgani haqida maʼlumot",
                    "Registration of the site to start construction works",
                ),
            ),
            field(
                "FILE",
                (
                    "Договор с подрядчиком",
                    "Loyiha tashabbuskori va pudratchi oʻrtasidagi shartnoma",
                    "Contract with the contractor",
                ),
            ),
            field(
                "FILE",
                (
                    "Юридическое заключение о соответствии договора законодательству (при необходимости — ценовая экспертиза)",
                    "Shartnomaning qonunchilikka muvofiqligi yuzasidan yuridik xulosa (zarur hollarda narx ekspertizasi)",
                    "Legal opinion on the contract's compliance with the law (price expertise if needed)",
                ),
            ),
        ],
    ),
    stage(
        5,
        ("Для ремонта", "Taʼmirlash uchun", "For repair"),
        when=("Цель займа", ("Ремонт",)),
        fields=[
            field(
                "FILE",
                (
                    "Кадастр или договор аренды ремонтируемого объекта (если это не место деятельности)",
                    "Taʼmirlanadigan obyektning kadastri yoki ijara shartnomasi (faoliyat joyidan boshqa boʻlsa)",
                    "Cadastre or lease of the repaired property (if not the business premises)",
                ),
                required=False,
            ),
            field(
                "FILE",
                (
                    "Смета ремонтных работ (при необходимости — с заключением экспертизы)",
                    "Taʼmirlash ishlarining smeta hujjatlari (zarur hollarda ekspertiza xulosasi bilan)",
                    "Repair cost estimate (with expert opinion if needed)",
                ),
                max_files=2,
            ),
            field(
                "FILE",
                (
                    "Разрешение, если работы его требуют",
                    "Ruxsat talab qilinadigan ishlarda ruxsat maʼlumoti",
                    "Permit, if the works require it",
                ),
                required=False,
            ),
            field(
                "FILE",
                (
                    "Договор с исполнителем работ",
                    "Loyiha tashabbuskori va ish bajaruvchi oʻrtasidagi shartnoma",
                    "Contract with the works contractor",
                ),
            ),
            field(
                "FILE",
                (
                    "Юридическое заключение о соответствии договора законодательству (при необходимости — ценовая экспертиза)",
                    "Shartnomaning qonunchilikka muvofiqligi yuzasidan yuridik xulosa (zarur hollarda narx ekspertizasi)",
                    "Legal opinion on the contract's compliance with the law (price expertise if needed)",
                ),
            ),
        ],
    ),
    stage(
        6,
        ("Для оснащения", "Jihozlash uchun", "For equipping"),
        when=("Цель займа", ("Оснащение",)),
        fields=[
            field(
                "FILE",
                (
                    "Перечень и стоимость закупаемого оборудования (спецификация)",
                    "Sotib olinadigan jihozlar roʻyxati va qiymati (spetsifikatsiya)",
                    "List and cost of the equipment to buy (specification)",
                ),
            ),
            field(
                "FILE",
                (
                    "Договор с поставщиком",
                    "Yetkazib beruvchi bilan shartnoma",
                    "Contract with the supplier",
                ),
            ),
            field(
                "FILE",
                (
                    "Юридическое заключение о соответствии договора законодательству (при необходимости — ценовая экспертиза)",
                    "Shartnomaning qonunchilikka muvofiqligi yuzasidan yuridik xulosa (zarur hollarda narx ekspertizasi)",
                    "Legal opinion on the contract's compliance with the law (price expertise if needed)",
                ),
            ),
            field(
                "FILE",
                (
                    "3 коммерческих предложения от разных организаций (одно — от поставщика по договору)",
                    "Turli tashkilotlardan 3 ta tijorat taklifi (biri shartnoma imzolangan korxonadan)",
                    "3 commercial offers from different companies (one from the contracted supplier)",
                ),
                max_files=3,
            ),
        ],
    ),
    stage(
        7,
        ("Для покупки здания", "Bino sotib olish uchun", "For buying a building"),
        when=("Цель займа", ("Покупка здания или сооружения",)),
        fields=[
            field(
                "FILE",
                (
                    "Кадастровые документы приобретаемой недвижимости",
                    "Sotib olinayotgan koʻchmas mulkning kadastr hujjatlari",
                    "Cadastre documents of the property being bought",
                ),
                max_files=2,
            ),
            field(
                "FILE",
                (
                    "Справка районного отдела архитектуры о том, что объект не подлежит сносу",
                    "Tuman arxitektura boʻlimidan koʻchmas mulk buzilmasligi toʻgʻrisida maʼlumotnoma",
                    "District architecture office certificate that the property is not to be demolished",
                ),
            ),
            field(
                "FILE",
                (
                    "Договор купли-продажи недвижимости",
                    "Koʻchmas mulk oldi-sotdi shartnomasi",
                    "Real estate purchase agreement",
                ),
            ),
        ],
    ),
    stage(
        8,
        ("Для покупки сырья", "Xomashyo sotib olish uchun", "For buying raw materials"),
        when=("Цель займа", ("Покупка сырья для производства",)),
        fields=[
            field(
                "FILE",
                (
                    "Договор купли-продажи с поставщиком сырья",
                    "Xomashyo yetkazib beruvchi bilan oldi-sotdi shartnomasi",
                    "Purchase agreement with the raw material supplier",
                ),
            ),
            field(
                "FILE",
                (
                    "Юридическое заключение о соответствии договора законодательству (при необходимости — ценовая экспертиза)",
                    "Shartnomaning qonunchilikka muvofiqligi yuzasidan yuridik xulosa (zarur hollarda narx ekspertizasi)",
                    "Legal opinion on the contract's compliance with the law (price expertise if needed)",
                ),
            ),
        ],
    ),
    stage(
        9,
        (
            "Для покупки технологий и оборудования",
            "Texnologiya va asbob-uskuna sotib olish uchun",
            "For buying technology and equipment",
        ),
        when=("Цель займа", ("Покупка технологий и оборудования",)),
        fields=[
            field(
                "FILE",
                (
                    "Договор с поставщиком (с приложением)",
                    "Yetkazib beruvchi bilan shartnoma (ilovasi bilan)",
                    "Contract with the supplier (with annex)",
                ),
                max_files=2,
            ),
            field(
                "FILE",
                (
                    "Юридическое заключение о соответствии договора законодательству (при необходимости — ценовая экспертиза)",
                    "Shartnomaning qonunchilikka muvofiqligi yuzasidan yuridik xulosa (zarur hollarda narx ekspertizasi)",
                    "Legal opinion on the contract's compliance with the law (price expertise if needed)",
                ),
            ),
            field(
                "FILE",
                (
                    "3 коммерческих предложения от разных организаций (одно — от поставщика по договору)",
                    "Turli tashkilotlardan 3 ta tijorat taklifi (biri shartnoma imzolangan korxonadan)",
                    "3 commercial offers from different companies (one from the contracted supplier)",
                ),
                max_files=3,
            ),
            field(
                "RADIO",
                (
                    "Оборудование или технологии импортируются?",
                    "Uskuna yoki texnologiya import qilinadimi?",
                    "Is the equipment or technology imported?",
                ),
                options=(("Да", "Ha", "Yes"), ("Нет", "Yoʻq", "No")),
            ),
            field(
                "FILE",
                (
                    "При импорте: подписанный импортный контракт со спецификацией",
                    "Import qilinganda: toʻliq imzolangan import shartnomasi, spetsifikatsiyasi bilan",
                    "If imported: signed import contract with specification",
                ),
                max_files=2,
                when=("Оборудование или технологии импортируются?", ("Да",)),
            ),
            field(
                "FILE",
                (
                    "При импорте: ценовая экспертиза импортного контракта",
                    "Import qilinganda: import shartnomasiga narx boʻyicha ekspertiza xulosasi",
                    "If imported: price expertise of the import contract",
                ),
                when=("Оборудование или технологии импортируются?", ("Да",)),
            ),
            field(
                "FILE",
                (
                    "При импорте: заключение областного отдела внешнеэкономической деятельности",
                    "Import qilinganda: viloyat tashqi iqtisodiy faoliyat boʻlimining xulosasi",
                    "If imported: opinion of the regional foreign economic activity department",
                ),
                when=("Оборудование или технологии импортируются?", ("Да",)),
            ),
            field(
                "FILE",
                (
                    "При импорте: таможенная грузовая декларация (ГТД) с актом приёма-передачи (после ввоза товара)",
                    "Import qilinganda: bojxona yuk deklaratsiyasi (BYUD) nusxasi, topshirish-qabul qilish dalolatnomasi bilan (tovar olib kirilgandan soʻng)",
                    "If imported: customs cargo declaration with the acceptance certificate (after the goods arrive)",
                ),
                required=False,
                max_files=2,
                when=("Оборудование или технологии импортируются?", ("Да",)),
            ),
        ],
    ),
]


def _log(message: str) -> None:
    print(f"[construction loan product] {message}")


def _insert(conn, sql: str, **params) -> int:
    return conn.execute(sa.text(sql + " RETURNING id"), params).scalar_one()


def _translations(
    conn, table: str, owner: str, owner_id: int, names: tuple, descriptions=None
) -> None:
    for index, language in enumerate(LANGUAGES):
        values = {"owner_id": owner_id, "language": language, "name": names[index]}
        columns = f"{owner}, language, name"
        placeholders = ":owner_id, CAST(:language AS language), :name"
        if descriptions is not None:
            columns += ", description"
            placeholders += ", :description"
            values["description"] = descriptions[index]
        conn.execute(sa.text(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"), values)


def _category_id(conn) -> int:
    found = conn.execute(
        sa.text(
            "SELECT category_id FROM product_category_translations "
            "WHERE language = 'ru' AND name = :name ORDER BY category_id LIMIT 1"
        ),
        {"name": CATEGORY["names"][0]},
    ).scalar()
    if found is not None:
        return found
    category_id = _insert(
        conn,
        "INSERT INTO product_categories (is_active, sort_order) VALUES (true, :sort_order)",
        sort_order=CATEGORY["sort_order"],
    )
    _translations(
        conn,
        "product_category_translations",
        "category_id",
        category_id,
        CATEGORY["names"],
        CATEGORY["descriptions"],
    )
    _log(f"category {category_id} created")
    return category_id


def upgrade() -> None:
    conn = op.get_bind()
    existing = conn.execute(
        sa.text(
            "SELECT product_id FROM product_translations "
            "WHERE language = 'ru' AND name = :name ORDER BY product_id LIMIT 1"
        ),
        {"name": PRODUCT["names"][0]},
    ).scalar()
    if existing is not None:
        _log(f"product {existing} already exists, skipped")
        return

    product_id = _insert(
        conn,
        "INSERT INTO products (status, allowed_subject_types, category_id) "
        "VALUES ('DRAFT', CAST(:types AS varchar[]), :category_id)",
        types=PRODUCT["allowed_subject_types"],
        category_id=_category_id(conn),
    )
    _translations(
        conn,
        "product_translations",
        "product_id",
        product_id,
        PRODUCT["names"],
        PRODUCT["descriptions"],
    )

    # ru-название поля с вариантами → (id поля, {ru-название варианта: id}) — для условий
    controllers: dict[str, tuple[int, dict[str, int]]] = {}

    def condition(when: tuple | None) -> tuple[int | None, list[int] | None]:
        if when is None:
            return None, None
        field_id, options = controllers[when[0]]
        return field_id, [options[name] for name in when[1]]

    for item in STAGES:
        condition_field_id, option_ids = condition(item["when"])
        stage_id = _insert(
            conn,
            "INSERT INTO product_stages "
            "(product_id, number, condition_field_id, condition_option_ids) "
            "VALUES (:product_id, :number, :field_id, CAST(:option_ids AS integer[]))",
            product_id=product_id,
            number=item["number"],
            field_id=condition_field_id,
            option_ids=option_ids,
        )
        _translations(conn, "product_stage_translations", "stage_id", stage_id, item["names"])
        for sort_order, spec in enumerate(item["fields"]):
            condition_field_id, option_ids = condition(spec["when"])
            field_id = _insert(
                conn,
                "INSERT INTO product_fields (stage_id, field_type, is_required, max_files, "
                "sort_order, condition_field_id, condition_option_ids) "
                "VALUES (:stage_id, CAST(:field_type AS product_field_type), :required, "
                ":max_files, :sort_order, :field_id, CAST(:option_ids AS integer[]))",
                stage_id=stage_id,
                field_type=spec["type"],
                required=spec["required"],
                max_files=spec["max_files"],
                sort_order=sort_order,
                field_id=condition_field_id,
                option_ids=option_ids,
            )
            _translations(conn, "product_field_translations", "field_id", field_id, spec["names"])
            if not spec["options"]:
                continue
            options = {}
            for option_order, names in enumerate(spec["options"]):
                option_id = _insert(
                    conn,
                    "INSERT INTO product_field_options (field_id, sort_order) "
                    "VALUES (:field_id, :sort_order)",
                    field_id=field_id,
                    sort_order=option_order,
                )
                _translations(
                    conn, "product_field_option_translations", "option_id", option_id, names
                )
                options[names[0]] = option_id
            controllers[spec["names"][0]] = (field_id, options)
    _log(f"product {product_id} created")


def downgrade() -> None:
    # Продукт удаляется через API Фонда (DELETE /fund/products/{id}), если по нему нет заявок.
    pass
