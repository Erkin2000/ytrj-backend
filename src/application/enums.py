from enum import StrEnum


class SubjectType(StrEnum):
    """Тип предпринимательского субъекта."""

    YATT = "YATT"  # ИП (yakka tartibdagi tadbirkor)
    MCHJ = "MCHJ"  # ООО (mas'uliyati cheklangan jamiyat)
    SELF_EMPLOYED = "SELF_EMPLOYED"  # Самозанятый


# Для ИП и ООО обязательно юридическое наименование.
SUBJECT_TYPES_WITH_LEGAL_NAME = {SubjectType.YATT, SubjectType.MCHJ}

# Реквизиты предприятия (СТИР, руководитель) и учредители — только у ООО.
# ИП и самозанятый действуют от своего имени: данные берутся из профиля заявителя.
SUBJECT_TYPES_WITH_COMPANY = {SubjectType.MCHJ}
SUBJECT_TYPES_WITH_FOUNDERS = {SubjectType.MCHJ}


class ApplicationStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    SCORING_IN_PROGRESS = "SCORING_IN_PROGRESS"
    SCORING_FAILED = "SCORING_FAILED"
    ELIGIBILITY_FAILED = "ELIGIBILITY_FAILED"
    READY_FOR_BANK = "READY_FOR_BANK"
    SENT_TO_BANK = "SENT_TO_BANK"
    BANK_REVIEW = "BANK_REVIEW"
    BANK_APPROVED = "BANK_APPROVED"
    BANK_REJECTED = "BANK_REJECTED"
    COUNCIL_REVIEW = "COUNCIL_REVIEW"
    COUNCIL_APPROVED = "COUNCIL_APPROVED"
    COUNCIL_REJECTED = "COUNCIL_REJECTED"
    DEMAND_DOCUMENT_CREATED = "DEMAND_DOCUMENT_CREATED"
    RESOURCE_ALLOCATION = "RESOURCE_ALLOCATION"
    COMPLETED = "COMPLETED"


# Конечные статусы: заявка только для просмотра.
FINAL_STATUSES = {
    ApplicationStatus.SCORING_FAILED,
    ApplicationStatus.ELIGIBILITY_FAILED,
    ApplicationStatus.BANK_REJECTED,
    ApplicationStatus.COUNCIL_REJECTED,
    ApplicationStatus.COMPLETED,
}

REJECTED_STATUSES = {
    ApplicationStatus.SCORING_FAILED,
    ApplicationStatus.ELIGIBILITY_FAILED,
    ApplicationStatus.BANK_REJECTED,
    ApplicationStatus.COUNCIL_REJECTED,
}


class ScoringResult(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"


class BankDecision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class CouncilDecision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DemandDocumentStatus(StrEnum):
    CREATED = "CREATED"  # запись создана, файл ещё не сформирован
    GENERATED = "GENERATED"  # файл сформирован (модуль documents)
    REVOKED = "REVOKED"
