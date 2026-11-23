from enum import StrEnum


class ProgramKind(StrEnum):
    """Направление финансирования (как на аналитическом сайте отдела)."""

    CREDIT = "CREDIT"  # кредит через коммерческие банки
    LOAN = "LOAN"  # беспроцентный заём (ссуда) Фонда
    COMPENSATION = "COMPENSATION"  # возмещение затрат
    INVESTMENT = "INVESTMENT"  # инвестиции (доля)


class ImportTemplate(StrEnum):
    """Шаблон Excel, по которому импортируются проекты программы."""

    PQ60 = "PQ60"  # «ЛОЙИҲАЛАР … сохалар»: лист «буюртмалар номма ном», суммы в млн сўм
    PQ400 = "PQ400"  # «ПҚ-400»: лист «Свод», суммы в млн сўм
    KOMAK = "KOMAK"  # «Кўмак»: лист «… рухсат берилган», суммы в сўм
    INCUBATION = "INCUBATION"  # «Oquv kurs inkubatsiya»: лист «Svod», суммы в сўм


class ProjectStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"  # решение Совета есть, ресурс ещё не выделен (документы)
    AWAITING_BANK_REQUEST = "AWAITING_BANK_REQUEST"  # ждём требование банка на ресурс
    CLIENT_REFUSED = "CLIENT_REFUSED"  # клиент отказался до выделения
    ALLOCATED = "ALLOCATED"  # ресурс выделен / заём профинансирован
    CREDIT_ISSUED = "CREDIT_ISSUED"  # банк выдал кредит (факт)
    RETURNED = "RETURNED"  # клиент отказался, ресурс вернулся в Фонд


class Decision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RegistrySubjectType(StrEnum):
    LEGAL_ENTITY = "LEGAL_ENTITY"  # юридическое лицо (МЧЖ)
    SOLE_PROPRIETOR = "SOLE_PROPRIETOR"  # ЯТТ
    INDIVIDUAL = "INDIVIDUAL"  # физическое лицо


class Sector(StrEnum):
    SERVICES = "SERVICES"  # хизмат кўрсатиш
    PRODUCTION = "PRODUCTION"  # ишлаб чиқариш
    AGRICULTURE = "AGRICULTURE"  # қишлоқ хўжалиги


class Source(StrEnum):
    MANUAL = "MANUAL"  # создан через API
    IMPORT = "IMPORT"  # загружен из Excel (заменяется следующим импортом программы)


class GroupBy(StrEnum):
    PROGRAM = "program"
    KIND = "kind"
    REGION = "region"
    DISTRICT = "district"
    BANK = "bank"
    SECTOR = "sector"
    DIRECTION = "direction"
    GENDER = "gender"
    SUBJECT_TYPE = "subject_type"
    STATUS = "status"
    YEAR = "year"
    MONTH = "month"
