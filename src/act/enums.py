"""Договоры исполнителей и акты выполненных работ (dalolatnoma)."""

from enum import StrEnum


class ContractStatus(StrEnum):
    """ACTIVE — по договору можно составлять акты; CLOSED — договор закрыт, новых актов нет."""

    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class ActStatus(StrEnum):
    """Статус акта выполненных работ.

    DRAFT — черновик исполнителя; SUBMITTED — исполнитель подписал E-IMZO и отправил
    на проверку; ACCEPTED — Фонд проверил, ждёт подписи руководителя; SIGNED —
    подписан руководителем (итоговый, неизменяемый); RETURNED — возвращён исполнителю
    с замечанием (подписи сняты, можно править); CANCELLED — аннулирован Фондом.
    """

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    SIGNED = "SIGNED"
    RETURNED = "RETURNED"
    CANCELLED = "CANCELLED"


# Акт можно править (исполнитель).
EDITABLE_STATUSES = {ActStatus.DRAFT, ActStatus.RETURNED}
# Акт в работе у Фонда.
IN_REVIEW_STATUSES = {ActStatus.SUBMITTED, ActStatus.ACCEPTED}
# Акт занимает свой период в договоре (с другим таким актом период пересекаться не может).
PERIOD_HOLDING_STATUSES = {
    ActStatus.DRAFT,
    ActStatus.SUBMITTED,
    ActStatus.ACCEPTED,
    ActStatus.SIGNED,
    ActStatus.RETURNED,
}
# Фонд может аннулировать.
CANCELLABLE_STATUSES = {
    ActStatus.DRAFT,
    ActStatus.SUBMITTED,
    ActStatus.ACCEPTED,
    ActStatus.RETURNED,
}


class ActSignerRole(StrEnum):
    """CONTRACTOR — «Topshiruvchi» (исполнитель); APPROVER — «Qabul qiluvchi» (руководитель)."""

    CONTRACTOR = "CONTRACTOR"
    APPROVER = "APPROVER"


class ActEventType(StrEnum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    WITHDRAWN = "WITHDRAWN"
    ACCEPTED = "ACCEPTED"
    RETURNED = "RETURNED"
    SIGNED = "SIGNED"
    CANCELLED = "CANCELLED"


class FundActTab(StrEnum):
    """Вкладки рабочего окна Фонда."""

    ALL = "all"
    TO_REVIEW = "to_review"  # SUBMITTED
    TO_SIGN = "to_sign"  # ACCEPTED
    SIGNED = "signed"
    RETURNED = "returned"
    CANCELLED = "cancelled"


UZ_MONTHS = (
    "yanvar",
    "fevral",
    "mart",
    "aprel",
    "may",
    "iyun",
    "iyul",
    "avgust",
    "sentabr",
    "oktabr",
    "noyabr",
    "dekabr",
)
