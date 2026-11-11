"""Категория «Возмещение расходов» (Положение, глава 4): продукты 08–12 и 15.

Продукты без банка (uses_bank=False): заявку одобряет или отклоняет только Фонд.
Инвестиции (13, 14) и Combinator (16) — в других категориях, здесь их нет.
"""

from src.product.seed_data import (
    APPLICATION_STAGE,
    DOCS,
    GENERAL_STAGE,
    LEGAL_STAGE,
)

REIMBURSEMENT_CATEGORY: dict = {
    "translations": (
        ("Возмещение расходов", "Xarajatlarni qoplash", "Expense reimbursement"),
        (
            "Возмещение и оплата расходов стартапов и молодых предпринимателей "
            "(Положение, глава 4).",
            "Startaplar va yosh tadbirkorlar xarajatlarini qoplash va toʻlash (Nizom, 4-bob).",
            "Reimbursement and payment of expenses of startups and young entrepreneurs "
            "(Regulation, chapter 4).",
        ),
    ),
    "sort_order": 2,
}

DOCS.update(
    {
        "amount_reimburse": (
            "Сумма к возмещению, сум",
            "Qoplanadigan summa, soʻm",
            "Amount to reimburse, UZS",
        ),
        "application_plain": (
            "Заявление в Фонд",
            "Jamgʻarmaga ariza",
            "Application to the Fund",
        ),
        "consent_personal": (
            "Письменное согласие на сбор и обработку персональных данных",
            "Shaxsga doir maʼlumotlarni yigʻish va ishlov berishga yozma rozilik",
            "Written consent to the collection and processing of personal data",
        ),
        "payment_proof": (
            "Документ об оплате (заверенный банком или платёжной организацией)",
            "Toʻlovni tasdiqlovchi hujjat nusxasi (bank yoki toʻlov tashkiloti tasdiqlagan)",
            "Proof of payment (certified by a bank or payment institution)",
        ),
        "mvp": (
            "Минимально жизнеспособный продукт (MVP) стартап-идеи",
            "Startap gʻoyaning namunaviy modeli (MVP)",
            "Minimum viable product (MVP) of the startup idea",
        ),
        "acceleration_mvp": (
            "Для акселерации: MVP",
            "Akseleratsiya dasturi uchun: MVP",
            "For acceleration: MVP",
        ),
    }
)


def reimburse_stage() -> tuple:
    return (
        APPLICATION_STAGE,
        [("amount_reimburse", "NUMBER", True, 1), ("application_plain", "FILE", True, 1)],
    )


ALL_SUBJECTS = ["YATT", "MCHJ", "SELF_EMPLOYED"]

