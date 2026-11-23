"""Все 16 продуктов Фонда из `products/`: категории, этапы, поля, варианты, условия

Revision ID: b7d9f1a3c5e6
Revises: a6c8e0f2b4d5
Create Date: 2026-11-24

Data-миграция по перечням документов (docx в `products/`, Положение Фонда):

- «Займы и ссуды» — 01 строительство и оснащение, 02 центр иностранных языков, 03 стартап-студии,
  04 «Янги авлод тадбиркорлари», 05 Book cafe, 06 мастерские-лаборатории, 07 передвижные магазины;
- «Возмещение расходов» — 08 эксперты и тренеры, 09 стартап-курсы и инкубация, 10 R&D-ваучер,
  11 патент и товарный знак, 12 брендинг для победителей чемпионата, 15 инженерные сети;
- «Инвестиции» — 13 Yoshlar ventures (до 5 млрд сум), 14 чемпионат «Ёш тадбиркорлар» (до 1 млрд);
- «Программы» — 16 Uz-Combinator, Business-Combinator, Creative-Combinator.

У каждого продукта — типы субъекта (ЯТТ / МЧЖ / самозанятый) по требованиям к документам.
В анкету заявителя не входят документы, которые оформляет сам Фонд (решение Совета, договоры,
мониторинг), и документы после одобрения (транши, ежеквартальные отчёты).

- Категория ищется по русскому названию, если её нет — создаётся.
- Продукт создаётся черновиком (DRAFT), только если продукта с таким русским названием ещё нет
  (01 создаёт и миграция `c8e0a2b4d6f8` — тогда здесь он пропускается).
- Банки не привязываются: займы, возмещение и инвестиции выдаёт сам Фонд, продукт без банков
  публикуется, и утверждение Советом завершает заявку. Если продукту нужен банк — Фонд выбирает его
  перед публикацией.

Downgrade ничего не делает: продукт удаляется через API Фонда, если по нему нет заявок.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7d9f1a3c5e6"
down_revision: str | Sequence[str] | None = "a6c8e0f2b4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LANGUAGES = ("ru", "uz", "en")

CATEGORIES = {
    "LOANS": {
        "names": ("Займы и ссуды", "Qarzlar va ssudalar", "Loans"),
        "descriptions": (
            "Займы и беспроцентные ссуды Фонда (Положение, глава 3).",
            "Jamgʻarmaning qarzlari va foizsiz ssudalari (Nizom, 3-bob).",
            "Fund loans and interest-free loans (Regulation, chapter 3).",
        ),
        "sort_order": 1,
    },
    "COMPENSATION": {
        "names": ("Возмещение расходов", "Xarajatlarni qoplash", "Expense reimbursement"),
        "descriptions": (
            "Возмещение и оплата расходов стартапов и молодых предпринимателей (Положение, глава 4).",
            "Startaplar va yosh tadbirkorlar xarajatlarini qoplash va toʻlash (Nizom, 4-bob).",
            "Reimbursement and payment of expenses of startups and young entrepreneurs (Regulation, chapter 4).",
        ),
        "sort_order": 2,
    },
    "INVEST": {
        "names": ("Инвестиции", "Investitsiyalar", "Investments"),
        "descriptions": (
            "Инвестиции Фонда и Yoshlar ventures в обмен на долю в компании (Положение, глава 4).",
            "Jamgʻarma va Yoshlar ventures investitsiyalari kompaniyadagi ulush evaziga (Nizom, 4-bob).",
            "Investments by the Fund and Yoshlar ventures in exchange for an equity stake (Regulation, chapter 4).",
        ),
        "sort_order": 3,
    },
    "PROGRAMS": {
        "names": ("Программы", "Dasturlar", "Programmes"),
        "descriptions": (
            "Программы Фонда для молодёжи: Uz-Combinator, Business-Combinator, Creative-Combinator (Положение, глава 5).",
            "Jamgʻarmaning yoshlar uchun dasturlari: Uz-Combinator, Business-Combinator, Creative-Combinator (Nizom, 5-bob).",
            "Fund programmes for young people: Uz-Combinator, Business-Combinator, Creative-Combinator (Regulation, chapter 5).",
        ),
        "sort_order": 4,
    },
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


PRODUCTS = [
    {
        "source": "products/01_Bino_qurish_tamirlash_xomashyo_uskuna_qarz.docx",
        "category": "LOANS",
        "names": (
            "Строительство, ремонт и оснащение зданий, сырьё и оборудование",
            "Bino qurish, taʼmirlash va jihozlash, xomashyo va uskuna",
            "Construction, repair and equipping of buildings, raw materials and equipment",
        ),
        "descriptions": (
            "Заём до 10 000 БРВ на строительство, ремонт и оснащение зданий и сооружений, покупку зданий, сырья для производства, технологий и оборудования. Положение: глава 3, § 2.",
            "Bino va inshootlarni qurish, taʼmirlash va jihozlash, bino, ishlab chiqarish uchun xomashyo, texnologiya va asbob-uskuna sotib olish uchun 10 ming BHMgacha qarz. Nizom: 3-bob, 2-§.",
            "Loan of up to 10,000 BCU for construction, repair and equipping of buildings, purchase of buildings, production raw materials, technology and equipment. Regulation: chapter 3, § 2.",
        ),
        "allowed_subject_types": ["MCHJ"],
        "stages": [
            stage(
                1,
                ("Заявление и сумма", "Ariza va summa", "Application and amount"),
                fields=[
                    field(
                        "NUMBER",
                        (
                            "Запрашиваемая сумма, сум",
                            "Soʻralayotgan summa, soʻm",
                            "Requested amount, UZS",
                        ),
                    ),
                    field(
                        "NUMBER", ("Срок займа, месяцев", "Qarz muddati, oy", "Loan term, months")
                    ),
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
                when=("Цель займа", ("Строительство",)),
            ),
            stage(
                5,
                ("Для ремонта", "Taʼmirlash uchun", "For repair"),
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
                when=("Цель займа", ("Ремонт",)),
            ),
            stage(
                6,
                ("Для оснащения", "Jihozlash uchun", "For equipping"),
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
                when=("Цель займа", ("Оснащение",)),
            ),
            stage(
                7,
                ("Для покупки здания", "Bino sotib olish uchun", "For buying a building"),
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
                when=("Цель займа", ("Покупка здания или сооружения",)),
            ),
            stage(
                8,
                ("Для покупки сырья", "Xomashyo sotib olish uchun", "For buying raw materials"),
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
                when=("Цель займа", ("Покупка сырья для производства",)),
            ),
            stage(
                9,
                (
                    "Для покупки технологий и оборудования",
                    "Texnologiya va asbob-uskuna sotib olish uchun",
                    "For buying technology and equipment",
                ),
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
                        options=(
                            ("Да", "Ha", "Yes"),
                            ("Нет", "Yoʻq", "No"),
                        ),
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
                when=("Цель займа", ("Покупка технологий и оборудования",)),
            ),
        ],
    },
    {
        "source": "products/02_Xorijiy_til_markazi_320_BHM_qarz.docx",
        "category": "LOANS",
        "names": (
            "Центр иностранных языков в отдалённых районах",
            "Olis hududlarda xorijiy til markazi",
            "Foreign language centre in remote areas",
        ),
        "descriptions": (
            "Беспроцентная ссуда до 320 БРВ на организацию обучения иностранным языкам в отдалённых и периферийных районах. Положение: глава 3, § 3.",
            "Olis va chekka hududlarda xorijiy tillarga oʻqitish xizmatlarini tashkil etish uchun 320 BHMgacha foizsiz qarz (ssuda). Nizom: 3-bob, 3-§.",
            "Interest-free loan of up to 320 BCU to organise foreign language teaching in remote areas. Regulation: chapter 3, § 3.",
        ),
        "allowed_subject_types": ["YATT", "MCHJ"],
        "stages": [
            stage(
                1,
                ("Заявление и сумма", "Ariza va summa", "Application and amount"),
                fields=[
                    field(
                        "NUMBER",
                        (
                            "Запрашиваемая сумма, сум",
                            "Soʻralayotgan summa, soʻm",
                            "Requested amount, UZS",
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
                        ("Паспорт или ID-карта", "Pasport yoki ID-karta", "Passport or ID card"),
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
                            "Сертификат по иностранному языку не ниже C1 (не старше 2 лет)",
                            "Xorijiy til boʻyicha kamida C1 darajadagi sertifikat (olinganiga 2 yildan oshmagan)",
                            "Foreign language certificate of at least C1 (not older than 2 years)",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Документ о месте деятельности в махалле из приложения 3 к Положению (кадастр или аренда)",
                            "Faoliyat manzili Nizomning 3-ilovasidagi mahallada ekanini tasdiqlovchi hujjat",
                            "Proof that the business is in a mahalla listed in Annex 3 (cadastre or lease)",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Смета расходов и бизнес-план (не менее 20% учеников — из «Ёшлар дафтари»)",
                            "Xarajatlar smetasi va biznes-reja (oʻquvchilarning kamida 20 foizi “Yoshlar daftari”dan)",
                            "Cost estimate and business plan (at least 20% of students from the Youth Register)",
                        ),
                        max_files=2,
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
                    "Дополнительно для юридического лица",
                    "Yuridik shaxs uchun qoʻshimcha",
                    "Additional for a legal entity",
                ),
                fields=[
                    field(
                        "FILE",
                        (
                            "Учредительные документы (устав, учредительный договор; при одном учредителе — устав)",
                            "Taʼsis hujjatlari (ustav, taʼsis shartnomasi; yagona taʼsischida — ustav)",
                            "Founding documents (charter, founders' agreement; charter only for a sole founder)",
                        ),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Решение и приказ об учреждении",
                            "Taʼsis qarori va buyrugʻi",
                            "Founding decision and order",
                        ),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Приказ о назначении руководителя, паспорт или ID-карта и образец подписи",
                            "Rahbarni tayinlash toʻgʻrisida buyruq, pasport yoki ID-karta va imzo namunasi",
                            "Order appointing the head, passport or ID card and specimen signature",
                        ),
                        required=False,
                    ),
                ],
            ),
            stage(
                4,
                (
                    "Обеспечение (один или несколько видов)",
                    "Taʼminot (bir yoki bir nechta turi)",
                    "Collateral (one or more types)",
                ),
                fields=[
                    field(
                        "FILE",
                        (
                            "Поручительство третьего лица: письмо поручителя и его документы (паспорт, КАТМ, доход)",
                            "Uchinchi shaxs kafilligi: kafillik xati va kafil hujjatlari (pasport, KATM, ish haqi)",
                            "Third-party guarantee: guarantor's letter and documents (passport, KATM, income)",
                        ),
                        required=False,
                        max_files=3,
                    ),
                    field(
                        "FILE",
                        ("Страховой полис", "Sugʻurta polisi", "Insurance policy"),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Залог имущества: кадастр, свидетельство о праве или выписка из реестра, отчёт об оценке",
                            "Mol-mulk garovi: kadastr, huquq guvohnomasi yoki reestrdan koʻchirma, baholash hisoboti",
                            "Property pledge: cadastre, title certificate or registry extract, valuation report",
                        ),
                        required=False,
                        max_files=3,
                    ),
                ],
            ),
        ],
    },
    {
        "source": "products/03_Startap_studiya_inkubatsiya_5_mlrd_qarz.docx",
        "category": "LOANS",
        "names": (
            "Стартап-студии, инкубаторы и акселераторы",
            "Startap studiyalar, inkubatsiya va akseleratsiya markazlari",
            "Startup studios, incubators and accelerators",
        ),
        "descriptions": (
            "Беспроцентный заём до 5 млрд сум на создание стартап-студий, центров инкубации и акселерации. Положение: глава 3, § 4.",
            "Startap studiyalar, inkubatsiya va akseleratsiya markazlarini tashkil etish uchun 5 mlrd soʻmgacha foizsiz qarz. Nizom: 3-bob, 4-§.",
            "Interest-free loan of up to UZS 5 billion to set up startup studios, incubation and acceleration centres. Regulation: chapter 3, § 4.",
        ),
        "allowed_subject_types": ["MCHJ"],
        "stages": [
            stage(
                1,
                ("Заявление и сумма", "Ariza va summa", "Application and amount"),
                fields=[
                    field(
                        "NUMBER",
                        (
                            "Запрашиваемая сумма, сум",
                            "Soʻralayotgan summa, soʻm",
                            "Requested amount, UZS",
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
                            "Приказ о назначении руководителя, паспорт или ID-карта и образец подписи",
                            "Rahbarni tayinlash toʻgʻrisida buyruq, pasport yoki ID-karta va imzo namunasi",
                            "Order appointing the head, passport or ID card and specimen signature",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Подтверждение регистрации на единой электронной платформе стартап-экосистемы",
                            "Startap ekotizimining yagona elektron platformasida roʻyxatdan oʻtganlik tasdigʻi",
                            "Registration on the unified startup ecosystem platform",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Документ о праве собственности, аренды или безвозмездного пользования зданием",
                            "Binoga mulk, ijara yoki tekin foydalanish huquqini tasdiqlovchi hujjat",
                            "Document confirming ownership, lease or free use of the building",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Часть устава, где предусмотрена деятельность стартап-студии или инкубатора",
                            "Ustavda startap studiya yoki inkubatsiya faoliyati nazarda tutilgani (tegishli qismi)",
                            "Charter section providing for startup studio or incubator activity",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Трудовые или гражданско-правовые договоры команды (менеджер, разработчик, ментор)",
                            "Jamoa mavjudligini tasdiqlovchi mehnat yoki fuqarolik-huquqiy shartnomalar",
                            "Employment or service contracts of the team (manager, developer, mentor)",
                        ),
                        max_files=5,
                    ),
                    field(
                        "FILE",
                        (
                            "Справка об отсутствии налоговой задолженности (юрлицо, учредители, руководитель)",
                            "Soliq qarzi mavjud emasligi toʻgʻrisida maʼlumotnoma (yuridik shaxs, taʼsischilar, rahbar)",
                            "Certificate of no tax debt (legal entity, founders, head)",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Справка об отсутствии задолженности в Бюро принудительного исполнения",
                            "Majburiy ijro byurosida qarzdorlik yoʻqligi toʻgʻrisida maʼlumot",
                            "Certificate of no debt with the Compulsory Enforcement Bureau",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Документы о деятельности стартап-студии или инкубатора не менее 6 месяцев",
                            "Kamida 6 oy startap studiya yoki inkubatsiya faoliyatini yuritganini tasdiqlovchi hujjatlar",
                            "Proof of at least 6 months of startup studio or incubator activity",
                        ),
                        max_files=5,
                    ),
                    field(
                        "FILE",
                        (
                            "План деятельности стартап-студии или инкубатора",
                            "Startap studiya yoki inkubatsiya faoliyatini amalga oshirish rejasi",
                            "Activity plan of the startup studio or incubator",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Смета расходов на реализацию плана",
                            "Rejani amalga oshirish bilan bogʻliq xarajatlar smetasi",
                            "Cost estimate for the plan",
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
                    "Обеспечение: заём до 300 млн сум (один из видов)",
                    "Taʼminot: 300 mln soʻmgacha qarz (biri)",
                    "Collateral: loan up to UZS 300 million (one type)",
                ),
                fields=[
                    field(
                        "FILE",
                        (
                            "Страховой полис на возврат непогашенной части займа",
                            "Qarzning qaytarilmagan qismini toʻliq qaytarish majburiyatini olgan sugʻurta polisi",
                            "Insurance policy covering repayment of the outstanding loan",
                        ),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Поручительство юрлица с рейтингом не ниже «B» (56–65 баллов)",
                            "Reytingi kamida “B” (56–65 ball) boʻlgan yuridik shaxsning kafillik xati",
                            "Guarantee letter from a legal entity rated at least “B” (56–65 points)",
                        ),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Залог имущества: кадастр, свидетельство о праве или выписка из реестра, отчёт об оценке",
                            "Mol-mulk garovi: kadastr, huquq guvohnomasi yoki reestrdan koʻchirma, baholash hisoboti",
                            "Property pledge: cadastre, title certificate or registry extract, valuation report",
                        ),
                        required=False,
                        max_files=3,
                    ),
                ],
            ),
            stage(
                4,
                (
                    "Обеспечение: заём свыше 300 млн сум",
                    "Taʼminot: 300 mln soʻmdan ortiq qarz",
                    "Collateral: loan over UZS 300 million",
                ),
                fields=[
                    field(
                        "FILE",
                        (
                            "Подтверждение инвестиций в поддержанные стартапы не менее 10 000 $",
                            "Qoʻllab-quvvatlangan startaplar kamida 10 000 AQSh dollari investitsiya jalb qilganini tasdiqlovchi hujjatlar",
                            "Proof that supported startups raised at least USD 10,000 of investment",
                        ),
                        required=False,
                        max_files=5,
                    ),
                    field(
                        "FILE",
                        (
                            "Поручительство юрлица с рейтингом не ниже «BB» (66–75 баллов) или документы залога",
                            "Reytingi kamida “BB” (66–75 ball) boʻlgan yuridik shaxsning kafillik xati yoki garov hujjatlari",
                            "Guarantee from a legal entity rated at least “BB” (66–75 points) or pledge documents",
                        ),
                        required=False,
                        max_files=3,
                    ),
                ],
            ),
        ],
    },
    {
        "source": "products/04_Yangi_avlod_tadbirkorlari_500_BHM_ssuda.docx",
        "category": "LOANS",
        "names": (
            "«Янги авлод тадбиркорлари»: ссуда выпускникам программы",
            "“Yangi avlod tadbirkorlari”: dastur bitiruvchilariga ssuda",
            "“New Generation Entrepreneurs”: loan for programme graduates",
        ),
        "descriptions": (
            "Ссуда до 500 БРВ выпускникам программы «Янги авлод тадбиркорлари» (обучение оплачивает Фонд). Положение: глава 3, § 5.",
            "“Yangi avlod tadbirkorlari” dasturi bitiruvchilariga 500 BHMgacha ssuda (oʻqitish Jamgʻarma hisobidan). Nizom: 3-bob, 5-§.",
            "Loan of up to 500 BCU for graduates of the “New Generation Entrepreneurs” programme (training paid by the Fund). Regulation: chapter 3, § 5.",
        ),
        "allowed_subject_types": ["YATT", "MCHJ", "SELF_EMPLOYED"],
        "stages": [
            stage(
                1,
                ("Заявление и сумма", "Ariza va summa", "Application and amount"),
                fields=[
                    field(
                        "NUMBER",
                        (
                            "Запрашиваемая сумма, сум",
                            "Soʻralayotgan summa, soʻm",
                            "Requested amount, UZS",
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
                        ("Паспорт или ID-карта", "Pasport yoki ID-karta", "Passport or ID card"),
                    ),
                    field(
                        "FILE",
                        (
                            "Сертификат Агентства",
                            "Agentlik sertifikati nusxasi",
                            "Agency certificate",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Бизнес-проект (спрос, конкурентоспособность, расходы, доходы, рентабельность, срок окупаемости)",
                            "Biznes loyiha (bozor ehtiyoji, raqobatbardoshlik, xarajat, daromad, rentabellik, daromadga chiqish muddati)",
                            "Business project (demand, competitiveness, costs, income, profitability, payback period)",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Справка об отсутствии налоговой задолженности",
                            "Soliq qarzi mavjud emasligi toʻgʻrisida maʼlumotnoma",
                            "Certificate of no tax debt",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Справка об отсутствии задолженности в Бюро принудительного исполнения",
                            "Majburiy ijro byurosida qarzdorlik yoʻqligi toʻgʻrisida maʼlumot",
                            "Certificate of no debt with the Compulsory Enforcement Bureau",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Справка о наличии или отсутствии судимости",
                            "Sudlanmaganlik (yoki sudlanganlik) toʻgʻrisida maʼlumotnoma",
                            "Criminal record certificate",
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
                            "Справка о банковском счёте",
                            "Hisobvaraq toʻgʻrisida maʼlumotnoma",
                            "Bank account certificate",
                        ),
                    ),
                ],
            ),
            stage(
                3,
                ("Поручитель", "Kafil", "Guarantor"),
                fields=[
                    field(
                        "FILE",
                        (
                            "Паспорт, сведения о доходе и КАТМ поручителя",
                            "Kafilning pasporti, ish haqi va KATM maʼlumoti",
                            "Guarantor's passport, income and KATM report",
                        ),
                        max_files=3,
                    ),
                    field(
                        "FILE",
                        (
                            "Справка об отсутствии налоговой задолженности поручителя",
                            "Kafilning soliq qarzi mavjud emasligi toʻgʻrisida maʼlumotnoma",
                            "Guarantor's certificate of no tax debt",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Справка об отсутствии задолженности поручителя в Бюро принудительного исполнения",
                            "Kafilning Majburiy ijro byurosida qarzdorlik yoʻqligi toʻgʻrisida maʼlumot",
                            "Guarantor's certificate of no debt with the Compulsory Enforcement Bureau",
                        ),
                    ),
                ],
            ),
        ],
    },
    {
        "source": "products/05_Book_cafe_kitob_dokoni_1_mlrd_ssuda.docx",
        "category": "LOANS",
        "names": (
            "Book cafe и книжные магазины",
            "Book cafe va kitob doʻkonlari",
            "Book cafes and bookshops",
        ),
        "descriptions": (
            "Ссуда до 1 млрд сум на расширение деятельности Book cafe или книжного магазина. Положение: глава 3, § 6.",
            "“Book cafe” yoki kitob doʻkoni faoliyatini kengaytirish uchun 1 mlrd soʻmgacha ssuda. Nizom: 3-bob, 6-§.",
            "Loan of up to UZS 1 billion to expand a book cafe or bookshop. Regulation: chapter 3, § 6.",
        ),
        "allowed_subject_types": ["MCHJ"],
        "stages": [
            stage(
                1,
                ("Заявление и сумма", "Ariza va summa", "Application and amount"),
                fields=[
                    field(
                        "NUMBER",
                        (
                            "Запрашиваемая сумма, сум",
                            "Soʻralayotgan summa, soʻm",
                            "Requested amount, UZS",
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
                            "Приказ о назначении руководителя, решение о получении ссуды, паспорт или ID-карта",
                            "Rahbarni tayinlash toʻgʻrisida buyruq, ssuda olish boʻyicha qaror, pasport yoki ID-karta",
                            "Order appointing the head, decision to take the loan, passport or ID card",
                        ),
                        max_files=2,
                    ),
                    field(
                        "FILE",
                        (
                            "Подтверждение продажи более 10 000 книг в месяц (онлайн-касса, счета-фактуры)",
                            "Oyiga 10 mingdan ortiq kitob sotilganini tasdiqlovchi hujjat (onlayn-kassa, hisobvaraq-fakturalar)",
                            "Proof of selling over 10,000 books a month (online till, invoices)",
                        ),
                        max_files=3,
                    ),
                    field(
                        "FILE",
                        (
                            "Документ о праве собственности, аренды или безвозмездного пользования зданием",
                            "Binoga mulk, ijara yoki tekin foydalanish huquqini tasdiqlovchi hujjat",
                            "Document confirming ownership, lease or free use of the building",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Справка об отсутствии налоговой задолженности (юрлицо, учредители, руководитель)",
                            "Soliq qarzi mavjud emasligi toʻgʻrisida maʼlumotnoma (yuridik shaxs, taʼsischilar, rahbar)",
                            "Certificate of no tax debt (legal entity, founders, head)",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Справка об отсутствии задолженности в Бюро принудительного исполнения",
                            "Majburiy ijro byurosida qarzdorlik yoʻqligi toʻgʻrisida maʼlumot",
                            "Certificate of no debt with the Compulsory Enforcement Bureau",
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
                            "Технико-экономическое обоснование или бизнес-план проекта",
                            "Loyihaning texnik-iqtisodiy asoslanishi yoki biznes-reja",
                            "Feasibility study or business plan of the project",
                        ),
                    ),
                ],
            ),
            stage(
                3,
                ("Обеспечение", "Taʼminot", "Collateral"),
                fields=[
                    field(
                        "FILE",
                        (
                            "Поручительство или документы залога (кадастр, право собственности, оценка)",
                            "Kafillik xati yoki garov hujjatlari (kadastr, huquq guvohnomasi, baholash hisoboti)",
                            "Guarantee letter or pledge documents (cadastre, title, valuation)",
                        ),
                        max_files=3,
                    ),
                ],
            ),
        ],
    },
    {
        "source": "products/06_Kasb_hunar_ustaxona_1200_BHM_ssuda.docx",
        "category": "LOANS",
        "names": (
            "Ремесленные мастерские-лаборатории",
            "Kasb-hunar ustaxona-laboratoriyalari",
            "Vocational workshop laboratories",
        ),
        "descriptions": (
            "Беспроцентная ссуда до 1 200 БРВ на создание мастерской-лаборатории для обучения ремёслам. Положение: глава 3, § 7.",
            "Kasb-hunar ustaxona-laboratoriyasini tashkil etish uchun 1 200 BHMgacha foizsiz ssuda. Nizom: 3-bob, 7-§.",
            "Interest-free loan of up to 1,200 BCU to set up a vocational workshop laboratory. Regulation: chapter 3, § 7.",
        ),
        "allowed_subject_types": ["MCHJ"],
        "stages": [
            stage(
                1,
                ("Заявление и сумма", "Ariza va summa", "Application and amount"),
                fields=[
                    field(
                        "NUMBER",
                        (
                            "Запрашиваемая сумма, сум",
                            "Soʻralayotgan summa, soʻm",
                            "Requested amount, UZS",
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
                            "Приказ о назначении руководителя, паспорт или ID-карта и образец подписи",
                            "Rahbarni tayinlash toʻgʻrisida buyruq, pasport yoki ID-karta va imzo namunasi",
                            "Order appointing the head, passport or ID card and specimen signature",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Документ на собственное здание или договор долгосрочной аренды",
                            "Oʻz egaligidagi bino hujjati yoki uzoq muddatli ijara shartnomasi",
                            "Title to own building or long-term lease agreement",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Справка об отсутствии налоговой задолженности (юрлицо, учредители, руководитель)",
                            "Soliq qarzi mavjud emasligi toʻgʻrisida maʼlumotnoma (yuridik shaxs, taʼsischilar, rahbar)",
                            "Certificate of no tax debt (legal entity, founders, head)",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Справка об отсутствии задолженности в Бюро принудительного исполнения",
                            "Majburiy ijro byurosida qarzdorlik yoʻqligi toʻgʻrisida maʼlumot",
                            "Certificate of no debt with the Compulsory Enforcement Bureau",
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
                            "Технико-экономическое обоснование или бизнес-план проекта",
                            "Loyihaning texnik-iqtisodiy asoslanishi yoki biznes-reja",
                            "Feasibility study or business plan of the project",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Договоры со специалистами с опытом обучения ремеслу и подтверждение их опыта",
                            "Kasb-hunarga oʻrgatish tajribasiga ega mutaxassislar shartnomalari va tajribasini tasdiqlovchi hujjat",
                            "Contracts with craft-teaching specialists and proof of their experience",
                        ),
                        max_files=5,
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
                ("Обеспечение (один из видов)", "Taʼminot (biri)", "Collateral (one type)"),
                fields=[
                    field(
                        "FILE",
                        (
                            "Страховой полис на возврат непогашенной части займа",
                            "Qarzning qaytarilmagan qismini toʻliq qaytarish majburiyatini olgan sugʻurta polisi",
                            "Insurance policy covering repayment of the outstanding loan",
                        ),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Поручительство юрлица с рейтингом не ниже «B» (56–65 баллов)",
                            "Reytingi kamida “B” (56–65 ball) boʻlgan yuridik shaxsning kafillik xati",
                            "Guarantee letter from a legal entity rated at least “B” (56–65 points)",
                        ),
                        required=False,
                    ),
                ],
            ),
        ],
    },
    {
        "source": "products/07_Kochma_dokon_500_mln_ssuda.docx",
        "category": "LOANS",
        "names": ("Передвижные магазины", "Koʻchma doʻkonlar", "Mobile shops"),
        "descriptions": (
            "Ссуда до 500 млн сум на начало торговли и услуг в передвижных магазинах. Положение: глава 3, § 8.",
            "Koʻchma doʻkonlarda savdo va xizmat koʻrsatish faoliyatini boshlash uchun 500 mln soʻmgacha ssuda. Nizom: 3-bob, 8-§.",
            "Loan of up to UZS 500 million to start trade and services in mobile shops. Regulation: chapter 3, § 8.",
        ),
        "allowed_subject_types": ["YATT", "MCHJ"],
        "stages": [
            stage(
                1,
                ("Заявление и сумма", "Ariza va summa", "Application and amount"),
                fields=[
                    field(
                        "NUMBER",
                        (
                            "Запрашиваемая сумма, сум",
                            "Soʻralayotgan summa, soʻm",
                            "Requested amount, UZS",
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
                            "Подтверждение отсутствия аффилированности с Агентством, членами Совета, Фондом и Yoshlar ventures",
                            "Agentlik, Kengash aʼzolari, Jamgʻarma va Yoshlar ventures bilan affillanganlik yoʻqligi tasdigʻi",
                            "Confirmation of no affiliation with the Agency, Council members, the Fund and Yoshlar ventures",
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
                            "Справка об отсутствии налоговой задолженности (ИП или юрлицо, учредители, руководитель)",
                            "YaTT va yuridik shaxs, taʼsischilar va rahbarning soliq qarzi mavjud emasligi toʻgʻrisida maʼlumotnoma",
                            "Certificate of no tax debt (sole trader or legal entity, founders, head)",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Право на место передвижной торговли: QR-свидетельство E-auksion или договор с собственником",
                            "Koʻchma savdo joyiga huquq: E-auksion QR-kodli guvohnomasi yoki mulkdor bilan shartnoma",
                            "Right to the mobile trading spot: E-auksion QR certificate or contract with the owner",
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
                            "Технико-экономическое обоснование или бизнес-план проекта",
                            "Loyihaning texnik-iqtisodiy asoslanishi yoki biznes-reja",
                            "Feasibility study or business plan of the project",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Договор или коммерческое предложение на покупку передвижного магазина и оборудования",
                            "Koʻchma doʻkon, jihoz va asbob-uskuna xarid qilish shartnomasi yoki tijorat taklifi",
                            "Contract or offer to buy the mobile shop and equipment",
                        ),
                        max_files=2,
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
                    "Дополнительно для ИП",
                    "Yakka tartibdagi tadbirkor uchun qoʻshimcha",
                    "Additional for a sole trader",
                ),
                fields=[
                    field(
                        "FILE",
                        ("Паспорт или ID-карта", "Pasport yoki ID-karta", "Passport or ID card"),
                        required=False,
                    ),
                ],
            ),
            stage(
                4,
                (
                    "Дополнительно для юридического лица",
                    "Yuridik shaxs uchun qoʻshimcha",
                    "Additional for a legal entity",
                ),
                fields=[
                    field(
                        "FILE",
                        (
                            "Учредительные документы (устав, учредительный договор; при одном учредителе — устав)",
                            "Taʼsis hujjatlari (ustav, taʼsis shartnomasi; yagona taʼsischida — ustav)",
                            "Founding documents (charter, founders' agreement; charter only for a sole founder)",
                        ),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Приказ и решение о назначении руководителя и о получении займа, паспорт или ID-карта",
                            "Rahbarni tayinlash va qarz olish boʻyicha buyruq va qaror, pasport yoki ID-karta",
                            "Order and decision appointing the head and on borrowing, passport or ID card",
                        ),
                        required=False,
                        max_files=2,
                    ),
                ],
            ),
            stage(
                5,
                (
                    "Обеспечение (один или несколько видов)",
                    "Taʼminot (bir yoki bir nechta turi)",
                    "Collateral (one or more types)",
                ),
                fields=[
                    field(
                        "FILE",
                        (
                            "Поручительство третьего лица (паспорт, КАТМ, доход; для юрлица — письмо, устав, рейтинг)",
                            "Uchinchi shaxs kafilligi (pasport, KATM, ish haqi; yuridik shaxs — kafillik xati, taʼsis hujjatlari, reyting)",
                            "Third-party guarantee (passport, KATM, income; for a company — letter, charter, rating)",
                        ),
                        required=False,
                        max_files=3,
                    ),
                    field(
                        "FILE",
                        ("Страховой полис", "Sugʻurta polisi", "Insurance policy"),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Залог имущества: кадастр, свидетельство о праве или выписка из реестра, отчёт об оценке",
                            "Mol-mulk garovi: kadastr, huquq guvohnomasi yoki reestrdan koʻchirma, baholash hisoboti",
                            "Property pledge: cadastre, title certificate or registry extract, valuation report",
                        ),
                        required=False,
                        max_files=3,
                    ),
                    field(
                        "FILE",
                        (
                            "Иное обеспечение: покупаемый передвижной магазин (техпаспорт)",
                            "Boshqa taʼminot: sotib olinayotgan koʻchma doʻkon (texpasport)",
                            "Other collateral: the mobile shop being bought (registration certificate)",
                        ),
                        required=False,
                    ),
                ],
            ),
        ],
    },
    {
        "source": "products/08_Ekspert_trener_xarajatlari_100_mln.docx",
        "category": "COMPENSATION",
        "names": (
            "Расходы на экспертов и тренеров (менторов)",
            "Ekspert va trenerlar (mentorlar) xarajatlari",
            "Expert and trainer (mentor) expenses",
        ),
        "descriptions": (
            "Частичное возмещение расходов на иностранных и местных экспертов, тренеров (менторов) — до 100 млн сум. Положение: глава 4, § 2.",
            "Xorijiy va mahalliy ekspertlar, trenerlar (mentorlar) xarajatlarini qisman qoplash — 100 mln soʻmgacha. Nizom: 4-bob, 2-§.",
            "Partial reimbursement of foreign and local experts and trainers (mentors) — up to UZS 100 million. Regulation: chapter 4, § 2.",
        ),
        "allowed_subject_types": ["YATT", "MCHJ", "SELF_EMPLOYED"],
        "stages": [
            stage(
                1,
                ("Заявление и сумма", "Ariza va summa", "Application and amount"),
                fields=[
                    field(
                        "NUMBER",
                        (
                            "Сумма к возмещению, сум",
                            "Qoplanadigan summa, soʻm",
                            "Amount to reimburse, UZS",
                        ),
                    ),
                    field(
                        "FILE", ("Заявление в Фонд", "Jamgʻarmaga ariza", "Application to the Fund")
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
                            "Подтверждение отсутствия аффилированности с Агентством, членами Совета, Фондом и Yoshlar ventures",
                            "Agentlik, Kengash aʼzolari, Jamgʻarma va Yoshlar ventures bilan affillanganlik yoʻqligi tasdigʻi",
                            "Confirmation of no affiliation with the Agency, Council members, the Fund and Yoshlar ventures",
                        ),
                    ),
                    field(
                        "FILE",
                        ("Паспорт или ID-карта", "Pasport yoki ID-karta", "Passport or ID card"),
                    ),
                    field(
                        "FILE",
                        (
                            "Письменное согласие на сбор и обработку персональных данных",
                            "Shaxsga doir maʼlumotlarni yigʻish va ishlov berishga yozma rozilik",
                            "Written consent to the collection and processing of personal data",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Минимально жизнеспособный продукт (MVP) стартап-идеи",
                            "Startap gʻoyaning namunaviy modeli (MVP)",
                            "Minimum viable product (MVP) of the startup idea",
                        ),
                        max_files=3,
                    ),
                    field(
                        "FILE",
                        (
                            "Заключение привлечённого эксперта (ментора) о создании MVP",
                            "MVP yaratilgani haqida jalb etilgan ekspert, trener (mentor) xulosasi",
                            "Opinion of the engaged expert (mentor) on the MVP",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Целевая бизнес-модель и план коммерциализации",
                            "Maqsadli biznes model va tijoratlashtirish rejasi",
                            "Target business model and commercialisation plan",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Договор с экспертом или тренером (ментором); при трудовых отношениях — трудовой договор",
                            "Ekspert, trener (mentor) bilan shartnoma (mehnat munosabatlarida — mehnat shartnomasi)",
                            "Contract with the expert or trainer (mentor); employment contract if employed",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Подтверждение 3-летнего опыта эксперта в отрасли",
                            "Ekspertning sohadagi 3 yillik tajribasini tasdiqlovchi hujjat",
                            "Proof of the expert's 3 years of industry experience",
                        ),
                        max_files=2,
                    ),
                    field(
                        "FILE",
                        (
                            "Акт выполненных работ, подписанный заявителем и экспертом",
                            "Bajarilgan ishlar boʻyicha tashabbuskor va ekspert tasdiqlagan dalolatnoma",
                            "Certificate of completed work signed by the applicant and the expert",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Документ об оплате (заверенный банком или платёжной организацией)",
                            "Toʻlovni tasdiqlovchi hujjat nusxasi (bank yoki toʻlov tashkiloti tasdiqlagan)",
                            "Proof of payment (certified by a bank or payment institution)",
                        ),
                        max_files=3,
                    ),
                    field(
                        "FILE",
                        (
                            "Сведения о выплаченной зарплате (при трудовых отношениях)",
                            "Mehnat munosabatlarida toʻlangan ish haqi toʻgʻrisida maʼlumot",
                            "Salary paid (if employed)",
                        ),
                        required=False,
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
                    "Дополнительно для юридического лица",
                    "Yuridik shaxs uchun qoʻshimcha",
                    "Additional for a legal entity",
                ),
                fields=[
                    field(
                        "FILE",
                        (
                            "Учредительные документы (устав, учредительный договор; при одном учредителе — устав)",
                            "Taʼsis hujjatlari (ustav, taʼsis shartnomasi; yagona taʼsischida — ustav)",
                            "Founding documents (charter, founders' agreement; charter only for a sole founder)",
                        ),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Свидетельство о государственной регистрации",
                            "Davlat roʻyxatidan oʻtganlik guvohnomasi",
                            "State registration certificate",
                        ),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Если юрлицу больше 7 лет: аудиторское заключение, что операциям по стартапу не больше 7 лет",
                            "Yuridik shaxs 7 yildan ortiq faoliyat yuritgan boʻlsa: startap operatsiyalari 7 yildan oshmaganini tasdiqlovchi auditorlik xulosasi",
                            "If the company is over 7 years old: audit opinion that startup operations are under 7 years",
                        ),
                        required=False,
                    ),
                ],
            ),
        ],
    },
    {
        "source": "products/09_Oquv_kurs_inkubatsiya_xarajatlari.docx",
        "category": "COMPENSATION",
        "names": (
            "Стартап-курсы, инкубация и акселерация",
            "Startap oʻquv kurslari, inkubatsiya va akseleratsiya",
            "Startup courses, incubation and acceleration",
        ),
        "descriptions": (
            "Возмещение расходов на стартап-курсы, местные и международные программы инкубации и акселерации. Положение: глава 4, § 3.",
            "Startap oʻquv kurslari, mahalliy va xalqaro inkubatsiya va akseleratsiya dasturlari xarajatlarini qoplash. Nizom: 4-bob, 3-§.",
            "Reimbursement of startup courses and local or international incubation and acceleration programmes. Regulation: chapter 4, § 3.",
        ),
        "allowed_subject_types": ["YATT", "MCHJ", "SELF_EMPLOYED"],
        "stages": [
            stage(
                1,
                ("Заявление и сумма", "Ariza va summa", "Application and amount"),
                fields=[
                    field(
                        "NUMBER",
                        (
                            "Сумма к возмещению, сум",
                            "Qoplanadigan summa, soʻm",
                            "Amount to reimburse, UZS",
                        ),
                    ),
                    field(
                        "FILE", ("Заявление в Фонд", "Jamgʻarmaga ariza", "Application to the Fund")
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
                            "Подтверждение отсутствия аффилированности с Агентством, членами Совета, Фондом и Yoshlar ventures",
                            "Agentlik, Kengash aʼzolari, Jamgʻarma va Yoshlar ventures bilan affillanganlik yoʻqligi tasdigʻi",
                            "Confirmation of no affiliation with the Agency, Council members, the Fund and Yoshlar ventures",
                        ),
                    ),
                    field(
                        "FILE",
                        ("Паспорт или ID-карта", "Pasport yoki ID-karta", "Passport or ID card"),
                    ),
                    field(
                        "FILE",
                        (
                            "Письменное согласие на сбор и обработку персональных данных",
                            "Shaxsga doir maʼlumotlarni yigʻish va ishlov berishga yozma rozilik",
                            "Written consent to the collection and processing of personal data",
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
                ("Для стартап-курсов", "Startap oʻquv kurslari uchun", "For startup courses"),
                fields=[
                    field(
                        "FILE",
                        (
                            "Договор с организатором курса (направление одобрено Координационным советом)",
                            "Oʻquv kursi tashkilotchisi bilan shartnoma (yoʻnalishi Muvofiqlashtiruvchi kengash tasdiqlagan)",
                            "Contract with the course organiser (field approved by the Coordinating Council)",
                        ),
                        required=False,
                    ),
                    field(
                        "FILE",
                        ("Копия сертификата", "Sertifikat nusxasi", "Certificate copy"),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Документ об оплате (заверенный банком или платёжной организацией)",
                            "Toʻlovni tasdiqlovchi hujjat nusxasi (bank yoki toʻlov tashkiloti tasdiqlagan)",
                            "Proof of payment (certified by a bank or payment institution)",
                        ),
                        required=False,
                        max_files=3,
                    ),
                ],
            ),
            stage(
                4,
                (
                    "Для местных программ инкубации или акселерации",
                    "Mahalliy inkubatsiya yoki akseleratsiya dasturlari uchun",
                    "For local incubation or acceleration programmes",
                ),
                fields=[
                    field(
                        "FILE",
                        (
                            "Подтверждение регистрации на единой электронной платформе стартап-экосистемы",
                            "Startap ekotizimining yagona elektron platformasida roʻyxatdan oʻtganlik tasdigʻi",
                            "Registration on the unified startup ecosystem platform",
                        ),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Договор с организатором программы из утверждённого перечня",
                            "Tasdiqlangan roʻyxatdagi dastur tashkilotchisi bilan shartnoma",
                            "Contract with an organiser from the approved list",
                        ),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Для акселерации: MVP",
                            "Akseleratsiya dasturi uchun: MVP",
                            "For acceleration: MVP",
                        ),
                        required=False,
                        max_files=3,
                    ),
                ],
            ),
            stage(
                5,
                (
                    "Для международных программ инкубации или акселерации",
                    "Nufuzli xalqaro inkubatsiya yoki akseleratsiya dasturlari uchun",
                    "For international incubation or acceleration programmes",
                ),
                fields=[
                    field(
                        "FILE",
                        (
                            "Документ об успешном завершении программы",
                            "Dasturni muvaffaqiyatli tamomlaganini tasdiqlovchi hujjat",
                            "Proof of successful completion of the programme",
                        ),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Договор и (или) оферта",
                            "Shartnoma va (yoki) oferta",
                            "Contract and/or offer",
                        ),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Платёжное поручение, документы SWIFT и (или) инвойсы",
                            "Toʻlov topshiriqnomasi, SWIFT hujjatlari va (yoki) invoyslar",
                            "Payment order, SWIFT documents and/or invoices",
                        ),
                        required=False,
                        max_files=3,
                    ),
                    field(
                        "FILE",
                        (
                            "Для акселерации: MVP",
                            "Akseleratsiya dasturi uchun: MVP",
                            "For acceleration: MVP",
                        ),
                        required=False,
                        max_files=3,
                    ),
                ],
            ),
        ],
    },
    {
        "source": "products/10_RD_vaucher_MVP_xarajatlari.docx",
        "category": "COMPENSATION",
        "names": (
            "R&D-ваучер на создание MVP",
            "MVP yaratish uchun R&D vaucher",
            "R&D voucher for building an MVP",
        ),
        "descriptions": (
            "R&D-ваучер до 50 тыс. долл. США на создание MVP в молодёжных технопарках и R&D-центрах; отбор по конкурсу Агентства инновационного развития. Положение: глава 4, § 4.",
            "Yoshlar texnoparklari va R&D markazlarida MVP yaratish uchun 50 ming AQSh dollarigacha R&D vaucher; Innovatsion rivojlanish agentligi tanlovi orqali. Nizom: 4-bob, 4-§.",
            "R&D voucher of up to USD 50,000 for building an MVP in youth technoparks and R&D centres; selection through the Innovation Development Agency contest. Regulation: chapter 4, § 4.",
        ),
        "allowed_subject_types": ["YATT", "MCHJ", "SELF_EMPLOYED"],
        "stages": [
            stage(
                1,
                ("Заявление и сумма", "Ariza va summa", "Application and amount"),
                fields=[
                    field(
                        "NUMBER",
                        (
                            "Запрашиваемая сумма ваучера, долл. США",
                            "Soʻralayotgan vaucher summasi, AQSh dollari",
                            "Requested voucher amount, USD",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Заявка на участие в конкурсе и документы проекта",
                            "Tanlovda ishtirok etish arizasi va loyiha hujjatlari",
                            "Contest application and project documents",
                        ),
                        max_files=3,
                    ),
                    field(
                        "FILE",
                        (
                            "Подтверждение отбора по итогам конкурса",
                            "Tanlov natijasi boʻyicha saralab olinganlik tasdigʻi",
                            "Confirmation of selection in the contest",
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
                ],
            ),
        ],
    },
    {
        "source": "products/11_Patent_tovar_belgisi_xarajatlari_30_BHM.docx",
        "category": "COMPENSATION",
        "names": (
            "Патентование и регистрация товарного знака",
            "Patentlash va tovar belgisini roʻyxatdan oʻtkazish",
            "Patenting and trademark registration",
        ),
        "descriptions": (
            "Возмещение расходов на патентование стартапа и регистрацию товарного знака — до 30 БРВ. Положение: глава 4, § 5.",
            "Startap loyihalarni patentlash va tovar belgisini roʻyxatdan oʻtkazish xarajatlarini qoplash — 30 BHMgacha. Nizom: 4-bob, 5-§.",
            "Reimbursement of startup patenting and trademark registration — up to 30 BCU. Regulation: chapter 4, § 5.",
        ),
        "allowed_subject_types": ["YATT", "MCHJ", "SELF_EMPLOYED"],
        "stages": [
            stage(
                1,
                ("Заявление и сумма", "Ariza va summa", "Application and amount"),
                fields=[
                    field(
                        "NUMBER",
                        (
                            "Сумма к возмещению, сум",
                            "Qoplanadigan summa, soʻm",
                            "Amount to reimburse, UZS",
                        ),
                    ),
                    field(
                        "FILE", ("Заявление в Фонд", "Jamgʻarmaga ariza", "Application to the Fund")
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
                            "Подтверждение отсутствия аффилированности с Агентством, членами Совета, Фондом и Yoshlar ventures",
                            "Agentlik, Kengash aʼzolari, Jamgʻarma va Yoshlar ventures bilan affillanganlik yoʻqligi tasdigʻi",
                            "Confirmation of no affiliation with the Agency, Council members, the Fund and Yoshlar ventures",
                        ),
                    ),
                    field(
                        "FILE",
                        ("Паспорт или ID-карта", "Pasport yoki ID-karta", "Passport or ID card"),
                    ),
                    field(
                        "FILE",
                        (
                            "Письменное согласие на сбор и обработку персональных данных",
                            "Shaxsga doir maʼlumotlarni yigʻish va ishlov berishga yozma rozilik",
                            "Written consent to the collection and processing of personal data",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Свидетельство о регистрации изобретения, полезной модели, промышленного образца или товарного знака",
                            "Ixtiro, foydali model, sanoat namunasi yoki tovar belgisi roʻyxatdan oʻtkazilgani toʻgʻrisida guvohnoma",
                            "Registration certificate of the invention, utility model, industrial design or trademark",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Документы об оплате за получение свидетельства (за последний год)",
                            "Guvohnomani olish uchun toʻlovlarni tasdiqlovchi hujjatlar (soʻnggi 1 yil ichida)",
                            "Proof of fees paid for the certificate (within the last year)",
                        ),
                        max_files=3,
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
        ],
    },
    {
        "source": "products/12_Chempionat_brend_xarajatlari_100_BHM.docx",
        "category": "COMPENSATION",
        "names": (
            "Брендинг для победителей чемпионата «Ёш тадбиркорлар»",
            "“Yosh tadbirkorlar” chempionati gʻoliblari uchun brending",
            "Branding for “Young Entrepreneurs” championship winners",
        ),
        "descriptions": (
            "Оплата расходов на превращение проекта в бренд для победителей чемпионата «Ёш тадбиркорлар» — до 100 БРВ. Положение: глава 4, § 6.",
            "“Yosh tadbirkorlar” chempionati gʻoliblari uchun brendga aylantirish xarajatlarini toʻlash — 100 BHMgacha. Nizom: 4-bob, 6-§.",
            "Payment of branding costs for winners of the “Young Entrepreneurs” championship — up to 100 BCU. Regulation: chapter 4, § 6.",
        ),
        "allowed_subject_types": ["YATT", "MCHJ", "SELF_EMPLOYED"],
        "stages": [
            stage(
                1,
                ("Заявление и сумма", "Ariza va summa", "Application and amount"),
                fields=[
                    field(
                        "NUMBER",
                        (
                            "Сумма оплаты услуг эксперта, сум",
                            "Ekspert xizmat haqi summasi, soʻm",
                            "Expert service fee, UZS",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Заявление в Фонд об оплате услуг эксперта",
                            "Jamgʻarmaga ariza (ekspert xizmat haqini toʻlash toʻgʻrisida)",
                            "Application to the Fund to pay the expert's fee",
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
                            "Подтверждение отсутствия аффилированности с Агентством, членами Совета, Фондом и Yoshlar ventures",
                            "Agentlik, Kengash aʼzolari, Jamgʻarma va Yoshlar ventures bilan affillanganlik yoʻqligi tasdigʻi",
                            "Confirmation of no affiliation with the Agency, Council members, the Fund and Yoshlar ventures",
                        ),
                    ),
                    field(
                        "FILE",
                        ("Паспорт или ID-карта", "Pasport yoki ID-karta", "Passport or ID card"),
                    ),
                    field(
                        "FILE",
                        (
                            "Подтверждение 1–3 места в чемпионате",
                            "Chempionatda 1–3-oʻrinni egallaganlik tasdigʻi",
                            "Proof of 1st–3rd place in the championship",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Сведения об услугах эксперта из списка Фонда, оплате и ожидаемом результате",
                            "Jamgʻarma roʻyxatidan tanlangan ekspert xizmatlari, toʻlovlari va kutilgan natija haqida maʼlumot",
                            "Details of the expert from the Fund's list: services, fees and expected result",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Договор с экспертом на финансовые и маркетинговые услуги",
                            "Ariza beruvchi va ekspert oʻrtasidagi moliyaviy va marketing xizmatlari shartnomasi",
                            "Contract with the expert for financial and marketing services",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Реквизиты банковской карты эксперта",
                            "Ekspertning bank toʻlov kartasi rekvizitlari",
                            "Expert's bank card details",
                        ),
                    ),
                ],
            ),
            stage(
                3,
                ("Для итоговой оплаты", "Yakuniy toʻlov uchun", "For the final payment"),
                fields=[
                    field(
                        "FILE",
                        (
                            "Документ о полном выполнении и приёмке работ",
                            "Ishlar toʻliq bajarilib, qabul qilinganini tasdiqlovchi hujjat",
                            "Proof that the work was fully done and accepted",
                        ),
                        required=False,
                    ),
                ],
            ),
        ],
    },
    {
        "source": "products/13_Yoshlar_ventures_5_mlrd_investitsiya.docx",
        "category": "INVEST",
        "names": (
            "Yoshlar ventures: инвестиции до 5 млрд сум для выхода на внешний рынок",
            "Yoshlar ventures: xorijiy bozorga chiqish uchun 5 mlrd soʻmgacha investitsiya",
            "Yoshlar ventures: investment of up to UZS 5 billion to enter foreign markets",
        ),
        "descriptions": (
            "Доля Yoshlar ventures и инвестиции до 5 млрд сум в проекты, способные выйти на зарубежный рынок. Положение: глава 4, § 7.",
            "Xorijiy bozorga chiqish imkoniyatiga ega loyihalarga Yoshlar ventures ulushi va 5 mlrd soʻmgacha investitsiya. Nizom: 4-bob, 7-§.",
            "Yoshlar ventures equity stake and investment of up to UZS 5 billion in projects able to enter foreign markets. Regulation: chapter 4, § 7.",
        ),
        "allowed_subject_types": ["MCHJ"],
        "stages": [
            stage(
                1,
                ("Заявление и сумма", "Ariza va summa", "Application and amount"),
                fields=[
                    field(
                        "NUMBER",
                        (
                            "Запрашиваемая сумма, сум",
                            "Soʻralayotgan summa, soʻm",
                            "Requested amount, UZS",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Заявление по форме, утверждённой Фондом",
                            "Jamgʻarma tasdiqlagan shakldagi ariza",
                            "Application in the form approved by the Fund",
                        ),
                    ),
                ],
            ),
            stage(
                2,
                ("Документы компании", "Kompaniya hujjatlari", "Company documents"),
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
                            "Устав юридического лица",
                            "Yuridik shaxs ustavi",
                            "Charter of the legal entity",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Свидетельство о государственной регистрации",
                            "Davlat roʻyxatidan oʻtganlik guvohnomasi",
                            "State registration certificate",
                        ),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Подтверждение деятельности более 6 месяцев",
                            "Kamida 6 oydan ortiq faoliyat koʻrsatayotganini tasdiqlovchi maʼlumot",
                            "Proof of operating for more than 6 months",
                        ),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Паспорта или ID-карты учредителей-молодёжи",
                            "Taʼsischi yosh fuqarolarning pasporti yoki ID-kartasi",
                            "Passports or ID cards of young founders",
                        ),
                        max_files=5,
                    ),
                    field(
                        "FILE",
                        (
                            "Согласие на сбор и обработку персональных данных",
                            "Shaxsga doir maʼlumotlarni yigʻish va ishlov berishga yozma rozilik",
                            "Consent to the collection and processing of personal data",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Годовой оборот не менее 500 млн сум и рост выручки",
                            "Yillik aylanma kamida 500 mln soʻm va daromad oʻsishi toʻgʻrisida maʼlumot",
                            "Annual turnover of at least UZS 500 million and revenue growth",
                        ),
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Подтверждение создания не менее 5 рабочих мест",
                            "Kamida 5 ta ish oʻrni yaratilganini tasdiqlovchi maʼlumot",
                            "Proof that at least 5 jobs have been created",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Справка об отсутствии налоговой задолженности (юрлицо, учредители, руководитель)",
                            "Yuridik shaxs, taʼsischilar va rahbarning soliq qarzi yoʻqligi toʻgʻrisida maʼlumotnoma",
                            "Certificate of no tax debt (company, founders, head)",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Справка об отсутствии задолженности в Бюро принудительного исполнения",
                            "Majburiy ijro byurosida qarzdorlik yoʻqligi toʻgʻrisida maʼlumot",
                            "Certificate of no debt with the Compulsory Enforcement Bureau",
                        ),
                    ),
                ],
            ),
            stage(
                3,
                ("Проект", "Loyiha", "Project"),
                fields=[
                    field(
                        "FILE",
                        (
                            "Презентация: продукт на рынке Узбекистана и выход на зарубежный рынок (страна, спрос, конкурентоспособность)",
                            "Taqdimot: mahsulot Oʻzbekiston bozorida joriy qilingani va xorijiy bozorga chiqish imkoniyati (davlat, talab, raqobatbardoshlik)",
                            "Presentation: product on the Uzbek market and entry to a foreign market (country, demand, competitiveness)",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Бизнес-план проекта",
                            "Loyihaning biznes-rejasi",
                            "Project business plan",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Выручка от реализации товаров (услуг) за последние 6 месяцев",
                            "Soʻnggi 6 oyda tovar (xizmat) realizatsiyasidan olingan daromad toʻgʻrisida maʼlumot",
                            "Revenue from sales of goods (services) for the last 6 months",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Сведения о прежнем финансировании проекта из других источников",
                            "Loyiha avval boshqa manbalardan moliyalashtirilgan boʻlsa, bu haqida maʼlumot",
                            "Information on previous financing of the project from other sources",
                        ),
                        required=False,
                    ),
                ],
            ),
        ],
    },
    {
        "source": "products/14_Chempionat_1_mlrd_investitsiya.docx",
        "category": "INVEST",
        "names": (
            "Чемпионат «Ёш тадбиркорлар»: инвестиции до 1 млрд сум",
            "«Yosh tadbirkorlar» chempionati: 1 mlrd soʻmgacha investitsiya",
            "«Yosh tadbirkorlar» championship: investment of up to UZS 1 billion",
        ),
        "descriptions": (
            "Инвестиции до 1 млрд сум в лучшие (до 100) проекты чемпионата «Ёш тадбиркорлар». Положение: глава 4, § 8.",
            "«Yosh tadbirkorlar» chempionatining eng yaxshi 100 tagacha loyihasiga 1 mlrd soʻmgacha investitsiya. Nizom: 4-bob, 8-§.",
            "Investment of up to UZS 1 billion in the best (up to 100) projects of the «Yosh tadbirkorlar» championship. Regulation: chapter 4, § 8.",
        ),
        "allowed_subject_types": ["MCHJ"],
        "stages": [
            stage(
                1,
                ("Заявление и сумма", "Ariza va summa", "Application and amount"),
                fields=[
                    field(
                        "NUMBER",
                        (
                            "Запрашиваемая сумма, сум",
                            "Soʻralayotgan summa, soʻm",
                            "Requested amount, UZS",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Заявление и документы о соответствии критериям по порядку проведения чемпионата",
                            "Chempionat tartibida belgilangan ariza va mezonlarga muvofiqlik hujjatlari",
                            "Application and documents on meeting the criteria under the championship rules",
                        ),
                        max_files=5,
                    ),
                ],
            ),
            stage(
                2,
                ("Документы", "Hujjatlar", "Documents"),
                fields=[
                    field(
                        "FILE",
                        (
                            "Подтверждение включения в число лучших проектов",
                            "Eng yaxshi loyihalar qatoriga kiritilganlik tasdigʻi",
                            "Confirmation of inclusion among the best projects",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Подтверждение внедрения новой разработки в предпринимательскую деятельность (патент — при наличии)",
                            "Tadbirkorlik faoliyatiga yangi ishlanma joriy qilinganini tasdiqlovchi hujjat (patent boʻlsa)",
                            "Proof of introducing a new development into the business (patent, if any)",
                        ),
                        max_files=3,
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
                        required=False,
                    ),
                ],
            ),
        ],
    },
    {
        "source": "products/15_Muhandislik_tarmoqlariga_ulanish_10_BHM.docx",
        "category": "COMPENSATION",
        "names": (
            "Подключение к инженерным сетям",
            "Muhandislik tarmoqlariga ulanish",
            "Connection to utility networks",
        ),
        "descriptions": (
            "Возмещение расходов начинающих молодых предпринимателей на подключение к инженерно-коммуникационным сетям — до 10 БРВ. Положение: глава 4, § 9.",
            "Yangi ish boshlayotgan yosh tadbirkorlarga muhandislik-kommunikatsiya tarmoqlariga ulanish xarajatlarini qoplash — 10 BHMgacha. Nizom: 4-bob, 9-§.",
            "Reimbursement of utility network connection costs for young entrepreneurs starting a business — up to 10 BCU. Regulation: chapter 4, § 9.",
        ),
        "allowed_subject_types": ["MCHJ"],
        "stages": [
            stage(
                1,
                ("Заявление и сумма", "Ariza va summa", "Application and amount"),
                fields=[
                    field(
                        "NUMBER",
                        (
                            "Сумма к возмещению, сум",
                            "Qoplanadigan summa, soʻm",
                            "Amount to reimburse, UZS",
                        ),
                    ),
                    field(
                        "FILE", ("Заявление в Фонд", "Jamgʻarmaga ariza", "Application to the Fund")
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
                            "Паспорта или ID-карты учредителей (не менее 50% доли — у граждан 18–30 лет)",
                            "Taʼsischilarning pasporti yoki ID-kartasi (ulushning kamida 50 foizi 18–30 yoshdagi fuqaroga tegishli)",
                            "Founders' passports or ID cards (at least 50% share held by citizens aged 18–30)",
                        ),
                        max_files=5,
                    ),
                    field(
                        "FILE",
                        (
                            "Письменное согласие на сбор и обработку персональных данных",
                            "Shaxsga doir maʼlumotlarni yigʻish va ishlov berishga yozma rozilik",
                            "Written consent to the collection and processing of personal data",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Квитанция об оплате подключения к электросети, водопроводу или канализации (не старше 90 дней)",
                            "Elektr, ichimlik suvi yoki oqova suv tarmogʻiga ulanish yigʻimi toʻlov hujjati (90 kundan oshmagan)",
                            "Receipt for the electricity, water or sewerage connection fee (not older than 90 days)",
                        ),
                        max_files=3,
                    ),
                    field(
                        "FILE", ("Документ о подключении", "Ulanish hujjati", "Connection document")
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
        ],
    },
    {
        "source": "products/16_Combinator_dasturlari.docx",
        "category": "PROGRAMS",
        "names": ("Программы «Combinator»", "«Combinator» dasturlari", "«Combinator» programmes"),
        "descriptions": (
            "Uz-Combinator, Business-Combinator и Creative-Combinator — программы Фонда для молодёжи; участники по итогам программы получают призовые и могут привлечь инвестиции Yoshlar ventures. Положение: глава 5.",
            "Uz-Combinator, Business-Combinator va Creative-Combinator — Jamgʻarmaning yoshlar uchun dasturlari; ishtirokchilar dastur yakunida mukofot oladi va Yoshlar ventures investitsiyasini jalb qilishi mumkin. Nizom: 5-bob.",
            "Uz-Combinator, Business-Combinator and Creative-Combinator — Fund programmes for young people; participants receive prize money at the end and may attract Yoshlar ventures investment. Regulation: chapter 5.",
        ),
        "allowed_subject_types": ["YATT", "MCHJ", "SELF_EMPLOYED"],
        "stages": [
            stage(
                1,
                ("Заявка", "Ariza", "Application"),
                fields=[
                    field(
                        "SELECT",
                        ("Программа", "Dastur", "Programme"),
                        options=(
                            ("Uz-Combinator", "Uz-Combinator", "Uz-Combinator"),
                            ("Business-Combinator", "Business-Combinator", "Business-Combinator"),
                            ("Creative-Combinator", "Creative-Combinator", "Creative-Combinator"),
                        ),
                    ),
                    field(
                        "FILE",
                        ("Паспорт или ID-карта", "Pasport yoki ID-karta", "Passport or ID card"),
                    ),
                    field(
                        "FILE",
                        (
                            "Согласие на сбор и обработку персональных данных",
                            "Shaxsga doir maʼlumotlarni yigʻish va ishlov berishga yozma rozilik",
                            "Consent to the collection and processing of personal data",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Описание проекта или инициативы (по критериям, установленным Советом)",
                            "Loyiha yoki tashabbus tavsifi (Kengash belgilagan mezonlarga muvofiq)",
                            "Description of the project or initiative (per the criteria set by the Council)",
                        ),
                    ),
                ],
            ),
        ],
    },
]


def _log(message: str) -> None:
    print(f"[products] {message}")


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


def _category_id(conn, key: str) -> int:
    category = CATEGORIES[key]
    found = conn.execute(
        sa.text(
            "SELECT category_id FROM product_category_translations "
            "WHERE language = 'ru' AND name = :name ORDER BY category_id LIMIT 1"
        ),
        {"name": category["names"][0]},
    ).scalar()
    if found is not None:
        return found
    category_id = _insert(
        conn,
        "INSERT INTO product_categories (is_active, sort_order) VALUES (true, :sort_order)",
        sort_order=category["sort_order"],
    )
    _translations(
        conn,
        "product_category_translations",
        "category_id",
        category_id,
        category["names"],
        category["descriptions"],
    )
    _log(f"category «{category['names'][0]}» created (id {category_id})")
    return category_id


def _create_product(conn, product: dict) -> None:
    existing = conn.execute(
        sa.text(
            "SELECT product_id FROM product_translations "
            "WHERE language = 'ru' AND name = :name ORDER BY product_id LIMIT 1"
        ),
        {"name": product["names"][0]},
    ).scalar()
    if existing is not None:
        _log(f"«{product['names'][0]}» already exists (id {existing}), skipped")
        return

    product_id = _insert(
        conn,
        "INSERT INTO products (status, allowed_subject_types, category_id) "
        "VALUES ('DRAFT', CAST(:types AS varchar[]), :category_id)",
        types=product["allowed_subject_types"],
        category_id=_category_id(conn, product["category"]),
    )
    _translations(
        conn,
        "product_translations",
        "product_id",
        product_id,
        product["names"],
        product["descriptions"],
    )

    # ru-название поля с вариантами → (id поля, {ru-название варианта: id}) — для условий
    controllers: dict[str, tuple[int, dict[str, int]]] = {}

    def condition(when: tuple | None) -> tuple[int | None, list[int] | None]:
        if when is None:
            return None, None
        field_id, options = controllers[when[0]]
        return field_id, [options[name] for name in when[1]]

    for item in product["stages"]:
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
    _log(f"«{product['names'][0]}» created (id {product_id})")


def upgrade() -> None:
    conn = op.get_bind()
    for product in PRODUCTS:
        _create_product(conn, product)


def downgrade() -> None:
    # Продукты удаляются через API Фонда (DELETE /fund/products/{id}), если по ним нет заявок.
    pass
