"""Продукты по списку Фонда (20): +кредиты, «Кўмак+», инкубация; −3 лишних

Revision ID: d9f1b3c5e7a0
Revises: c8e0a2b4d6f9
Create Date: 2026-11-24

Список Фонда — 20 продуктов в 4 категориях:

- «Кредиты» (новая) — до 100 млн, 100–500 млн, 500 млн – 5 млрд сум (ЯТТ, МЧЖ, самозанятый) и
  кредит кооперативам до 5 млрд (тип «Кооператив»). Перечней документов банков пока нет: анкета —
  заявление, сумма и срок, паспорт, регистрация, бизнес-план, согласие на отчёт KATM, справка о
  счёте (у кооператива — ещё устав, решение собрания и список членов). Банки выбирает Фонд.
- «Займы и ссуды» — 7 продуктов миграции `b7d9f1a3c5e6` и «Кўмак+»: дополнительный заём до 730 БРВ
  только для получивших «Кўмак» (docx 02, раздел 4).
- «Возмещение расходов» — 08, 10, 11, 15 и два новых по docx 09: участие в международных
  программах инкубации и акселерации (50%, до 20 000 $) и взнос за местные программы (до 100 БРВ).
- «Инвестиции» — Yoshlar ventures и чемпионат «Ёш тадбиркорлар».

Продукты прежней миграции, которых нет в списке, — «Брендинг для победителей чемпионата»,
«Программы «Combinator»» и общий «Стартап-курсы, инкубация и акселерация» — удаляются, если по
ним нет заявок, иначе переводятся в ARCHIVED; пустая категория «Программы» удаляется.

Новые продукты создаются черновиками (DRAFT), только если продукта с таким русским названием нет.
Downgrade ничего не делает: продукты удаляются через API Фонда, если по ним нет заявок.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d9f1b3c5e7a0"
down_revision: str | Sequence[str] | None = "c8e0a2b4d6f9"
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
    "CREDITS": {
        "names": ("Кредиты", "Kreditlar", "Credits"),
        "descriptions": (
            "Льготные кредиты молодым предпринимателям через коммерческие банки.",
            "Yosh tadbirkorlarga tijorat banklari orqali imtiyozli kreditlar.",
            "Preferential loans to young entrepreneurs through commercial banks.",
        ),
        "sort_order": 0,
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
        "source": "список продуктов Фонда (кредит; docx нет)",
        "category": "CREDITS",
        "names": (
            "Льготный кредит до 100 млн сум",
            "100 mln soʻmgacha imtiyozli kredit",
            "Preferential loan of up to UZS 100 million",
        ),
        "descriptions": (
            "Кредит до 100 млн сум. Льготный кредит через коммерческий банк; заявитель проходит проверку KATM. Перечень документов банка уточняется.",
            "100 mln soʻmgacha kredit. Tijorat banki orqali imtiyozli kredit; tashabbuskor KATM tekshiruvidan oʻtadi. Bank hujjatlari roʻyxati aniqlashtiriladi.",
            "Loan of up to UZS 100 million. Preferential loan through a commercial bank; the applicant passes the KATM check. The bank's document list is to be specified.",
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
                        "NUMBER",
                        ("Срок кредита, месяцев", "Kredit muddati, oy", "Loan term, months"),
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
                ("Документы", "Hujjatlar", "Documents"),
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
                        required=False,
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
                            "Согласие на получение кредитного отчёта КАТМ (дата, пользователь и цель)",
                            "KATM kredit hisobotini olishga rozilik (sana, foydalanuvchi va maqsad koʻrsatilgan)",
                            "Consent to obtain the KATM credit report (date, user and purpose stated)",
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
        ],
    },
    {
        "source": "список продуктов Фонда (кредит; docx нет)",
        "category": "CREDITS",
        "names": (
            "Льготный кредит от 100 до 500 млн сум",
            "100 mln soʻmdan 500 mln soʻmgacha imtiyozli kredit",
            "Preferential loan from UZS 100 to 500 million",
        ),
        "descriptions": (
            "Кредит свыше 100 млн и до 500 млн сум. Льготный кредит через коммерческий банк; заявитель проходит проверку KATM. Перечень документов банка уточняется.",
            "100 mln soʻmdan ortiq va 500 mln soʻmgacha kredit. Tijorat banki orqali imtiyozli kredit; tashabbuskor KATM tekshiruvidan oʻtadi. Bank hujjatlari roʻyxati aniqlashtiriladi.",
            "Loan above UZS 100 million and up to 500 million. Preferential loan through a commercial bank; the applicant passes the KATM check. The bank's document list is to be specified.",
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
                        "NUMBER",
                        ("Срок кредита, месяцев", "Kredit muddati, oy", "Loan term, months"),
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
                ("Документы", "Hujjatlar", "Documents"),
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
                        required=False,
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
                            "Согласие на получение кредитного отчёта КАТМ (дата, пользователь и цель)",
                            "KATM kredit hisobotini olishga rozilik (sana, foydalanuvchi va maqsad koʻrsatilgan)",
                            "Consent to obtain the KATM credit report (date, user and purpose stated)",
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
        ],
    },
    {
        "source": "список продуктов Фонда (кредит; docx нет)",
        "category": "CREDITS",
        "names": (
            "Льготный кредит от 500 млн до 5 млрд сум",
            "500 mln soʻmdan 5 mlrd soʻmgacha imtiyozli kredit",
            "Preferential loan from UZS 500 million to 5 billion",
        ),
        "descriptions": (
            "Кредит свыше 500 млн и до 5 млрд сум. Льготный кредит через коммерческий банк; заявитель проходит проверку KATM. Перечень документов банка уточняется.",
            "500 mln soʻmdan ortiq va 5 mlrd soʻmgacha kredit. Tijorat banki orqali imtiyozli kredit; tashabbuskor KATM tekshiruvidan oʻtadi. Bank hujjatlari roʻyxati aniqlashtiriladi.",
            "Loan above UZS 500 million and up to 5 billion. Preferential loan through a commercial bank; the applicant passes the KATM check. The bank's document list is to be specified.",
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
                        "NUMBER",
                        ("Срок кредита, месяцев", "Kredit muddati, oy", "Loan term, months"),
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
                ("Документы", "Hujjatlar", "Documents"),
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
                        required=False,
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
                            "Согласие на получение кредитного отчёта КАТМ (дата, пользователь и цель)",
                            "KATM kredit hisobotini olishga rozilik (sana, foydalanuvchi va maqsad koʻrsatilgan)",
                            "Consent to obtain the KATM credit report (date, user and purpose stated)",
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
        ],
    },
    {
        "source": "список продуктов Фонда (кредит; docx нет)",
        "category": "CREDITS",
        "names": (
            "Кредит кооперативам до 5 млрд сум",
            "Kooperativlarga 5 mlrd soʻmgacha kredit",
            "Loan to cooperatives of up to UZS 5 billion",
        ),
        "descriptions": (
            "Кредит кооперативам до 5 млрд сум. Льготный кредит через коммерческий банк; заявитель проходит проверку KATM. Перечень документов банка уточняется.",
            "Kooperativlarga 5 mlrd soʻmgacha kredit. Tijorat banki orqali imtiyozli kredit; tashabbuskor KATM tekshiruvidan oʻtadi. Bank hujjatlari roʻyxati aniqlashtiriladi.",
            "Loan to cooperatives of up to UZS 5 billion. Preferential loan through a commercial bank; the applicant passes the KATM check. The bank's document list is to be specified.",
        ),
        "allowed_subject_types": ["COOPERATIVE"],
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
                        "NUMBER",
                        ("Срок кредита, месяцев", "Kredit muddati, oy", "Loan term, months"),
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
                ("Документы", "Hujjatlar", "Documents"),
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
                        required=False,
                    ),
                    field(
                        "FILE",
                        (
                            "Устав кооператива и решение общего собрания о получении кредита",
                            "Kooperativ ustavi va kredit olish toʻgʻrisida umumiy yigʻilish qarori",
                            "Cooperative charter and general meeting decision to borrow",
                        ),
                        max_files=2,
                    ),
                    field(
                        "FILE",
                        (
                            "Список членов кооператива",
                            "Kooperativ aʼzolari roʻyxati",
                            "List of cooperative members",
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
                            "Согласие на получение кредитного отчёта КАТМ (дата, пользователь и цель)",
                            "KATM kredit hisobotini olishga rozilik (sana, foydalanuvchi va maqsad koʻrsatilgan)",
                            "Consent to obtain the KATM credit report (date, user and purpose stated)",
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
        ],
    },
    {
        "source": "products/02_Xorijiy_til_markazi_320_BHM_qarz.docx, раздел 4",
        "category": "LOANS",
        "names": (
            "«Кўмак+»: дополнительный заём до 730 БРВ",
            "«Koʻmak+»: 730 BHMgacha qoʻshimcha qarz",
            "«Komak+»: additional loan of up to 730 BCU",
        ),
        "descriptions": (
            "Дополнительный беспроцентный заём до 730 БРВ на расширение центра иностранных языков — только для получивших заём «Кўмак» (до 320 БРВ). Положение: глава 3, § 3.",
            "Xorijiy til markazi faoliyatini kengaytirish uchun 730 BHMgacha qoʻshimcha foizsiz qarz — faqat «Koʻmak» (320 BHMgacha) qarzini olganlar uchun. Nizom: 3-bob, 3-§.",
            "Additional interest-free loan of up to 730 BCU to expand a foreign language centre — only for recipients of the «Komak» loan (up to 320 BCU). Regulation: chapter 3, § 3.",
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
                            "Заявление в Фонд о дополнительном займе (подпись руководителя, печать при наличии)",
                            "Jamgʻarmaga qoʻshimcha qarz soʻrash toʻgʻrisida ariza (rahbar imzosi, muhr mavjud boʻlsa)",
                            "Application to the Fund for an additional loan (signed by the head, sealed if applicable)",
                        ),
                    ),
                    field(
                        "STRING",
                        (
                            "Номер и дата договора займа «Кўмак»",
                            "«Koʻmak» qarz shartnomasining raqami va sanasi",
                            "Number and date of the «Komak» loan agreement",
                        ),
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
                            "План расширения деятельности, смета расходов и бизнес-план",
                            "Faoliyatni kengaytirish rejasi, xarajatlar smetasi va biznes-reja",
                            "Business expansion plan, cost estimate and business plan",
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
                    field(
                        "PHOTO",
                        ("Фото залога", "Garov fotosuratlari", "Photos of the pledged property"),
                        required=False,
                        max_files=8,
                    ),
                    field(
                        "FILE",
                        (
                            "Иной вид обеспечения, предусмотренный законодательством",
                            "Qonunchilikda nazarda tutilgan boshqa taʼminot turi",
                            "Other collateral provided by law",
                        ),
                        required=False,
                        max_files=3,
                    ),
                ],
            ),
        ],
    },
    {
        "source": "products/09_Oquv_kurs_inkubatsiya_xarajatlari.docx, разделы 1 и 4",
        "category": "COMPENSATION",
        "names": (
            "Участие в международных программах инкубации и акселерации",
            "Xalqaro inkubatsiya va akseleratsiya dasturlarida ishtirok etish",
            "Participation in international incubation and acceleration programmes",
        ),
        "descriptions": (
            "Возмещение 50% расходов на участие в престижных международных программах инкубации или акселерации, не более 20 000 долларов США. Положение: глава 4, § 3.",
            "Nufuzli xalqaro inkubatsiya yoki akseleratsiya dasturlarida ishtirok etish xarajatlarining 50 foizini, 20 000 AQSh dollaridan oshmagan miqdorda qoplash. Nizom: 4-bob, 3-§.",
            "Reimbursement of 50% of the costs of prestigious international incubation or acceleration programmes, up to USD 20,000. Regulation: chapter 4, § 3.",
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
                ("Программа", "Dastur", "Programme"),
                fields=[
                    field(
                        "RADIO",
                        ("Вид программы", "Dastur turi", "Programme type"),
                        options=(
                            ("Инкубация", "Inkubatsiya", "Incubation"),
                            ("Акселерация", "Akseleratsiya", "Acceleration"),
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Документ об успешном завершении программы",
                            "Dasturni muvaffaqiyatli tamomlaganini tasdiqlovchi hujjat",
                            "Proof of successful completion of the programme",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Договор и (или) оферта",
                            "Shartnoma va (yoki) oferta",
                            "Contract and/or offer",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Платёжное поручение, документы SWIFT и (или) инвойсы",
                            "Toʻlov topshiriqnomasi, SWIFT hujjatlari va (yoki) invoyslar",
                            "Payment order, SWIFT documents and/or invoices",
                        ),
                        max_files=3,
                    ),
                    field(
                        "FILE",
                        (
                            "MVP (для акселерации)",
                            "MVP (akseleratsiya uchun)",
                            "MVP (for acceleration)",
                        ),
                        max_files=3,
                        when=("Вид программы", ("Акселерация",)),
                    ),
                ],
            ),
        ],
    },
    {
        "source": "products/09_Oquv_kurs_inkubatsiya_xarajatlari.docx, разделы 1 и 3",
        "category": "COMPENSATION",
        "names": (
            "Взнос за участие в местных программах инкубации и акселерации",
            "Mahalliy inkubatsiya va akseleratsiya dasturida ishtirok etish badali",
            "Fee for local incubation and acceleration programmes",
        ),
        "descriptions": (
            "Возмещение взноса за участие в местной программе инкубации или акселерации из утверждённого перечня, до 100 БРВ. Положение: глава 4, § 3.",
            "Tasdiqlangan roʻyxatdagi mahalliy inkubatsiya yoki akseleratsiya dasturida ishtirok etish badalini 100 BHMgacha qoplash. Nizom: 4-bob, 3-§.",
            "Reimbursement of the fee for a local incubation or acceleration programme from the approved list, up to 100 BCU. Regulation: chapter 4, § 3.",
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
                ("Программа", "Dastur", "Programme"),
                fields=[
                    field(
                        "RADIO",
                        ("Вид программы", "Dastur turi", "Programme type"),
                        options=(
                            ("Инкубация", "Inkubatsiya", "Incubation"),
                            ("Акселерация", "Akseleratsiya", "Acceleration"),
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
                            "Договор с организатором программы из утверждённого перечня",
                            "Tasdiqlangan roʻyxatdagi dastur tashkilotchisi bilan shartnoma",
                            "Contract with an organiser from the approved list",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "MVP (для акселерации)",
                            "MVP (akseleratsiya uchun)",
                            "MVP (for acceleration)",
                        ),
                        max_files=3,
                        when=("Вид программы", ("Акселерация",)),
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


# Продукты прежней миграции, которых нет в списке Фонда из 20 продуктов.
REMOVED_PRODUCTS = (
    "Брендинг для победителей чемпионата «Ёш тадбиркорлар»",
    "Программы «Combinator»",
    "Стартап-курсы, инкубация и акселерация",
)
REMOVED_CATEGORY = "Программы"


def _remove_products(conn) -> None:
    for name in REMOVED_PRODUCTS:
        ids = (
            conn.execute(
                sa.text(
                    "SELECT product_id FROM product_translations WHERE language = 'ru' AND name = :n"
                ),
                {"n": name},
            )
            .scalars()
            .all()
        )
        for product_id in ids:
            used = conn.execute(
                sa.text("SELECT 1 FROM applications WHERE product_id = :id LIMIT 1"),
                {"id": product_id},
            ).scalar()
            if used:
                conn.execute(
                    sa.text("UPDATE products SET status = 'ARCHIVED' WHERE id = :id"),
                    {"id": product_id},
                )
                _log(f"«{name}» has applications — archived (id {product_id})")
            else:
                conn.execute(sa.text("DELETE FROM products WHERE id = :id"), {"id": product_id})
                _log(f"«{name}» deleted (id {product_id})")
    conn.execute(
        sa.text(
            "DELETE FROM product_categories c USING product_category_translations t "
            "WHERE t.category_id = c.id AND t.language = 'ru' AND t.name = :n "
            "AND NOT EXISTS (SELECT 1 FROM products p WHERE p.category_id = c.id)"
        ),
        {"n": REMOVED_CATEGORY},
    )


def upgrade() -> None:
    conn = op.get_bind()
    for product in PRODUCTS:
        _create_product(conn, product)
    _remove_products(conn)


def downgrade() -> None:
    # Продукты удаляются через API Фонда (DELETE /fund/products/{id}), если по ним нет заявок.
    pass
