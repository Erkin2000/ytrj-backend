"""Продукты Фонда из перечней документов (папка products/, Положение Фонда, глава 3).

Сюда вошли займы и ссуды 01–07: продукты с банком, заявка идёт Фонд → Совет → банк.
Возмещения расходов (08–12, 15) — в seed_data_reimbursement.py, это продукты без банка.
Инвестиции (13, 14) и Combinator (16) пока не заводятся.

Не вошли разделы, которые оформляет сам Фонд (решение Совета, договоры, мониторинг),
и разделы «после одобрения» (следующие транши, дополнительный заём).
Условные документы (по цели займа, только для юрлица, только при импорте) — необязательные.

Переводы: (ru, uz, en); uz — латиницей.
"""

T = tuple[str, str, str]

CATEGORY: dict = {
    "translations": (
        ("Займы и ссуды", "Qarzlar va ssudalar", "Loans"),
        (
            "Займы и беспроцентные ссуды Фонда (Положение, глава 3).",
            "Jamgʻarmaning qarzlari va foizsiz ssudalari (Nizom, 3-bob).",
            "Fund loans and interest-free loans (Regulation, chapter 3).",
        ),
    ),
    "sort_order": 1,
}

# ---------- документы, которые повторяются в разных продуктах ----------

DOCS: dict[str, T] = {
    "amount": (
        "Запрашиваемая сумма, сум",
        "Soʻralayotgan summa, soʻm",
        "Requested amount, UZS",
    ),
    "application": (
        "Заявление в Фонд (с указанием суммы; подпись руководителя, печать при наличии)",
        "Jamgʻarmaga ariza (soʻralayotgan summa koʻrsatilgan; rahbar imzosi, muhr mavjud boʻlsa)",
        "Application to the Fund (stating the amount; signed by the head, sealed if applicable)",
    ),
    "consent_state": (
        "Письменное согласие на получение Фондом сведений о заявителе из госорганов",
        "Jamgʻarma davlat organlaridan tashabbuskor haqida maʼlumot olishiga yozma rozilik",
        "Written consent for the Fund to obtain information about the applicant from state bodies",
    ),
    "no_affiliation": (
        "Подтверждение отсутствия аффилированности с Агентством, членами Совета, Фондом и Yoshlar ventures",
        "Agentlik, Kengash aʼzolari, Jamgʻarma va Yoshlar ventures bilan affillanganlik yoʻqligi tasdigʻi",
        "Confirmation of no affiliation with the Agency, Council members, the Fund and Yoshlar ventures",
    ),
    "charter": (
        "Учредительные документы (устав, учредительный договор; при одном учредителе — устав)",
        "Taʼsis hujjatlari (ustav, taʼsis shartnomasi; yagona taʼsischida — ustav)",
        "Founding documents (charter, founders' agreement; charter only for a sole founder)",
    ),
    "registration": (
        "Свидетельство о государственной регистрации",
        "Davlat roʻyxatidan oʻtganlik guvohnomasi",
        "State registration certificate",
    ),
    "director": (
        "Приказ о назначении руководителя, паспорт или ID-карта руководителя",
        "Rahbarni tayinlash toʻgʻrisida buyruq, rahbarning pasporti yoki ID-kartasi",
        "Order appointing the head, head's passport or ID card",
    ),
    "director_signature": (
        "Приказ о назначении руководителя, паспорт или ID-карта и образец подписи",
        "Rahbarni tayinlash toʻgʻrisida buyruq, pasport yoki ID-karta va imzo namunasi",
        "Order appointing the head, passport or ID card and specimen signature",
    ),
    "passport": (
        "Паспорт или ID-карта",
        "Pasport yoki ID-karta",
        "Passport or ID card",
    ),
    "business_plan": (
        "Технико-экономическое обоснование или бизнес-план проекта",
        "Loyihaning texnik-iqtisodiy asoslanishi yoki biznes-reja",
        "Feasibility study or business plan of the project",
    ),
    "premises_right": (
        "Документ о праве собственности, аренды или безвозмездного пользования зданием",
        "Binoga mulk, ijara yoki tekin foydalanish huquqini tasdiqlovchi hujjat",
        "Document confirming ownership, lease or free use of the building",
    ),
    "tax_debt": (
        "Справка об отсутствии налоговой задолженности (юрлицо, учредители, руководитель)",
        "Soliq qarzi mavjud emasligi toʻgʻrisida maʼlumotnoma (yuridik shaxs, taʼsischilar, rahbar)",
        "Certificate of no tax debt (legal entity, founders, head)",
    ),
    "mib_debt": (
        "Справка об отсутствии задолженности в Бюро принудительного исполнения",
        "Majburiy ijro byurosida qarzdorlik yoʻqligi toʻgʻrisida maʼlumot",
        "Certificate of no debt with the Compulsory Enforcement Bureau",
    ),
    "credit_bureau": (
        "Справка кредитного бюро «Кредитно-информационный аналитический центр» (КАТМ)",
        "“Kredit-axborot tahliliy markazi” kredit byurosi maʼlumotnomasi (KATM)",
        "Credit bureau report of the Credit Information Analytical Centre (KATM)",
    ),
    "credit_consent": (
        "Согласие на получение кредитного отчёта (дата, пользователь и цель)",
        "Kredit hisobotini olishga rozilik (sana, foydalanuvchi va maqsad koʻrsatilgan)",
        "Consent to obtain the credit report (date, user and purpose stated)",
    ),
    "bank_account": (
        "Справка о банковском счёте",
        "Hisobvaraq toʻgʻrisida maʼlumotnoma",
        "Bank account certificate",
    ),
    "insurance": (
        "Страховой полис на возврат непогашенной части займа",
        "Qarzning qaytarilmagan qismini toʻliq qaytarish majburiyatini olgan sugʻurta polisi",
        "Insurance policy covering repayment of the outstanding loan",
    ),
    "guarantee_b": (
        "Поручительство юрлица с рейтингом не ниже «B» (56–65 баллов)",
        "Reytingi kamida “B” (56–65 ball) boʻlgan yuridik shaxsning kafillik xati",
        "Guarantee letter from a legal entity rated at least “B” (56–65 points)",
    ),
    "pledge": (
        "Залог имущества: кадастр, свидетельство о праве или выписка из реестра, отчёт об оценке",
        "Mol-mulk garovi: kadastr, huquq guvohnomasi yoki reestrdan koʻchirma, baholash hisoboti",
        "Property pledge: cadastre, title certificate or registry extract, valuation report",
    ),
    "third_party_guarantee": (
        "Поручительство третьего лица: письмо поручителя и его документы (паспорт, КАТМ, доход)",
        "Uchinchi shaxs kafilligi: kafillik xati va kafil hujjatlari (pasport, KATM, ish haqi)",
        "Third-party guarantee: guarantor's letter and documents (passport, KATM, income)",
    ),
    "insurance_policy": (
        "Страховой полис",
        "Sugʻurta polisi",
        "Insurance policy",
    ),
    "contract_legal_opinion": (
        "Юридическое заключение о соответствии договора законодательству (при необходимости — ценовая экспертиза)",
        "Shartnomaning qonunchilikka muvofiqligi yuzasidan yuridik xulosa (zarur hollarda narx ekspertizasi)",
        "Legal opinion on the contract's compliance with the law (price expertise if needed)",
    ),
    "three_offers": (
        "3 коммерческих предложения от разных организаций (одно — от поставщика по договору)",
        "Turli tashkilotlardan 3 ta tijorat taklifi (biri shartnoma imzolangan korxonadan)",
        "3 commercial offers from different companies (one from the contracted supplier)",
    ),
}

