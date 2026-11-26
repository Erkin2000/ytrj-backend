"""Переводы каталога RBAC на узбекский и английский.

Русские названия — источник (`PERMISSIONS`, `MODULE_NAMES`, `ACTION_NAMES`, `ROLE_PRESETS`
в `src/rbac/permissions.py`); здесь — uz и en. Новое право, модуль или системная роль —
добавить перевод сюда, иначе тест `test_rbac_catalog_translated` упадёт.

В БД переводы прав и ролей лежат в `permission_translations` / `role_translations`;
миграция, которая добавляет права, должна заполнить и их переводы
(см. `fill_permission_translations` в `2026_11_23_rbac_translations.py`).
"""

from src.product.enums import Language
from src.rbac.permissions import (
    ACTION_NAMES,
    MODULE_NAMES,
    PERMISSIONS,
    ROLE_PRESETS,
    Action,
    Module,
)

# code -> {language: (name, description)}
PERMISSION_I18N: dict[str, dict[str, tuple[str, str]]] = {
    "users.create": {
        "uz": ("Foydalanuvchilarni yaratish", "Ichki foydalanuvchilarni yaratish"),
        "en": ("Create users", "Create internal users"),
    },
    "users.read": {
        "uz": ("Foydalanuvchilarni koʻrish", "Profillarni koʻrish, qidirish va saralash"),
        "en": ("View users", "View, search and filter profiles"),
    },
    "users.update": {
        "uz": ("Foydalanuvchilarni oʻzgartirish", "Rol va scope tayinlash, bloklash"),
        "en": ("Edit users", "Assign role and scope, block"),
    },
    "users.delete": {
        "uz": ("Foydalanuvchilarni oʻchirish", "Profillarni oʻchirish"),
        "en": ("Delete users", "Delete profiles"),
    },
    "roles.create": {
        "uz": ("Rollarni yaratish", "Rollar katalogini yuritish"),
        "en": ("Create roles", "Maintain the role catalog"),
    },
    "roles.read": {
        "uz": ("Rollarni koʻrish", "Rollar va huquqlar matritsasini koʻrish"),
        "en": ("View roles", "View roles and the permission matrix"),
    },
    "roles.update": {
        "uz": ("Rollarni oʻzgartirish", "Rol huquqlarini modullar boʻyicha sozlash"),
        "en": ("Edit roles", "Configure role permissions by module"),
    },
    "roles.delete": {
        "uz": ("Rollarni oʻchirish", "Foydalanuvchisiz rollarni oʻchirish"),
        "en": ("Delete roles", "Delete roles without users"),
    },
    "banks.create": {
        "uz": ("Banklarni qoʻshish", "Banklar katalogini yuritish"),
        "en": ("Add banks", "Maintain the bank catalog"),
    },
    "banks.read": {
        "uz": ("Banklarni koʻrish", "Hamkor banklar katalogi"),
        "en": ("View banks", "Partner bank catalog"),
    },
    "banks.update": {
        "uz": ("Banklarni oʻzgartirish", "Subyekt turi boʻyicha bank tanlash qoidalari"),
        "en": ("Edit banks", "Bank selection rules by subject type"),
    },
    "banks.delete": {
        "uz": ("Banklarni oʻchirish", "Banklarni nofaol qilish"),
        "en": ("Delete banks", "Deactivate banks"),
    },
    "products.create": {
        "uz": ("Mahsulotlarni yaratish", "Yangi mahsulot va mavjudining nusxasi"),
        "en": ("Create products", "New product or a copy of an existing one"),
    },
    "products.read": {
        "uz": (
            "Mahsulotlarni koʻrish",
            "Mahsulotlar katalogi; ariza beruvchi eʼlon qilinganlarini koʻradi",
        ),
        "en": ("View products", "Product catalog; applicants see published ones"),
    },
    "products.update": {
        "uz": (
            "Mahsulotlarni oʻzgartirish",
            "Nomlar, banklar, muddatlar, anketa bosqichlari va maydonlari",
        ),
        "en": ("Edit products", "Names, banks, dates, form stages and fields"),
    },
    "products.delete": {
        "uz": ("Mahsulotlarni oʻchirish", "Arizasi yoʻq mahsulotni oʻchirish"),
        "en": ("Delete products", "Delete a product without applications"),
    },
    "products.approve": {
        "uz": ("Mahsulotlarni eʼlon qilish", "Eʼlon qilish va eʼlondan olish"),
        "en": ("Publish products", "Publish and unpublish"),
    },
    "applications.create": {
        "uz": ("Ariza yaratish", "Ariza beruvchi tomonidan ariza topshirish"),
        "en": ("Create application", "Submission of an application by the applicant"),
    },
    "applications.read": {
        "uz": ("Arizalarni koʻrish", "Scope doirasidagi arizalarni koʻrish"),
        "en": ("View applications", "View applications within scope"),
    },
    "applications.update": {
        "uz": ("Arizani oʻzgartirish", "Qoralamani tahrirlash, qoʻshimcha soʻrash"),
        "en": ("Edit application", "Edit the draft, request additions"),
    },
    "applications.delete": {
        "uz": ("Arizani oʻchirish", "Qoralamani oʻchirish"),
        "en": ("Delete application", "Delete the draft"),
    },
    "applications.approve": {
        "uz": ("Kengashga yoʻnaltirish", "Arizani tayyorlash va Kengashga yuborish"),
        "en": ("Send to the Council", "Prepare and send the application to the Council"),
    },
    "fund_review.read": {
        "uz": (
            "Jamgʻarma ish oynasidagi arizalar",
            "Jamgʻarma arizalari roʻyxati, hisoblagichlari va kartochkalari (/fund/applications)",
        ),
        "en": (
            "Applications in the Fund workspace",
            "Fund application list, counters and cards (/fund/applications)",
        ),
    },
    "fund_review.approve": {
        "uz": (
            "Jamgʻarmaning ariza boʻyicha rad javobi",
            "Arizani Kengashgacha sababi bilan rad etish",
        ),
        "en": (
            "Fund rejection of an application",
            "Reject an application before the Council with a reason",
        ),
    },
    "scoring.read": {
        "uz": ("Skoringni koʻrish", "KATM natijasining toʻliq sabablari"),
        "en": ("View scoring", "Full reasons of the KATM result"),
    },
    "scoring.update": {
        "uz": ("Qayta skoring", "Texnik xatodan keyin qayta ishlash"),
        "en": ("Re-run scoring", "Reprocess after a technical error"),
    },
    "bank_review.read": {
        "uz": ("Bank arizalarini koʻrish", "Xodimning bankiga yoʻnaltirilgan arizalar"),
        "en": ("View bank applications", "Applications sent to the employee's bank"),
    },
    "bank_review.update": {
        "uz": ("Arizani bank tomonidan qabul qilish", "Arizani koʻrib chiqishga qabul qilish"),
        "en": ("Accept application by bank", "Accept the application for review"),
    },
    "bank_review.approve": {
        "uz": ("Bank qarori", "Sababi bilan maʼqullash yoki rad etish"),
        "en": ("Bank decision", "Approve or reject with a reason"),
    },
    "council_review.read": {
        "uz": ("Kengash arizalarini koʻrish", "Kengash aʼzosiga yoʻnaltirilgan arizalar"),
        "en": ("View Council applications", "Applications sent to the Council member"),
    },
    "council_review.approve": {
        "uz": ("Kengash qarori", "«Roziman» / «Rad etaman» sababi bilan"),
        "en": ("Council decision", "«Agree» / «Reject» with a reason"),
    },
    "allocation.create": {
        "uz": ("Resurs ajratilishini qayd etish", "Resurs ajratilganini kiritish"),
        "en": ("Record resource allocation", "Enter the fact of resource allocation"),
    },
    "allocation.read": {
        "uz": ("Resurs ajratilishini koʻrish", "Ajratish bosqichini koʻrish"),
        "en": ("View resource allocation", "View the allocation stage"),
    },
    "allocation.approve": {
        "uz": ("Arizani yakunlash", "Arizani COMPLETED holatiga oʻtkazish"),
        "en": ("Complete application", "Move the application to COMPLETED"),
    },
    "bulletins.create": {
        "uz": ("Byulletenlarni yaratish", "Kengash aʼzolari uchun yangi byulleten"),
        "en": ("Create bulletins", "New bulletin for Council members"),
    },
    "bulletins.read": {
        "uz": ("Byulletenlarni koʻrish", "Barcha byulletenlar va imzolanish holati"),
        "en": ("View bulletins", "All bulletins and signing status"),
    },
    "bulletins.update": {
        "uz": ("Byulletenlarni oʻzgartirish", "Byulleten maʼlumotlari, fayli va imzolash muddati"),
        "en": ("Edit bulletins", "Bulletin data, file and signing deadline"),
    },
    "bulletins.delete": {
        "uz": ("Byulletenlarni oʻchirish", "Yuborilmagan byulletenni oʻchirish"),
        "en": ("Delete bulletins", "Delete an unsent bulletin"),
    },
    "bulletins.approve": {
        "uz": ("Byulletenlarni yuborish", "Kengash aʼzolariga yuborish va bekor qilish"),
        "en": ("Send bulletins", "Send to Council members and cancel"),
    },
    "faq.create": {
        "uz": ("FAQ savollarini yaratish", "Sayt uchun yangi savol va javob"),
        "en": ("Create FAQ questions", "New question and answer for the website"),
    },
    "faq.read": {
        "uz": ("FAQ savollarini koʻrish", "Barcha savollar, saytdan yashirilganlari bilan"),
        "en": ("View FAQ questions", "All questions, including hidden ones"),
    },
    "faq.update": {
        "uz": ("FAQ savollarini oʻzgartirish", "Matn, tartib va saytda koʻrsatish"),
        "en": ("Edit FAQ questions", "Text, order and visibility on the website"),
    },
    "faq.delete": {
        "uz": ("FAQ savollarini oʻchirish", "Savolni oʻchirish"),
        "en": ("Delete FAQ questions", "Delete a question"),
    },
    "news.create": {
        "uz": ("Yangiliklarni yaratish", "Yangi yangilik: darhol, tanlangan vaqtda yoki qoralama"),
        "en": ("Create news", "New article: now, at a chosen time or as a draft"),
    },
    "news.read": {
        "uz": ("Yangiliklarni koʻrish", "Barcha yangiliklar, qoralama va kechiktirilganlari bilan"),
        "en": ("View news", "All news, including drafts and scheduled"),
    },
    "news.update": {
        "uz": ("Yangiliklarni oʻzgartirish", "Matn, sana, rasm va eʼlon qilish"),
        "en": ("Edit news", "Text, date, photo and publication"),
    },
    "news.delete": {
        "uz": ("Yangiliklarni oʻchirish", "Yangilikni rasmi bilan oʻchirish"),
        "en": ("Delete news", "Delete an article with its photo"),
    },
    "events.create": {
        "uz": ("Tadbirlarni yaratish", "Sayt uchun yangi tadbir"),
        "en": ("Create events", "New event for the website"),
    },
    "events.read": {
        "uz": ("Tadbirlarni koʻrish", "Barcha tadbirlar, yashirinlari bilan"),
        "en": ("View events", "All events, including hidden ones"),
    },
    "events.update": {
        "uz": ("Tadbirlarni oʻzgartirish", "Matn, sana va saytda koʻrsatish"),
        "en": ("Edit events", "Text, date and visibility on the website"),
    },
    "events.delete": {
        "uz": ("Tadbirlarni oʻchirish", "Tadbirni oʻchirish"),
        "en": ("Delete events", "Delete an event"),
    },
    "about.create": {
        "uz": (
            "«Biz haqimizda» boʻlimlarini yaratish",
            "«Biz haqimizda» sahifasining yangi boʻlimi",
        ),
        "en": ("Create «About us» sections", "New section of the «About us» page"),
    },
    "about.read": {
        "uz": ("«Biz haqimizda» boʻlimlarini koʻrish", "Barcha boʻlimlar, yashirinlari bilan"),
        "en": ("View «About us» sections", "All sections, including hidden ones"),
    },
    "about.update": {
        "uz": ("«Biz haqimizda» boʻlimlarini oʻzgartirish", "Matn, tartib va saytda koʻrsatish"),
        "en": ("Edit «About us» sections", "Text, order and visibility on the website"),
    },
    "about.delete": {
        "uz": ("«Biz haqimizda» boʻlimlarini oʻchirish", "Boʻlimni oʻchirish"),
        "en": ("Delete «About us» sections", "Delete a section"),
    },
    "council_profiles.create": {
        "uz": ("Kengash aʼzolarini saytga qoʻshish", "Kengash aʼzosining yangi kartochkasi"),
        "en": ("Add Council members to the website", "New Council member card"),
    },
    "council_profiles.read": {
        "uz": ("Saytdagi Kengash aʼzolarini koʻrish", "Barcha kartochkalar, yashirinlari bilan"),
        "en": ("View Council members on the website", "All cards, including hidden ones"),
    },
    "council_profiles.update": {
        "uz": ("Saytdagi Kengash aʼzolarini oʻzgartirish", "Maʼlumotlar, rasm, roʻyxatdagi oʻrni"),
        "en": ("Edit Council members on the website", "Details, photo, position in the list"),
    },
    "council_profiles.delete": {
        "uz": ("Kengash aʼzolarini saytdan oʻchirish", "Kartochkani rasmi bilan oʻchirish"),
        "en": ("Remove Council members from the website", "Delete a card with its photo"),
    },
    "leadership.create": {
        "uz": ("Rahbariyatni saytga qoʻshish", "Rahbarning yangi kartochkasi"),
        "en": ("Add leadership to the website", "New leader card"),
    },
    "leadership.read": {
        "uz": ("Saytdagi rahbariyatni koʻrish", "Barcha kartochkalar, yashirinlari bilan"),
        "en": ("View leadership on the website", "All cards, including hidden ones"),
    },
    "leadership.update": {
        "uz": ("Saytdagi rahbariyatni oʻzgartirish", "Maʼlumotlar, rasm, roʻyxatdagi oʻrni"),
        "en": ("Edit leadership on the website", "Details, photo, position in the list"),
    },
    "leadership.delete": {
        "uz": ("Rahbariyatni saytdan oʻchirish", "Kartochkani rasmi bilan oʻchirish"),
        "en": ("Remove leadership from the website", "Delete a card with its photo"),
    },
    "contacts.create": {
        "uz": ("Kontaktlarni saytga qoʻshish", "Tashkilotning yangi telefoni va/yoki emaili"),
        "en": ("Add contacts to the website", "New organization phone and/or email"),
    },
    "contacts.read": {
        "uz": ("Sayt kontaktlarini koʻrish", "Barcha kontaktlar, yashirinlari bilan"),
        "en": ("View website contacts", "All contacts, including hidden ones"),
    },
    "contacts.update": {
        "uz": ("Sayt kontaktlarini oʻzgartirish", "Telefon, email, tartib va saytda koʻrsatish"),
        "en": ("Edit website contacts", "Phone, email, order and visibility on the website"),
    },
    "contacts.delete": {
        "uz": ("Kontaktlarni saytdan oʻchirish", "Kontaktni oʻchirish"),
        "en": ("Delete website contacts", "Delete a contact"),
    },
    "testimonials.create": {
        "uz": ("Fikrlarni saytga qoʻshish", "Yangi fikr: rasm, F.I.Sh., matn"),
        "en": ("Add testimonials to the website", "New testimonial: photo, full name, text"),
    },
    "testimonials.read": {
        "uz": ("Saytdagi fikrlarni koʻrish", "Barcha fikrlar, yashirinlari bilan"),
        "en": ("View testimonials on the website", "All testimonials, including hidden ones"),
    },
    "testimonials.update": {
        "uz": ("Saytdagi fikrlarni oʻzgartirish", "Matn, rasm, tartib va koʻrsatish"),
        "en": ("Edit testimonials on the website", "Text, photo, order and visibility"),
    },
    "registry.create": {
        "uz": ("Loyihalar reestriga qoʻshish", "Yangi dastur yoki qoʻlda loyiha"),
        "en": ("Add to the project registry", "New programme or a manual project"),
    },
    "registry.read": {
        "uz": ("Reestr va tahlilni koʻrish", "Loyihalar, dasturlar, jami va kesimlar"),
        "en": ("View registry and analytics", "Projects, programmes, totals and breakdowns"),
    },
    "registry.update": {
        "uz": ("Loyihalar reestrini oʻzgartirish", "Dastur yoki loyiha maʼlumotlari"),
        "en": ("Edit the project registry", "Programme or project data"),
    },
    "registry.delete": {
        "uz": ("Loyihalar reestridan oʻchirish", "Loyihani yoki boʻsh dasturni oʻchirish"),
        "en": ("Delete from the project registry", "Delete a project or an empty programme"),
    },
    "registry.approve": {
        "uz": (
            "Reestrga Excel import qilish",
            "Boʻlim faylini yuklash, dastur maʼlumotlari almashadi",
        ),
        "en": (
            "Import Excel into the registry",
            "Upload the department file, replacing programme data",
        ),
    },
    "testimonials.delete": {
        "uz": ("Fikrlarni saytdan oʻchirish", "Fikrni rasmi bilan oʻchirish"),
        "en": ("Delete testimonials from the website", "Delete a testimonial with its photo"),
    },
    "contracts.create": {
        "uz": ("Shartnomalarni yaratish", "Ijrochi bilan yangi shartnoma"),
        "en": ("Create contracts", "New contract with a contractor"),
    },
    "contracts.read": {
        "uz": ("Shartnomalarni koʻrish", "Ijrochilarning barcha shartnomalari"),
        "en": ("View contracts", "All contractor contracts"),
    },
    "contracts.update": {
        "uz": ("Shartnomalarni oʻzgartirish", "Maʼlumotlar, muddat, rahbar, shartnomani yopish"),
        "en": ("Edit contracts", "Data, term, approver, closing the contract"),
    },
    "contracts.delete": {
        "uz": ("Shartnomalarni oʻchirish", "Dalolatnomasi yoʻq shartnomani oʻchirish"),
        "en": ("Delete contracts", "Delete a contract without reports"),
    },
    "acts.create": {
        "uz": ("Oʻz dalolatnomalarini tuzish", "Oʻz shartnomasi boʻyicha yangi dalolatnoma"),
        "en": ("Draft own reports", "New report under own contract"),
    },
    "acts.read": {
        "uz": ("Oʻz dalolatnomalarini koʻrish", "Oʻz shartnomalari va dalolatnomalari"),
        "en": ("View own reports", "Own contracts and reports"),
    },
    "acts.update": {
        "uz": ("Oʻz dalolatnomalarini oʻzgartirish", "Qatorlar, ilova, imzolash va yuborish"),
        "en": ("Edit own reports", "Rows, appendix, signing and submitting"),
    },
    "acts.delete": {
        "uz": ("Oʻz qoralamalarini oʻchirish", "Yuborilmagan dalolatnomani oʻchirish"),
        "en": ("Delete own drafts", "Delete a report that was not submitted"),
    },
    "act_review.read": {
        "uz": ("Ijrochilar dalolatnomalarini koʻrish", "Barcha dalolatnomalar va tarixi"),
        "en": ("View contractor reports", "All reports and their history"),
    },
    "act_review.approve": {
        "uz": (
            "Ijrochilar dalolatnomalarini tekshirish",
            "Qabul qilish, qayta ishlashga qaytarish va bekor qilish",
        ),
        "en": ("Review contractor reports", "Accept, return for changes and cancel"),
    },
    "act_signing.approve": {
        "uz": (
            "Dalolatnomalarni rahbar sifatida imzolash",
            "U rahbar boʻlgan shartnomalar dalolatnomalarini E-IMZO bilan imzolash",
        ),
        "en": (
            "Sign reports as approver",
            "E-IMZO signature of reports under contracts where they are the approver",
        ),
    },
}

