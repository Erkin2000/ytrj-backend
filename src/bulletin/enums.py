from datetime import timedelta, timezone
from enum import StrEnum

# Даты календаря и страницы проверки — по Ташкенту (UTC+5, без перехода на летнее время).
TASHKENT_TZ = timezone(timedelta(hours=5), name="Asia/Tashkent")


class BulletinStatus(StrEnum):
    """Общий статус бюллетеня.

    PENDING — создан, ждёт даты отправки (`send_at`) и членам Совета не виден;
    PUBLISHED — отправлен всем активным членам Совета, подписей ещё нет;
    PARTIALLY_SIGNED — подписала часть членов; COMPLETED — подписали все;
    CANCELLED — аннулирован Фондом (страница QR показывает «Аннулирован»).
    """

    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    PARTIALLY_SIGNED = "PARTIALLY_SIGNED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# Бюллетень разослан и ждёт подписей.
SIGNING_STATUSES = {BulletinStatus.PUBLISHED, BulletinStatus.PARTIALLY_SIGNED}
# Бюллетень виден членам Совета.
SENT_STATUSES = SIGNING_STATUSES | {BulletinStatus.COMPLETED, BulletinStatus.CANCELLED}


class BulletinDecision(StrEnum):
    AGREE = "AGREE"  # «Согласен»
    AGAINST = "AGAINST"  # «Против»


DECISION_NAMES = {BulletinDecision.AGREE: "Согласен", BulletinDecision.AGAINST: "Против"}


class MemberBulletinStatus(StrEnum):
    """Личный статус бюллетеня у члена Совета."""

    NEW = "NEW"  # ещё не открывал
    VIEWED = "VIEWED"  # открыл, не подписал
    SIGNED = "SIGNED"  # подписал ЭЦП
    OVERDUE = "OVERDUE"  # срок подписания прошёл без подписи
    CANCELLED = "CANCELLED"  # бюллетень аннулирован до подписи


class CouncilBulletinTab(StrEnum):
    """Вкладки рабочего окна члена Совета."""

    ALL = "all"
    NEW = "new"  # не открытые и ещё открытые для подписи
    TO_SIGN = "to_sign"  # ждут моей подписи (срок не прошёл)
    SIGNED = "signed"
    OVERDUE = "overdue"


class CalendarEventType(StrEnum):
    SEND = "SEND"  # дата отправки (для PENDING — плановая)
    DEADLINE = "DEADLINE"  # срок подписания
