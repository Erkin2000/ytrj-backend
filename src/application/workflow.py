"""State machine заявки и индикатор прогресса для заявителя (ТЗ, п. 60-63).

Порядок (решение заказчика от 2026-11-05, отличается от ТЗ 30.09.2026):
скоринг KATM → Фонд → Совет → банк. Одобрение банком завершает заявку."""

from src.application.enums import REJECTED_STATUSES
from src.application.enums import ApplicationStatus as S
from src.application.schemas.application_schema import ProgressStepDTO
from src.common.responses.exceptions import InvalidStatusTransitionException

TRANSITIONS: dict[S, set[S]] = {
    S.DRAFT: {S.SUBMITTED},
    S.SUBMITTED: {S.SCORING_IN_PROGRESS},
    S.SCORING_IN_PROGRESS: {S.SCORING_FAILED, S.ELIGIBILITY_FAILED, S.FUND_REVIEW},
    S.FUND_REVIEW: {S.FUND_REJECTED, S.COUNCIL_REVIEW},
    S.COUNCIL_REVIEW: {S.COUNCIL_APPROVED, S.COUNCIL_REJECTED},
    S.COUNCIL_APPROVED: {S.SENT_TO_BANK},
    S.SENT_TO_BANK: {S.BANK_REVIEW},
    S.BANK_REVIEW: {S.BANK_APPROVED, S.BANK_REJECTED},
    S.BANK_APPROVED: {S.COMPLETED},
}

# Статусы, в которых заявка видна банку: банк — последний этап.
BANK_VISIBLE_STATUSES = {
    S.SENT_TO_BANK,
    S.BANK_REVIEW,
    S.BANK_APPROVED,
    S.BANK_REJECTED,
    S.COMPLETED,
}

# Рабочее окно банка: новые / на рассмотрении / завершённые.
BANK_BUCKETS: dict[str, set[S]] = {
    "new": {S.SENT_TO_BANK},
    "in_review": {S.BANK_REVIEW},
    "completed": {S.BANK_APPROVED, S.BANK_REJECTED, S.COMPLETED},
}


def assert_transition(current: S, target: S) -> None:
    if target not in TRANSITIONS.get(current, set()):
        raise InvalidStatusTransitionException(
            f"Invalid application status transition: {current} -> {target}"
        )


# ---------- индикатор прогресса для заявителя ----------

# (key, title, описание этапа, что требуется от пользователя)
PROGRESS_STEPS: list[tuple[str, str, str, str | None]] = [
    (
        "submitted",
        "Заявка подана",
        "Заявка принята и зарегистрирована. Начата предварительная проверка.",
        None,
    ),
    (
        "scoring",
        "Проверка KATM",
        "Проводится проверка в системе скоринга и соответствие требованиям Фонда.",
        None,
    ),
    (
        "fund_review",
        "Рассмотрение Фондом",
        "Оператор Фонда проверяет заявку и направляет её на рассмотрение Совета.",
        None,
    ),
    (
        "council_review",
        "Рассмотрение Советом",
        "Совет выносит решение «Согласен» или «Отклоняю».",
        None,
    ),
    (
        "sent_to_bank",
        "Отправлена в банк",
        "Совет утвердил заявку. Она направлена в выбранный вами банк.",
        None,
    ),
    (
        "bank_review",
        "Банк рассматривает",
        "Ответственный сотрудник банка проводит внутреннее рассмотрение.",
        None,
    ),
    (
        "completed",
        "Заявка одобрена",
        "Банк одобрил заявку. Процесс на платформе завершён.",
        None,
    ),
]

# Какой шаг активен для каждого статуса (индекс в PROGRESS_STEPS).
STATUS_STEP_INDEX: dict[S, int] = {
    S.DRAFT: -1,
    S.SUBMITTED: 0,
    S.SCORING_IN_PROGRESS: 1,
    S.SCORING_FAILED: 1,
    S.ELIGIBILITY_FAILED: 1,
    S.FUND_REVIEW: 2,
    S.FUND_REJECTED: 2,
    S.COUNCIL_REVIEW: 3,
    S.COUNCIL_REJECTED: 3,
    S.COUNCIL_APPROVED: 4,
    S.SENT_TO_BANK: 4,
    S.BANK_REVIEW: 5,
    S.BANK_REJECTED: 5,
    S.BANK_APPROVED: 6,
    S.COMPLETED: 6,
    # устаревшие (на случай непереведённых записей)
    S.READY_FOR_BANK: 2,
    S.DEMAND_DOCUMENT_CREATED: 6,
    S.RESOURCE_ALLOCATION: 6,
}


def build_progress(status: S, scoring_retry_required: bool = False) -> list[ProgressStepDTO]:
    active = STATUS_STEP_INDEX[status]
    rejected = status in REJECTED_STATUSES
    completed = status == S.COMPLETED

    steps: list[ProgressStepDTO] = []
    for index, (key, title, description, action) in enumerate(PROGRESS_STEPS):
        if index < active or completed:
            state = "done"
        elif index == active:
            state = "rejected" if rejected else "active"
        else:
            state = "pending"

        if state == "active" and key == "scoring" and scoring_retry_required:
            description = (
                "Проверка временно недоступна по техническим причинам. "
                "Заявка не отклонена и будет обработана повторно."
            )

        steps.append(
            ProgressStepDTO(
                key=key,
                title=title,
                state=state,
                description=description,
                action_required=action if state == "active" else None,
            )
        )
    return steps