# Поле: (ключ DOCS или свой перевод (ru, uz, en), тип, обязательное, max_files)
F = tuple

APPLICATION_STAGE: T = ("Заявление и сумма", "Ariza va summa", "Application and amount")
GENERAL_STAGE: T = ("Общие документы", "Umumiy hujjatlar", "General documents")
COLLATERAL_STAGE: T = ("Обеспечение", "Taʼminot", "Collateral")
LEGAL_STAGE: T = (
    "Дополнительно для юридического лица",
    "Yuridik shaxs uchun qoʻshimcha",
    "Additional for a legal entity",
)


def amount_stage(*docs: F) -> tuple:
    return (
        APPLICATION_STAGE,
        [("amount", "NUMBER", True, 1), ("application", "FILE", True, 1), *docs],
    )


PRODUCTS: list[dict] = [
    # ---------- 01 ----------
    {
        "translations": (
            (
                "Строительство, ремонт и оснащение зданий, сырьё и оборудование",
                "Bino qurish, taʼmirlash va jihozlash, xomashyo va uskuna",
                "Construction, repair and equipping of buildings, raw materials and equipment",
            ),
            (
                "Заём до 10 000 БРВ на строительство, ремонт и оснащение зданий и сооружений, "
                "покупку зданий, сырья для производства, технологий и оборудования. "
                "Положение: глава 3, § 2.",
                "Bino va inshootlarni qurish, taʼmirlash va jihozlash, bino, ishlab chiqarish uchun "
                "xomashyo, texnologiya va asbob-uskuna sotib olish uchun 10 ming BHMgacha qarz. "
                "Nizom: 3-bob, 2-§.",
                "Loan of up to 10,000 BCU for construction, repair and equipping of buildings, "
                "purchase of buildings, production raw materials, technology and equipment. "
                "Regulation: chapter 3, § 2.",
            ),
        ),
        "subject_types": ["MCHJ"],
        "stages": [
            amount_stage(),
            (
                GENERAL_STAGE,
                [
                    ("consent_state", "FILE", True, 1),
                    ("no_affiliation", "FILE", True, 1),
                    ("charter", "FILE", True, 1),
                    ("registration", "FILE", True, 1),
                    ("director", "FILE", True, 1),
                    (
                        (
                            "Решение учредителей о получении займа (если сделка > 25% чистых активов или по уставу)",
                            "Qarz olish boʻyicha taʼsischilar qarori (bitim sof aktivlarning 25% dan oshsa yoki ustav talab qilsa)",
                            "Founders' decision to borrow (if the deal exceeds 25% of net assets or the charter requires)",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    ("business_plan", "FILE", True, 1),
                    (
                        (
                            "Финансовая отчётность за последний отчётный период (формы 1 и 2)",
                            "Oxirgi hisobot davridagi moliyaviy hisobot (1-shakl, 2-shakl)",
                            "Financial statements for the last reporting period (forms 1 and 2)",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Кадастровый документ или договор аренды помещения по месту деятельности",
                            "Faoliyat joyi binosining kadastr hujjati yoki ijara shartnomasi",
                            "Cadastre document or lease agreement for the business premises",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Паспорта или ID-карты учредителей-молодёжи (18–30 лет)",
                            "Taʼsischi yosh fuqarolarning pasporti yoki ID-kartasi (18–30 yosh)",
                            "Passports or ID cards of young founders (aged 18–30)",
                        ),
                        "FILE",
                        False,
                        5,
                    ),
                    (
                        (
                            "План трудоустройства: число рабочих мест, не менее 50% — молодёжь",
                            "Ishga joylashtirish rejasi: ish oʻrinlari soni, kamida 50 foizi yoshlar",
                            "Employment plan: number of jobs, at least 50% for young people",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    (
                        (
                            "Показатель рейтинга устойчивости",
                            "Barqarorlik reytingi koʻrsatkichi",
                            "Sustainability rating",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    ("credit_bureau", "FILE", True, 1),
                    ("credit_consent", "FILE", True, 1),
                    ("bank_account", "FILE", True, 1),
                ],
            ),
            (
                (
                    "Залог (не менее 125% суммы займа)",
                    "Garov taʼminoti (qarz summasining kamida 125 foizi)",
                    "Collateral (at least 125% of the loan)",
                ),
                [
                    (
                        (
                            "Кадастровые документы или технический паспорт недвижимости",
                            "Koʻchmas mulk kadastr hujjatlari yoki texnik pasport",
                            "Cadastre documents or technical passport of the real estate",
                        ),
                        "FILE",
                        True,
                        3,
                    ),
                    (
                        (
                            "Свидетельство о регистрации права на здание и участок или выписка из реестра",
                            "Bino, inshoot va yer uchastkasiga huquq guvohnomasi yoki reestrdan koʻchirma",
                            "Title registration certificate for the building and land or registry extract",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Решение учредителей о передаче имущества в залог",
                            "Garovga taqdim etish boʻyicha taʼsischilar qarori",
                            "Founders' decision to pledge the property",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Согласие всех собственников (если залог — общая совместная собственность), нотариально",
                            "Umumiy birgalikdagi mulk garovga berilsa, barcha mulkdorlarning roziligi (notarius orqali)",
                            "Consent of all co-owners if the pledge is joint property (notarised)",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    (
                        (
                            "Отчёт независимого оценщика о рыночной стоимости",
                            "Bozor bahosi boʻyicha mustaqil baholovchining hisoboti",
                            "Independent appraiser's market value report",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Фото залога снаружи и внутри с 4 сторон",
                            "Garovning ichki va tashqi 4 tomonlama fotosuratlari",
                            "Photos of the pledged property inside and outside from 4 sides",
                        ),
                        "PHOTO",
                        True,
                        8,
                    ),
                    (
                        (
                            "Если залог — транспорт: техпаспорт и страховой полис",
                            "Garov transport vositasi boʻlsa: guvohnoma nusxasi va sugʻurta polisi",
                            "If the pledge is a vehicle: registration certificate and insurance policy",
                        ),
                        "FILE",
                        False,
                        2,
                    ),
                ],
            ),
            (
                ("Для строительства", "Qurilish uchun", "For construction"),
                [
                    (
                        (
                            "Право на земельный участок (договор по итогам аукциона, выписка) или кадастр здания",
                            "Yer uchastkasiga huquq (auksion shartnomasi, reestrdan koʻchirma) yoki bino kadastri",
                            "Land right (auction contract, registry extract) or building cadastre",
                        ),
                        "FILE",
                        False,
                        2,
                    ),
                    (
                        (
                            "Проекты объекта строительства",
                            "Qurilish obyekti loyihalari",
                            "Construction project designs",
                        ),
                        "FILE",
                        False,
                        3,
                    ),
                    (
                        (
                            "Проектно-сметная документация и заключение экспертизы",
                            "Loyiha-smeta hujjatlari va ekspertiza xulosasi",
                            "Design and estimate documents with expert opinion",
                        ),
                        "FILE",
                        False,
                        3,
                    ),
                    (
                        (
                            "Сведения о регистрации объекта для начала строительно-монтажных работ",
                            "Qurilish-montaj ishlarini boshlash uchun obyekt roʻyxatdan oʻtgani haqida maʼlumot",
                            "Registration of the site to start construction works",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    (
                        (
                            "Договор с подрядчиком",
                            "Loyiha tashabbuskori va pudratchi oʻrtasidagi shartnoma",
                            "Contract with the contractor",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    ("contract_legal_opinion", "FILE", False, 1),
                ],
            ),
            (
                ("Для ремонта", "Taʼmirlash uchun", "For repair"),
                [
                    (
                        (
                            "Кадастр или договор аренды ремонтируемого объекта (если это не место деятельности)",
                            "Taʼmirlanadigan obyektning kadastri yoki ijara shartnomasi (faoliyat joyidan boshqa boʻlsa)",
                            "Cadastre or lease of the repaired property (if not the business premises)",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    (
                        (
                            "Смета ремонтных работ (при необходимости — с заключением экспертизы)",
                            "Taʼmirlash ishlarining smeta hujjatlari (zarur hollarda ekspertiza xulosasi bilan)",
                            "Repair cost estimate (with expert opinion if needed)",
                        ),
                        "FILE",
                        False,
                        2,
                    ),
                    (
                        (
                            "Разрешение, если работы его требуют",
                            "Ruxsat talab qilinadigan ishlarda ruxsat maʼlumoti",
                            "Permit, if the works require it",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    (
                        (
                            "Договор с исполнителем работ",
                            "Loyiha tashabbuskori va ish bajaruvchi oʻrtasidagi shartnoma",
                            "Contract with the works contractor",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    ("contract_legal_opinion", "FILE", False, 1),
                ],
            ),
            (
                ("Для оснащения", "Jihozlash uchun", "For equipping"),
                [
                    (
                        (
                            "Перечень и стоимость закупаемого оборудования (спецификация)",
                            "Sotib olinadigan jihozlar roʻyxati va qiymati (spetsifikatsiya)",
                            "List and cost of the equipment to buy (specification)",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    (
                        (
                            "Договор с поставщиком",
                            "Yetkazib beruvchi bilan shartnoma",
                            "Contract with the supplier",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    ("contract_legal_opinion", "FILE", False, 1),
                    ("three_offers", "FILE", False, 3),
                ],
            ),
            (
                ("Для покупки здания", "Bino sotib olish uchun", "For buying a building"),
                [
                    (
                        (
                            "Кадастровые документы приобретаемой недвижимости",
                            "Sotib olinayotgan koʻchmas mulkning kadastr hujjatlari",
                            "Cadastre documents of the property being bought",
                        ),
                        "FILE",
                        False,
                        2,
                    ),
                    (
                        (
                            "Справка районного отдела архитектуры о том, что объект не подлежит сносу",
                            "Tuman arxitektura boʻlimidan koʻchmas mulk buzilmasligi toʻgʻrisida maʼlumotnoma",
                            "District architecture office certificate that the property is not to be demolished",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    (
                        (
                            "Договор купли-продажи недвижимости",
                            "Koʻchmas mulk oldi-sotdi shartnomasi",
                            "Real estate purchase agreement",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                ],
            ),
            (
                ("Для покупки сырья", "Xomashyo sotib olish uchun", "For buying raw materials"),
                [
                    (
                        (
                            "Договор купли-продажи с поставщиком сырья",
                            "Xomashyo yetkazib beruvchi bilan oldi-sotdi shartnomasi",
                            "Purchase agreement with the raw material supplier",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    ("contract_legal_opinion", "FILE", False, 1),
                ],
            ),
            (
                (
                    "Для покупки технологий и оборудования",
                    "Texnologiya va asbob-uskuna sotib olish uchun",
                    "For buying technology and equipment",
                ),
                [
                    (
                        (
                            "Договор с поставщиком (с приложением)",
                            "Yetkazib beruvchi bilan shartnoma (ilovasi bilan)",
                            "Contract with the supplier (with annex)",
                        ),
                        "FILE",
                        False,
                        2,
                    ),
                    ("contract_legal_opinion", "FILE", False, 1),
                    ("three_offers", "FILE", False, 3),
                    (
                        (
                            "При импорте: подписанный импортный контракт со спецификацией",
                            "Import qilinganda: toʻliq imzolangan import shartnomasi, spetsifikatsiyasi bilan",
                            "If imported: signed import contract with specification",
                        ),
                        "FILE",
                        False,
                        2,
                    ),
                    (
                        (
                            "При импорте: ценовая экспертиза импортного контракта",
                            "Import qilinganda: import shartnomasiga narx boʻyicha ekspertiza xulosasi",
                            "If imported: price expertise of the import contract",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    (
                        (
                            "При импорте: заключение областного отдела внешнеэкономической деятельности",
                            "Import qilinganda: viloyat tashqi iqtisodiy faoliyat boʻlimining xulosasi",
                            "If imported: opinion of the regional foreign economic activity department",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                ],
            ),
        ],
    },
    # ---------- 02 ----------
    {
        "translations": (
            (
                "Центр иностранных языков в отдалённых районах",
                "Olis hududlarda xorijiy til markazi",
                "Foreign language centre in remote areas",
            ),
            (
                "Беспроцентная ссуда до 320 БРВ на организацию обучения иностранным языкам "
                "в отдалённых и периферийных районах. Положение: глава 3, § 3.",
                "Olis va chekka hududlarda xorijiy tillarga oʻqitish xizmatlarini tashkil etish uchun "
                "320 BHMgacha foizsiz qarz (ssuda). Nizom: 3-bob, 3-§.",
                "Interest-free loan of up to 320 BCU to organise foreign language teaching "
                "in remote areas. Regulation: chapter 3, § 3.",
            ),
        ),
        "subject_types": ["YATT", "MCHJ"],
        "stages": [
            amount_stage(),
            (
                GENERAL_STAGE,
                [
                    ("passport", "FILE", True, 1),
                    ("registration", "FILE", True, 1),
                    (
                        (
                            "Сертификат по иностранному языку не ниже C1 (не старше 2 лет)",
                            "Xorijiy til boʻyicha kamida C1 darajadagi sertifikat (olinganiga 2 yildan oshmagan)",
                            "Foreign language certificate of at least C1 (not older than 2 years)",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Документ о месте деятельности в махалле из приложения 3 к Положению (кадастр или аренда)",
                            "Faoliyat manzili Nizomning 3-ilovasidagi mahallada ekanini tasdiqlovchi hujjat",
                            "Proof that the business is in a mahalla listed in Annex 3 (cadastre or lease)",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Смета расходов и бизнес-план (не менее 20% учеников — из «Ёшлар дафтари»)",
                            "Xarajatlar smetasi va biznes-reja (oʻquvchilarning kamida 20 foizi “Yoshlar daftari”dan)",
                            "Cost estimate and business plan (at least 20% of students from the Youth Register)",
                        ),
                        "FILE",
                        True,
                        2,
                    ),
                    ("bank_account", "FILE", True, 1),
                ],
            ),
            (
                LEGAL_STAGE,
                [
                    ("charter", "FILE", False, 1),
                    (
                        (
                            "Решение и приказ об учреждении",
                            "Taʼsis qarori va buyrugʻi",
                            "Founding decision and order",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    ("director_signature", "FILE", False, 1),
                ],
            ),
            (
                (
                    "Обеспечение (один или несколько видов)",
                    "Taʼminot (bir yoki bir nechta turi)",
                    "Collateral (one or more types)",
                ),
                [
                    ("third_party_guarantee", "FILE", False, 3),
                    ("insurance_policy", "FILE", False, 1),
                    ("pledge", "FILE", False, 3),
                ],
            ),
        ],
    },
    # ---------- 03 ----------
    {
        "translations": (
            (
                "Стартап-студии, инкубаторы и акселераторы",
                "Startap studiyalar, inkubatsiya va akseleratsiya markazlari",
                "Startup studios, incubators and accelerators",
            ),
            (
                "Беспроцентный заём до 5 млрд сум на создание стартап-студий, центров инкубации "
                "и акселерации. Положение: глава 3, § 4.",
                "Startap studiyalar, inkubatsiya va akseleratsiya markazlarini tashkil etish uchun "
                "5 mlrd soʻmgacha foizsiz qarz. Nizom: 3-bob, 4-§.",
                "Interest-free loan of up to UZS 5 billion to set up startup studios, incubation "
                "and acceleration centres. Regulation: chapter 3, § 4.",
            ),
        ),
        "subject_types": ["MCHJ"],
        "stages": [
            amount_stage(),
            (
                GENERAL_STAGE,
                [
                    ("no_affiliation", "FILE", True, 1),
                    ("charter", "FILE", True, 1),
                    ("registration", "FILE", True, 1),
                    ("director_signature", "FILE", True, 1),
                    (
                        (
                            "Подтверждение регистрации на единой электронной платформе стартап-экосистемы",
                            "Startap ekotizimining yagona elektron platformasida roʻyxatdan oʻtganlik tasdigʻi",
                            "Registration on the unified startup ecosystem platform",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    ("premises_right", "FILE", True, 1),
                    (
                        (
                            "Часть устава, где предусмотрена деятельность стартап-студии или инкубатора",
                            "Ustavda startap studiya yoki inkubatsiya faoliyati nazarda tutilgani (tegishli qismi)",
                            "Charter section providing for startup studio or incubator activity",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Трудовые или гражданско-правовые договоры команды (менеджер, разработчик, ментор)",
                            "Jamoa mavjudligini tasdiqlovchi mehnat yoki fuqarolik-huquqiy shartnomalar",
                            "Employment or service contracts of the team (manager, developer, mentor)",
                        ),
                        "FILE",
                        True,
                        5,
                    ),
                    ("tax_debt", "FILE", True, 1),
                    ("mib_debt", "FILE", True, 1),
                    (
                        (
                            "Документы о деятельности стартап-студии или инкубатора не менее 6 месяцев",
                            "Kamida 6 oy startap studiya yoki inkubatsiya faoliyatini yuritganini tasdiqlovchi hujjatlar",
                            "Proof of at least 6 months of startup studio or incubator activity",
                        ),
                        "FILE",
                        True,
                        5,
                    ),
                    (
                        (
                            "План деятельности стартап-студии или инкубатора",
                            "Startap studiya yoki inkubatsiya faoliyatini amalga oshirish rejasi",
                            "Activity plan of the startup studio or incubator",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Смета расходов на реализацию плана",
                            "Rejani amalga oshirish bilan bogʻliq xarajatlar smetasi",
                            "Cost estimate for the plan",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    ("bank_account", "FILE", True, 1),
                ],
            ),
            (
                (
                    "Обеспечение: заём до 300 млн сум (один из видов)",
                    "Taʼminot: 300 mln soʻmgacha qarz (biri)",
                    "Collateral: loan up to UZS 300 million (one type)",
                ),
                [
                    ("insurance", "FILE", False, 1),
                    ("guarantee_b", "FILE", False, 1),
                    ("pledge", "FILE", False, 3),
                ],
            ),
            (
                (
                    "Обеспечение: заём свыше 300 млн сум",
                    "Taʼminot: 300 mln soʻmdan ortiq qarz",
                    "Collateral: loan over UZS 300 million",
                ),
                [
                    (
                        (
                            "Подтверждение инвестиций в поддержанные стартапы не менее 10 000 $",
                            "Qoʻllab-quvvatlangan startaplar kamida 10 000 AQSh dollari investitsiya jalb qilganini tasdiqlovchi hujjatlar",
                            "Proof that supported startups raised at least USD 10,000 of investment",
                        ),
                        "FILE",
                        False,
                        5,
                    ),
                    (
                        (
                            "Поручительство юрлица с рейтингом не ниже «BB» (66–75 баллов) или документы залога",
                            "Reytingi kamida “BB” (66–75 ball) boʻlgan yuridik shaxsning kafillik xati yoki garov hujjatlari",
                            "Guarantee from a legal entity rated at least “BB” (66–75 points) or pledge documents",
                        ),
                        "FILE",
                        False,
                        3,
                    ),
                ],
            ),
        ],
    },
    # ---------- 04 ----------
    {
        "translations": (
            (
                "«Янги авлод тадбиркорлари»: ссуда выпускникам программы",
                "“Yangi avlod tadbirkorlari”: dastur bitiruvchilariga ssuda",
                "“New Generation Entrepreneurs”: loan for programme graduates",
            ),
            (
                "Ссуда до 500 БРВ выпускникам программы «Янги авлод тадбиркорлари» "
                "(обучение оплачивает Фонд). Положение: глава 3, § 5.",
                "“Yangi avlod tadbirkorlari” dasturi bitiruvchilariga 500 BHMgacha ssuda "
                "(oʻqitish Jamgʻarma hisobidan). Nizom: 3-bob, 5-§.",
                "Loan of up to 500 BCU for graduates of the “New Generation Entrepreneurs” "
                "programme (training paid by the Fund). Regulation: chapter 3, § 5.",
            ),
        ),
        "subject_types": ["YATT", "MCHJ", "SELF_EMPLOYED"],
        "stages": [
            amount_stage(),
            (
                GENERAL_STAGE,
                [
                    ("passport", "FILE", True, 1),
                    (
                        (
                            "Сертификат Агентства",
                            "Agentlik sertifikati nusxasi",
                            "Agency certificate",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Бизнес-проект (спрос, конкурентоспособность, расходы, доходы, рентабельность, срок окупаемости)",
                            "Biznes loyiha (bozor ehtiyoji, raqobatbardoshlik, xarajat, daromad, rentabellik, daromadga chiqish muddati)",
                            "Business project (demand, competitiveness, costs, income, profitability, payback period)",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Справка об отсутствии налоговой задолженности",
                            "Soliq qarzi mavjud emasligi toʻgʻrisida maʼlumotnoma",
                            "Certificate of no tax debt",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    ("mib_debt", "FILE", True, 1),
                    (
                        (
                            "Справка о наличии или отсутствии судимости",
                            "Sudlanmaganlik (yoki sudlanganlik) toʻgʻrisida maʼlumotnoma",
                            "Criminal record certificate",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    ("registration", "FILE", True, 1),
                    ("bank_account", "FILE", True, 1),
                ],
            ),
            (
                ("Поручитель", "Kafil", "Guarantor"),
                [
                    (
                        (
                            "Паспорт, сведения о доходе и КАТМ поручителя",
                            "Kafilning pasporti, ish haqi va KATM maʼlumoti",
                            "Guarantor's passport, income and KATM report",
                        ),
                        "FILE",
                        True,
                        3,
                    ),
                    (
                        (
                            "Справка об отсутствии налоговой задолженности поручителя",
                            "Kafilning soliq qarzi mavjud emasligi toʻgʻrisida maʼlumotnoma",
                            "Guarantor's certificate of no tax debt",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Справка об отсутствии задолженности поручителя в Бюро принудительного исполнения",
                            "Kafilning Majburiy ijro byurosida qarzdorlik yoʻqligi toʻgʻrisida maʼlumot",
                            "Guarantor's certificate of no debt with the Compulsory Enforcement Bureau",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                ],
            ),
        ],
    },
    # ---------- 05 ----------
    {
        "translations": (
            (
                "Book cafe и книжные магазины",
                "Book cafe va kitob doʻkonlari",
                "Book cafes and bookshops",
            ),
            (
                "Ссуда до 1 млрд сум на расширение деятельности Book cafe или книжного магазина. "
                "Положение: глава 3, § 6.",
                "“Book cafe” yoki kitob doʻkoni faoliyatini kengaytirish uchun 1 mlrd soʻmgacha ssuda. "
                "Nizom: 3-bob, 6-§.",
                "Loan of up to UZS 1 billion to expand a book cafe or bookshop. "
                "Regulation: chapter 3, § 6.",
            ),
        ),
        "subject_types": ["MCHJ"],
        "stages": [
            amount_stage(),
            (
                GENERAL_STAGE,
                [
                    ("consent_state", "FILE", True, 1),
                    ("no_affiliation", "FILE", True, 1),
                    ("charter", "FILE", True, 1),
                    ("registration", "FILE", True, 1),
                    (
                        (
                            "Приказ о назначении руководителя, решение о получении ссуды, паспорт или ID-карта",
                            "Rahbarni tayinlash toʻgʻrisida buyruq, ssuda olish boʻyicha qaror, pasport yoki ID-karta",
                            "Order appointing the head, decision to take the loan, passport or ID card",
                        ),
                        "FILE",
                        True,
                        2,
                    ),
                    (
                        (
                            "Подтверждение продажи более 10 000 книг в месяц (онлайн-касса, счета-фактуры)",
                            "Oyiga 10 mingdan ortiq kitob sotilganini tasdiqlovchi hujjat (onlayn-kassa, hisobvaraq-fakturalar)",
                            "Proof of selling over 10,000 books a month (online till, invoices)",
                        ),
                        "FILE",
                        True,
                        3,
                    ),
                    ("premises_right", "FILE", True, 1),
                    ("tax_debt", "FILE", True, 1),
                    ("mib_debt", "FILE", True, 1),
                    ("credit_bureau", "FILE", True, 1),
                    ("credit_consent", "FILE", True, 1),
                    ("business_plan", "FILE", True, 1),
                ],
            ),
            (
                COLLATERAL_STAGE,
                [
                    (
                        (
                            "Поручительство или документы залога (кадастр, право собственности, оценка)",
                            "Kafillik xati yoki garov hujjatlari (kadastr, huquq guvohnomasi, baholash hisoboti)",
                            "Guarantee letter or pledge documents (cadastre, title, valuation)",
                        ),
                        "FILE",
                        True,
                        3,
                    ),
                ],
            ),
        ],
    },
    # ---------- 06 ----------
    {
        "translations": (
            (
                "Ремесленные мастерские-лаборатории",
                "Kasb-hunar ustaxona-laboratoriyalari",
                "Vocational workshop laboratories",
            ),
            (
                "Беспроцентная ссуда до 1 200 БРВ на создание мастерской-лаборатории для обучения "
                "ремёслам. Положение: глава 3, § 7.",
                "Kasb-hunar ustaxona-laboratoriyasini tashkil etish uchun 1 200 BHMgacha foizsiz ssuda. "
                "Nizom: 3-bob, 7-§.",
                "Interest-free loan of up to 1,200 BCU to set up a vocational workshop laboratory. "
                "Regulation: chapter 3, § 7.",
            ),
        ),
        "subject_types": ["MCHJ"],
        "stages": [
            amount_stage(),
            (
                GENERAL_STAGE,
                [
                    ("no_affiliation", "FILE", True, 1),
                    ("charter", "FILE", True, 1),
                    ("registration", "FILE", True, 1),
                    ("director_signature", "FILE", True, 1),
                    (
                        (
                            "Документ на собственное здание или договор долгосрочной аренды",
                            "Oʻz egaligidagi bino hujjati yoki uzoq muddatli ijara shartnomasi",
                            "Title to own building or long-term lease agreement",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    ("tax_debt", "FILE", True, 1),
                    ("mib_debt", "FILE", True, 1),
                    ("credit_bureau", "FILE", True, 1),
                    ("business_plan", "FILE", True, 1),
                    (
                        (
                            "Договоры со специалистами с опытом обучения ремеслу и подтверждение их опыта",
                            "Kasb-hunarga oʻrgatish tajribasiga ega mutaxassislar shartnomalari va tajribasini tasdiqlovchi hujjat",
                            "Contracts with craft-teaching specialists and proof of their experience",
                        ),
                        "FILE",
                        True,
                        5,
                    ),
                    ("bank_account", "FILE", True, 1),
                ],
            ),
            (
                (
                    "Обеспечение (один из видов)",
                    "Taʼminot (biri)",
                    "Collateral (one type)",
                ),
                [
                    ("insurance", "FILE", False, 1),
                    ("guarantee_b", "FILE", False, 1),
                ],
            ),
        ],
    },
    # ---------- 07 ----------
    {
        "translations": (
            (
                "Передвижные магазины",
                "Koʻchma doʻkonlar",
                "Mobile shops",
            ),
            (
                "Ссуда до 500 млн сум на начало торговли и услуг в передвижных магазинах. "
                "Положение: глава 3, § 8.",
                "Koʻchma doʻkonlarda savdo va xizmat koʻrsatish faoliyatini boshlash uchun "
                "500 mln soʻmgacha ssuda. Nizom: 3-bob, 8-§.",
                "Loan of up to UZS 500 million to start trade and services in mobile shops. "
                "Regulation: chapter 3, § 8.",
            ),
        ),
        "subject_types": ["YATT", "MCHJ"],
        "stages": [
            amount_stage(),
            (
                GENERAL_STAGE,
                [
                    ("no_affiliation", "FILE", True, 1),
                    ("registration", "FILE", True, 1),
                    (
                        (
                            "Справка об отсутствии налоговой задолженности (ИП или юрлицо, учредители, руководитель)",
                            "YaTT va yuridik shaxs, taʼsischilar va rahbarning soliq qarzi mavjud emasligi toʻgʻrisida maʼlumotnoma",
                            "Certificate of no tax debt (sole trader or legal entity, founders, head)",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Право на место передвижной торговли: QR-свидетельство E-auksion или договор с собственником",
                            "Koʻchma savdo joyiga huquq: E-auksion QR-kodli guvohnomasi yoki mulkdor bilan shartnoma",
                            "Right to the mobile trading spot: E-auksion QR certificate or contract with the owner",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    ("credit_bureau", "FILE", True, 1),
                    ("business_plan", "FILE", True, 1),
                    (
                        (
                            "Договор или коммерческое предложение на покупку передвижного магазина и оборудования",
                            "Koʻchma doʻkon, jihoz va asbob-uskuna xarid qilish shartnomasi yoki tijorat taklifi",
                            "Contract or offer to buy the mobile shop and equipment",
                        ),
                        "FILE",
                        True,
                        2,
                    ),
                    ("bank_account", "FILE", True, 1),
                ],
            ),
            (
                (
                    "Дополнительно для ИП",
                    "Yakka tartibdagi tadbirkor uchun qoʻshimcha",
                    "Additional for a sole trader",
                ),
                [("passport", "FILE", False, 1)],
            ),
            (
                LEGAL_STAGE,
                [
                    ("charter", "FILE", False, 1),
                    (
                        (
                            "Приказ и решение о назначении руководителя и о получении займа, паспорт или ID-карта",
                            "Rahbarni tayinlash va qarz olish boʻyicha buyruq va qaror, pasport yoki ID-karta",
                            "Order and decision appointing the head and on borrowing, passport or ID card",
                        ),
                        "FILE",
                        False,
                        2,
                    ),
                ],
            ),
            (
                (
                    "Обеспечение (один или несколько видов)",
                    "Taʼminot (bir yoki bir nechta turi)",
                    "Collateral (one or more types)",
                ),
                [
                    (
                        (
                            "Поручительство третьего лица (паспорт, КАТМ, доход; для юрлица — письмо, устав, рейтинг)",
                            "Uchinchi shaxs kafilligi (pasport, KATM, ish haqi; yuridik shaxs — kafillik xati, taʼsis hujjatlari, reyting)",
                            "Third-party guarantee (passport, KATM, income; for a company — letter, charter, rating)",
                        ),
                        "FILE",
                        False,
                        3,
                    ),
                    ("insurance_policy", "FILE", False, 1),
                    ("pledge", "FILE", False, 3),
                    (
                        (
                            "Иное обеспечение: покупаемый передвижной магазин (техпаспорт)",
                            "Boshqa taʼminot: sotib olinayotgan koʻchma doʻkon (texpasport)",
                            "Other collateral: the mobile shop being bought (registration certificate)",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                ],
            ),
        ],
    },
]