REIMBURSEMENT_PRODUCTS: list[dict] = [
    # ---------- 08 ----------
    {
        "translations": (
            (
                "Расходы на экспертов и тренеров (менторов)",
                "Ekspert va trenerlar (mentorlar) xarajatlari",
                "Expert and trainer (mentor) expenses",
            ),
            (
                "Частичное возмещение расходов на иностранных и местных экспертов, тренеров "
                "(менторов) — до 100 млн сум. Положение: глава 4, § 2.",
                "Xorijiy va mahalliy ekspertlar, trenerlar (mentorlar) xarajatlarini qisman "
                "qoplash — 100 mln soʻmgacha. Nizom: 4-bob, 2-§.",
                "Partial reimbursement of foreign and local experts and trainers (mentors) — "
                "up to UZS 100 million. Regulation: chapter 4, § 2.",
            ),
        ),
        "uses_bank": False,
        "subject_types": ALL_SUBJECTS,
        "stages": [
            reimburse_stage(),
            (
                GENERAL_STAGE,
                [
                    ("no_affiliation", "FILE", True, 1),
                    ("passport", "FILE", True, 1),
                    ("consent_personal", "FILE", True, 1),
                    ("mvp", "FILE", True, 3),
                    (
                        (
                            "Заключение привлечённого эксперта (ментора) о создании MVP",
                            "MVP yaratilgani haqida jalb etilgan ekspert, trener (mentor) xulosasi",
                            "Opinion of the engaged expert (mentor) on the MVP",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Целевая бизнес-модель и план коммерциализации",
                            "Maqsadli biznes model va tijoratlashtirish rejasi",
                            "Target business model and commercialisation plan",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Договор с экспертом или тренером (ментором); при трудовых отношениях — трудовой договор",
                            "Ekspert, trener (mentor) bilan shartnoma (mehnat munosabatlarida — mehnat shartnomasi)",
                            "Contract with the expert or trainer (mentor); employment contract if employed",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Подтверждение 3-летнего опыта эксперта в отрасли",
                            "Ekspertning sohadagi 3 yillik tajribasini tasdiqlovchi hujjat",
                            "Proof of the expert's 3 years of industry experience",
                        ),
                        "FILE",
                        True,
                        2,
                    ),
                    (
                        (
                            "Акт выполненных работ, подписанный заявителем и экспертом",
                            "Bajarilgan ishlar boʻyicha tashabbuskor va ekspert tasdiqlagan dalolatnoma",
                            "Certificate of completed work signed by the applicant and the expert",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    ("payment_proof", "FILE", True, 3),
                    (
                        (
                            "Сведения о выплаченной зарплате (при трудовых отношениях)",
                            "Mehnat munosabatlarida toʻlangan ish haqi toʻgʻrisida maʼlumot",
                            "Salary paid (if employed)",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    ("bank_account", "FILE", True, 1),
                ],
            ),
            (
                LEGAL_STAGE,
                [
                    ("charter", "FILE", False, 1),
                    ("registration", "FILE", False, 1),
                    (
                        (
                            "Если юрлицу больше 7 лет: аудиторское заключение, что операциям по стартапу не больше 7 лет",
                            "Yuridik shaxs 7 yildan ortiq faoliyat yuritgan boʻlsa: startap operatsiyalari 7 yildan oshmaganini tasdiqlovchi auditorlik xulosasi",
                            "If the company is over 7 years old: audit opinion that startup operations are under 7 years",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                ],
            ),
        ],
    },
    # ---------- 09 ----------
    {
        "translations": (
            (
                "Стартап-курсы, инкубация и акселерация",
                "Startap oʻquv kurslari, inkubatsiya va akseleratsiya",
                "Startup courses, incubation and acceleration",
            ),
            (
                "Возмещение расходов на стартап-курсы, местные и международные программы "
                "инкубации и акселерации. Положение: глава 4, § 3.",
                "Startap oʻquv kurslari, mahalliy va xalqaro inkubatsiya va akseleratsiya "
                "dasturlari xarajatlarini qoplash. Nizom: 4-bob, 3-§.",
                "Reimbursement of startup courses and local or international incubation and "
                "acceleration programmes. Regulation: chapter 4, § 3.",
            ),
        ),
        "uses_bank": False,
        "subject_types": ALL_SUBJECTS,
        "stages": [
            reimburse_stage(),
            (
                GENERAL_STAGE,
                [
                    ("no_affiliation", "FILE", True, 1),
                    ("passport", "FILE", True, 1),
                    ("consent_personal", "FILE", True, 1),
                    ("bank_account", "FILE", True, 1),
                ],
            ),
            (
                ("Для стартап-курсов", "Startap oʻquv kurslari uchun", "For startup courses"),
                [
                    (
                        (
                            "Договор с организатором курса (направление одобрено Координационным советом)",
                            "Oʻquv kursi tashkilotchisi bilan shartnoma (yoʻnalishi Muvofiqlashtiruvchi kengash tasdiqlagan)",
                            "Contract with the course organiser (field approved by the Coordinating Council)",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    (
                        ("Копия сертификата", "Sertifikat nusxasi", "Certificate copy"),
                        "FILE",
                        False,
                        1,
                    ),
                    ("payment_proof", "FILE", False, 3),
                ],
            ),
            (
                (
                    "Для местных программ инкубации или акселерации",
                    "Mahalliy inkubatsiya yoki akseleratsiya dasturlari uchun",
                    "For local incubation or acceleration programmes",
                ),
                [
                    (
                        (
                            "Подтверждение регистрации на единой электронной платформе стартап-экосистемы",
                            "Startap ekotizimining yagona elektron platformasida roʻyxatdan oʻtganlik tasdigʻi",
                            "Registration on the unified startup ecosystem platform",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    (
                        (
                            "Договор с организатором программы из утверждённого перечня",
                            "Tasdiqlangan roʻyxatdagi dastur tashkilotchisi bilan shartnoma",
                            "Contract with an organiser from the approved list",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    ("acceleration_mvp", "FILE", False, 3),
                ],
            ),
            (
                (
                    "Для международных программ инкубации или акселерации",
                    "Nufuzli xalqaro inkubatsiya yoki akseleratsiya dasturlari uchun",
                    "For international incubation or acceleration programmes",
                ),
                [
                    (
                        (
                            "Документ об успешном завершении программы",
                            "Dasturni muvaffaqiyatli tamomlaganini tasdiqlovchi hujjat",
                            "Proof of successful completion of the programme",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    (
                        (
                            "Договор и (или) оферта",
                            "Shartnoma va (yoki) oferta",
                            "Contract and/or offer",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                    (
                        (
                            "Платёжное поручение, документы SWIFT и (или) инвойсы",
                            "Toʻlov topshiriqnomasi, SWIFT hujjatlari va (yoki) invoyslar",
                            "Payment order, SWIFT documents and/or invoices",
                        ),
                        "FILE",
                        False,
                        3,
                    ),
                    ("acceleration_mvp", "FILE", False, 3),
                ],
            ),
        ],
    },
    # ---------- 10 ----------
    {
        "translations": (
            (
                "R&D-ваучер на создание MVP",
                "MVP yaratish uchun R&D vaucher",
                "R&D voucher for building an MVP",
            ),
            (
                "R&D-ваучер до 50 тыс. долл. США на создание MVP в молодёжных технопарках и "
                "R&D-центрах; отбор по конкурсу Агентства инновационного развития. "
                "Положение: глава 4, § 4.",
                "Yoshlar texnoparklari va R&D markazlarida MVP yaratish uchun 50 ming AQSh "
                "dollarigacha R&D vaucher; Innovatsion rivojlanish agentligi tanlovi orqali. "
                "Nizom: 4-bob, 4-§.",
                "R&D voucher of up to USD 50,000 for building an MVP in youth technoparks and R&D "
                "centres; selection through the Innovation Development Agency contest. "
                "Regulation: chapter 4, § 4.",
            ),
        ),
        "uses_bank": False,
        "subject_types": ALL_SUBJECTS,
        "stages": [
            (
                APPLICATION_STAGE,
                [
                    (
                        (
                            "Запрашиваемая сумма ваучера, долл. США",
                            "Soʻralayotgan vaucher summasi, AQSh dollari",
                            "Requested voucher amount, USD",
                        ),
                        "NUMBER",
                        True,
                        1,
                    ),
                    (
                        (
                            "Заявка на участие в конкурсе и документы проекта",
                            "Tanlovda ishtirok etish arizasi va loyiha hujjatlari",
                            "Contest application and project documents",
                        ),
                        "FILE",
                        True,
                        3,
                    ),
                    (
                        (
                            "Подтверждение отбора по итогам конкурса",
                            "Tanlov natijasi boʻyicha saralab olinganlik tasdigʻi",
                            "Confirmation of selection in the contest",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    ("no_affiliation", "FILE", True, 1),
                ],
            ),
        ],
    },
    # ---------- 11 ----------
    {
        "translations": (
            (
                "Патентование и регистрация товарного знака",
                "Patentlash va tovar belgisini roʻyxatdan oʻtkazish",
                "Patenting and trademark registration",
            ),
            (
                "Возмещение расходов на патентование стартапа и регистрацию товарного знака — "
                "до 30 БРВ. Положение: глава 4, § 5.",
                "Startap loyihalarni patentlash va tovar belgisini roʻyxatdan oʻtkazish "
                "xarajatlarini qoplash — 30 BHMgacha. Nizom: 4-bob, 5-§.",
                "Reimbursement of startup patenting and trademark registration — up to 30 BCU. "
                "Regulation: chapter 4, § 5.",
            ),
        ),
        "uses_bank": False,
        "subject_types": ALL_SUBJECTS,
        "stages": [
            reimburse_stage(),
            (
                GENERAL_STAGE,
                [
                    ("no_affiliation", "FILE", True, 1),
                    ("passport", "FILE", True, 1),
                    ("consent_personal", "FILE", True, 1),
                    (
                        (
                            "Свидетельство о регистрации изобретения, полезной модели, промышленного образца или товарного знака",
                            "Ixtiro, foydali model, sanoat namunasi yoki tovar belgisi roʻyxatdan oʻtkazilgani toʻgʻrisida guvohnoma",
                            "Registration certificate of the invention, utility model, industrial design or trademark",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Документы об оплате за получение свидетельства (за последний год)",
                            "Guvohnomani olish uchun toʻlovlarni tasdiqlovchi hujjatlar (soʻnggi 1 yil ichida)",
                            "Proof of fees paid for the certificate (within the last year)",
                        ),
                        "FILE",
                        True,
                        3,
                    ),
                    ("bank_account", "FILE", True, 1),
                ],
            ),
        ],
    },
    # ---------- 12 ----------
    {
        "translations": (
            (
                "Брендинг для победителей чемпионата «Ёш тадбиркорлар»",
                "“Yosh tadbirkorlar” chempionati gʻoliblari uchun brending",
                "Branding for “Young Entrepreneurs” championship winners",
            ),
            (
                "Оплата расходов на превращение проекта в бренд для победителей чемпионата "
                "«Ёш тадбиркорлар» — до 100 БРВ. Положение: глава 4, § 6.",
                "“Yosh tadbirkorlar” chempionati gʻoliblari uchun brendga aylantirish "
                "xarajatlarini toʻlash — 100 BHMgacha. Nizom: 4-bob, 6-§.",
                "Payment of branding costs for winners of the “Young Entrepreneurs” championship — "
                "up to 100 BCU. Regulation: chapter 4, § 6.",
            ),
        ),
        "uses_bank": False,
        "subject_types": ALL_SUBJECTS,
        "stages": [
            (
                APPLICATION_STAGE,
                [
                    (
                        (
                            "Сумма оплаты услуг эксперта, сум",
                            "Ekspert xizmat haqi summasi, soʻm",
                            "Expert service fee, UZS",
                        ),
                        "NUMBER",
                        True,
                        1,
                    ),
                    (
                        (
                            "Заявление в Фонд об оплате услуг эксперта",
                            "Jamgʻarmaga ariza (ekspert xizmat haqini toʻlash toʻgʻrisida)",
                            "Application to the Fund to pay the expert's fee",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                ],
            ),
            (
                GENERAL_STAGE,
                [
                    ("no_affiliation", "FILE", True, 1),
                    ("passport", "FILE", True, 1),
                    (
                        (
                            "Подтверждение 1–3 места в чемпионате",
                            "Chempionatda 1–3-oʻrinni egallaganlik tasdigʻi",
                            "Proof of 1st–3rd place in the championship",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Сведения об услугах эксперта из списка Фонда, оплате и ожидаемом результате",
                            "Jamgʻarma roʻyxatidan tanlangan ekspert xizmatlari, toʻlovlari va kutilgan natija haqida maʼlumot",
                            "Details of the expert from the Fund's list: services, fees and expected result",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Договор с экспертом на финансовые и маркетинговые услуги",
                            "Ariza beruvchi va ekspert oʻrtasidagi moliyaviy va marketing xizmatlari shartnomasi",
                            "Contract with the expert for financial and marketing services",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                    (
                        (
                            "Реквизиты банковской карты эксперта",
                            "Ekspertning bank toʻlov kartasi rekvizitlari",
                            "Expert's bank card details",
                        ),
                        "FILE",
                        True,
                        1,
                    ),
                ],
            ),
            (
                ("Для итоговой оплаты", "Yakuniy toʻlov uchun", "For the final payment"),
                [
                    (
                        (
                            "Документ о полном выполнении и приёмке работ",
                            "Ishlar toʻliq bajarilib, qabul qilinganini tasdiqlovchi hujjat",
                            "Proof that the work was fully done and accepted",
                        ),
                        "FILE",
                        False,
                        1,
                    ),
                ],
            ),
        ],
    },
    # ---------- 15 ----------
    {
        "translations": (
            (
                "Подключение к инженерным сетям",
                "Muhandislik tarmoqlariga ulanish",
                "Connection to utility networks",
            ),
            (
                "Возмещение расходов начинающих молодых предпринимателей на подключение к "
                "инженерно-коммуникационным сетям — до 10 БРВ. Положение: глава 4, § 9.",
                "Yangi ish boshlayotgan yosh tadbirkorlarga muhandislik-kommunikatsiya "
                "tarmoqlariga ulanish xarajatlarini qoplash — 10 BHMgacha. Nizom: 4-bob, 9-§.",
                "Reimbursement of utility network connection costs for young entrepreneurs "
                "starting a business — up to 10 BCU. Regulation: chapter 4, § 9.",
            ),
        ),
        "uses_bank": False,
        "subject_types": ["MCHJ"],
        "stages": [
            reimburse_stage(),
            (
                GENERAL_STAGE,
                [
                    ("no_affiliation", "FILE", True, 1),
                    ("charter", "FILE", True, 1),
                    ("registration", "FILE", True, 1),
                    (
                        (
                            "Паспорта или ID-карты учредителей (не менее 50% доли — у граждан 18–30 лет)",
                            "Taʼsischilarning pasporti yoki ID-kartasi (ulushning kamida 50 foizi 18–30 yoshdagi fuqaroga tegishli)",
                            "Founders' passports or ID cards (at least 50% share held by citizens aged 18–30)",
                        ),
                        "FILE",
                        True,
                        5,
                    ),
                    ("consent_personal", "FILE", True, 1),
                    (
                        (
                            "Квитанция об оплате подключения к электросети, водопроводу или канализации (не старше 90 дней)",
                            "Elektr, ichimlik suvi yoki oqova suv tarmogʻiga ulanish yigʻimi toʻlov hujjati (90 kundan oshmagan)",
                            "Receipt for the electricity, water or sewerage connection fee (not older than 90 days)",
                        ),
                        "FILE",
                        True,
                        3,
                    ),
                    (
                        ("Документ о подключении", "Ulanish hujjati", "Connection document"),
                        "FILE",
                        True,
                        1,
                    ),
                    ("bank_account", "FILE", True, 1),
                ],
            ),
        ],
    },
]
