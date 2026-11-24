"""Обновлённые анкеты продуктов по новым docx из `products/`

Revision ID: 7b9d1f3a5c8e
Revises: d9f1b3c5e7a0
Create Date: 2026-11-24

- 03 «Стартап-студии, инкубаторы и акселераторы» (`03_… (2).docx`): обеспечение займа до 300 млн —
  теперь один документ на выбор (полис, или поручительство с рейтингом «B», или залог). В этапе 1
  добавлен выбор «Сумма займа: до 300 млн / свыше 300 млн»: этап обеспечения до 300 млн
  показывается только при «до 300 млн», этап свыше 300 млн — только при «свыше 300 млн»; документы
  обеспечения стали обязательными для своего диапазона. Заявление — с указанием СТИР.
- «Взнос за участие в местных программах инкубации и акселерации» (`xalqaro inkubatsiya
  akseleratsiya.docx`, раздел 3): платформа startupbase; договор с организатором программы (без
  «из утверждённого перечня»); для акселерации — ссылка на MVP и заключение специалиста по
  техническому DD.

Разделы 1 и 4 этого файла (международные программы) и новые 08, 10, 11 совпадают с текущими
анкетами — их миграция не трогает.

Анкета продукта пересоздаётся целиком (этапы, поля, варианты, условия), только если по продукту
нет заявок: иначе этапы и поля менять нельзя, и продукт пропускается (Фонд делает копию —
`POST /fund/products/{id}/copy`). Название, описание, банки, статус и типы субъекта не меняются.
Downgrade ничего не делает.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7b9d1f3a5c8e"
down_revision: str | Sequence[str] | None = "d9f1b3c5e7a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LANGUAGES = ("ru", "uz", "en")


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


UPDATES = [
    {
        "source": "products/03_Startap_studiya_inkubatsiya_5_mlrd_qarz (2).docx",
        "name": "Стартап-студии, инкубаторы и акселераторы",
        "stages": [
            stage(
                1,
                ("Заявление и сумма", "Ariza va summa", "Application and amount"),
                fields=[
                    field(
                        "RADIO",
                        ("Сумма займа", "Qarz summasi", "Loan amount"),
                        options=(
                            ("До 300 млн сум", "300 mln soʻmgacha", "Up to UZS 300 million"),
                            ("Свыше 300 млн сум", "300 mln soʻmdan ortiq", "Over UZS 300 million"),
                        ),
                    ),
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
                            "Заявление в Фонд (с указанием СТИР и суммы; подпись руководителя, печать при наличии)",
                            "Jamgʻarmaga ariza (STIR va soʻralayotgan summa koʻrsatilgan; rahbar imzosi, muhr mavjud boʻlsa)",
                            "Application to the Fund (stating the TIN and amount; signed by the head, sealed if applicable)",
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
                    "Обеспечение: заём до 300 млн сум",
                    "Taʼminot: 300 mln soʻmgacha qarz",
                    "Collateral: loan up to UZS 300 million",
                ),
                fields=[
                    field(
                        "FILE",
                        (
                            "Один вид обеспечения на выбор: страховой полис на возврат займа, поручительство юрлица с рейтингом не ниже «B» (56–65 баллов) или документы залога (кадастр, право собственности, оценка)",
                            "Taʼminotning bir turi: qarzni qaytarish sugʻurta polisi, reytingi kamida «B» (56–65 ball) yuridik shaxs kafilligi yoki garov hujjatlari (kadastr, huquq guvohnomasi, baholash)",
                            "One type of collateral: loan repayment insurance policy, guarantee from a legal entity rated at least «B» (56–65 points) or pledge documents (cadastre, title, valuation)",
                        ),
                        max_files=5,
                    ),
                ],
                when=("Сумма займа", ("До 300 млн сум",)),
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
                            "Подтверждение, что поддержанные стартапы привлекли инвестиции не менее 10 000 $",
                            "Qoʻllab-quvvatlangan startap loyihalar kamida 10 000 AQSh dollari ekvivalentida investitsiya jalb qilganini tasdiqlovchi hujjatlar",
                            "Proof that the supported startups raised investment of at least USD 10,000",
                        ),
                        max_files=5,
                    ),
                    field(
                        "FILE",
                        (
                            "Поручительство юрлица с рейтингом не ниже «BB» (66–75 баллов) или документы залога",
                            "Reytingi kamida «BB» (66–75 ball) boʻlgan yuridik shaxsning kafillik xati yoki garov taʼminoti hujjatlari",
                            "Guarantee from a legal entity rated at least «BB» (66–75 points) or pledge documents",
                        ),
                        max_files=3,
                    ),
                ],
                when=("Сумма займа", ("Свыше 300 млн сум",)),
            ),
        ],
    },
    {
        "source": "products/xalqaro inkubatsiya akseleratsiya.docx, раздел 3",
        "name": "Взнос за участие в местных программах инкубации и акселерации",
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
                            "Подтверждение регистрации на единой электронной платформе стартап-экосистемы (startupbase)",
                            "Startap ekotizimining yagona elektron platformasida (startupbase) roʻyxatdan oʻtganlik tasdigʻi",
                            "Registration on the unified startup ecosystem platform (startupbase)",
                        ),
                    ),
                    field(
                        "FILE",
                        (
                            "Договор с организатором программы",
                            "Dastur tashkilotchisi bilan tuzilgan shartnoma",
                            "Contract with the programme organiser",
                        ),
                    ),
                    field(
                        "STRING",
                        (
                            "Ссылка на MVP (для акселерации)",
                            "MVP havolasi (akseleratsiya uchun)",
                            "Link to the MVP (for acceleration)",
                        ),
                        when=("Вид программы", ("Акселерация",)),
                    ),
                    field(
                        "FILE",
                        (
                            "Заключение специалиста по техническому DD о MVP (для акселерации)",
                            "MVP boʻyicha texnik DD mutaxassisi xulosasi (akseleratsiya uchun)",
                            "Technical due diligence specialist's opinion on the MVP (for acceleration)",
                        ),
                        when=("Вид программы", ("Акселерация",)),
                    ),
                ],
            ),
        ],
    },
]


def _log(message: str) -> None:
    print(f"[product forms] {message}")


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


def _create_stages(conn, product_id: int, stages: list) -> None:
    # ru-название поля с вариантами → (id поля, {ru-название варианта: id}) — для условий
    controllers: dict[str, tuple[int, dict[str, int]]] = {}

    def condition(when: tuple | None) -> tuple[int | None, list[int] | None]:
        if when is None:
            return None, None
        field_id, options = controllers[when[0]]
        return field_id, [options[name] for name in when[1]]

    for item in stages:
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


def _replace_form(conn, update: dict) -> None:
    ids = (
        conn.execute(
            sa.text(
                "SELECT product_id FROM product_translations WHERE language = 'ru' AND name = :n"
            ),
            {"n": update["name"]},
        )
        .scalars()
        .all()
    )
    if not ids:
        _log(f"«{update['name']}» not found, skipped")
    for product_id in ids:
        used = conn.execute(
            sa.text("SELECT 1 FROM applications WHERE product_id = :id LIMIT 1"),
            {"id": product_id},
        ).scalar()
        if used:
            _log(f"«{update['name']}» (id {product_id}) has applications, form not changed")
            continue
        conn.execute(
            sa.text("DELETE FROM product_stages WHERE product_id = :id"), {"id": product_id}
        )
        _create_stages(conn, product_id, update["stages"])
        _log(f"«{update['name']}» (id {product_id}) form updated")


def upgrade() -> None:
    conn = op.get_bind()
    for update in UPDATES:
        _replace_form(conn, update)


def downgrade() -> None:
    pass