MODULE_I18N: dict[str, dict[str, str]] = {
    Module.USERS: {"uz": "Foydalanuvchilar", "en": "Users"},
    Module.ROLES: {"uz": "Rollar va huquqlar", "en": "Roles and permissions"},
    Module.BANKS: {"uz": "Banklar katalogi", "en": "Bank catalog"},
    Module.PRODUCTS: {"uz": "Mahsulotlar", "en": "Products"},
    Module.APPLICATIONS: {"uz": "Arizalar", "en": "Applications"},
    Module.FUND_REVIEW: {
        "uz": "Jamgʻarma ish oynasi (arizalar)",
        "en": "Fund workspace (applications)",
    },
    Module.SCORING: {"uz": "KATM skoringi", "en": "KATM scoring"},
    Module.BANK_REVIEW: {"uz": "Bank bosqichi", "en": "Bank stage"},
    Module.COUNCIL_REVIEW: {"uz": "Kengash bosqichi", "en": "Council stage"},
    Module.ALLOCATION: {"uz": "Resurs ajratish", "en": "Resource allocation"},
    Module.BULLETINS: {"uz": "Kengash byulletenlari", "en": "Council bulletins"},
    Module.FAQ: {"uz": "Sayt FAQ", "en": "Website FAQ"},
    Module.NEWS: {"uz": "Sayt yangiliklari", "en": "Website news"},
    Module.EVENTS: {"uz": "Sayt tadbirlari", "en": "Website events"},
    Module.ABOUT: {"uz": "«Biz haqimizda» sahifasi", "en": "«About us» page"},
    Module.COUNCIL_PROFILES: {
        "uz": "Saytdagi Kengash aʼzolari",
        "en": "Council members on the website",
    },
    Module.LEADERSHIP: {"uz": "Saytdagi rahbariyat", "en": "Leadership on the website"},
    Module.CONTACTS: {"uz": "Saytdagi kontaktlar", "en": "Contacts on the website"},
    Module.TESTIMONIALS: {"uz": "Saytdagi fikrlar", "en": "Testimonials on the website"},
    Module.REGISTRY: {"uz": "Loyihalar reestri va tahlil", "en": "Project registry and analytics"},
    Module.CONTRACTS: {"uz": "Ijrochilar shartnomalari", "en": "Contractor contracts"},
    Module.ACTS: {"uz": "Mening dalolatnomalarim", "en": "My work reports"},
    Module.ACT_REVIEW: {"uz": "Dalolatnomalarni tekshirish", "en": "Work report review"},
    Module.ACT_SIGNING: {"uz": "Dalolatnomalarni rahbar imzolashi", "en": "Approver signing"},
}

ACTION_I18N: dict[str, dict[str, str]] = {
    Action.CREATE: {"uz": "Yaratish", "en": "Create"},
    Action.READ: {"uz": "Koʻrish", "en": "View"},
    Action.UPDATE: {"uz": "Oʻzgartirish", "en": "Edit"},
    Action.DELETE: {"uz": "Oʻchirish", "en": "Delete"},
    Action.APPROVE: {"uz": "Tasdiqlash / qaror", "en": "Approve / decide"},
}

# Системные роли: code -> {language: (name, description)}
ROLE_I18N: dict[str, dict[str, tuple[str, str]]] = {
    "SUPER_ADMIN": {
        "uz": (
            "Super Admin",
            "Platformani boshqarish: foydalanuvchilar, RBAC, maʼlumotnomalar, audit",
        ),
        "en": ("Super Admin", "Platform management: users, RBAC, reference data, audit"),
    },
    "FUND_OPERATOR": {
        "uz": (
            "Jamgʻarma operatori",
            "Jamgʻarmaning kundalik jarayonlari: arizalar, Kengash, moliyalashtirish",
        ),
        "en": ("Fund operator", "Day-to-day Fund processes: applications, Council, financing"),
    },
    "BANK_EMPLOYEE": {
        "uz": ("Bankning masʼul xodimi", "Faqat uning bankiga yoʻnaltirilgan arizalar"),
        "en": ("Responsible bank employee", "Only applications sent to their bank"),
    },
    "COUNCIL_MEMBER": {
        "uz": ("Kengash aʼzosi", "Faqat unga yoʻnaltirilgan arizalar"),
        "en": ("Council member", "Only applications assigned to them"),
    },
    "MARKETING": {
        "uz": (
            "Marketing",
            "Sayt kontenti: yangiliklar, tadbirlar, FAQ, «Biz haqimizda», Kengash aʼzolari, "
            "rahbariyat, kontaktlar va fikrlar",
        ),
        "en": (
            "Marketing",
            "Website content: news, events, FAQ, «About us», Council members, leadership, "
            "contacts and testimonials",
        ),
    },
    "CONTRACTOR": {
        "uz": ("Ijrochi", "Shartnoma boʻyicha ijrochi: oʻz shartnomalari va dalolatnomalari"),
        "en": ("Contractor", "Contractor under a contract: own contracts and work reports"),
    },
    "APPLICANT": {
        "uz": ("Ariza beruvchi", "Faqat oʻz profili va oʻz arizalari"),
        "en": ("Applicant", "Only own profile and own applications"),
    },
}


def permission_translations(code: str, ru_name: str, ru_description: str | None) -> dict:
    """{language: (name, description)} для права; нет перевода — русский текст."""
    i18n = PERMISSION_I18N.get(code, {})
    ru = PERMISSIONS.get(code, (ru_name, ru_description or ""))
    return {
        Language.RU: ru,
        Language.UZ: i18n.get("uz", ru),
        Language.EN: i18n.get("en", ru),
    }


def role_translations(code: str, ru_name: str, ru_description: str | None) -> dict:
    """{language: (name, description)} для роли: системная — из каталога, своя — русский текст."""
    preset = ROLE_PRESETS.get(code)
    ru = (preset[0], preset[1]) if preset else (ru_name, ru_description)
    i18n = ROLE_I18N.get(code, {})
    return {
        Language.RU: ru,
        Language.UZ: i18n.get("uz", ru),
        Language.EN: i18n.get("en", ru),
    }


def module_translations(module: str) -> dict[Language, str]:
    i18n = MODULE_I18N.get(module, {})
    ru = MODULE_NAMES.get(module, module)
    return {
        Language.RU: ru,
        Language.UZ: i18n.get("uz", ru),
        Language.EN: i18n.get("en", ru),
    }


def action_translations(action: str) -> dict[Language, str]:
    i18n = ACTION_I18N.get(action, {})
    ru = ACTION_NAMES.get(action, action)
    return {
        Language.RU: ru,
        Language.UZ: i18n.get("uz", ru),
        Language.EN: i18n.get("en", ru),
    }


def missing_translations() -> list[str]:
    """Что в каталоге без перевода на uz / en — для теста."""
    missing = [f"permission:{code}" for code in PERMISSIONS if code not in PERMISSION_I18N]
    missing += [f"module:{m.value}" for m in Module if m not in MODULE_I18N]
    missing += [f"action:{a.value}" for a in Action if a not in ACTION_I18N]
    missing += [f"role:{code}" for code in ROLE_PRESETS if code not in ROLE_I18N]
    return missing
