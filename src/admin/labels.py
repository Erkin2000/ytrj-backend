"""Подписи статусов и справочных значений для админ-панели.

Значения словарей — русские msgid; перевод выполняется в момент
отрисовки (``_``), чтобы учитывать язык текущего запроса.
"""

from __future__ import annotations

from markupsafe import Markup, escape

from src.admin.i18n import _

# статус заявки → (подпись, цвет Tabler)
STATUS_LABELS: dict[str, tuple[str, str]] = {
    "DRAFT": ("Черновик", "secondary"),
    "SUBMITTED": ("Подана", "blue"),
    "SCORING_IN_PROGRESS": ("Скоринг KATM", "azure"),
    "SCORING_FAILED": ("Скоринг не пройден", "red"),
    "ELIGIBILITY_FAILED": ("Не соответствует требованиям", "red"),
    "READY_FOR_BANK": ("Готова к отправке в банк", "cyan"),
    "SENT_TO_BANK": ("Отправлена в банк", "indigo"),
    "BANK_REVIEW": ("Банк рассматривает", "purple"),
    "BANK_APPROVED": ("Банк одобрил", "teal"),
    "BANK_REJECTED": ("Банк отказал", "red"),
    "COUNCIL_REVIEW": ("Рассмотрение Советом", "orange"),
    "COUNCIL_APPROVED": ("Совет утвердил", "lime"),
    "COUNCIL_REJECTED": ("Совет отказал", "red"),
    "DEMAND_DOCUMENT_CREATED": ("Требование подтверждено", "green"),
    "RESOURCE_ALLOCATION": ("Выделение ресурсов", "yellow"),
    "COMPLETED": ("Завершена", "success"),
}

PIPELINE_GROUPS: list[tuple[str, list[str]]] = [
    ("Черновики", ["DRAFT"]),
    ("Скоринг", ["SUBMITTED", "SCORING_IN_PROGRESS"]),
    ("Банк", ["READY_FOR_BANK", "SENT_TO_BANK", "BANK_REVIEW"]),
    ("Фонд → Совет", ["BANK_APPROVED", "COUNCIL_REVIEW"]),
    ("Финансирование", ["COUNCIL_APPROVED", "DEMAND_DOCUMENT_CREATED", "RESOURCE_ALLOCATION"]),
    ("Завершены", ["COMPLETED"]),
    ("Отклонены", ["SCORING_FAILED", "ELIGIBILITY_FAILED", "BANK_REJECTED", "COUNCIL_REJECTED"]),
]

SUBJECT_LABELS: dict[str, str] = {
    "YATT": "ИП",
    "MCHJ": "ООО",
    "SELF_EMPLOYED": "Самозанятый",
}

DECISION_LABELS: dict[str, tuple[str, str]] = {
    "APPROVED": ("Одобрено", "green"),
    "REJECTED": ("Отклонено", "red"),
}

SCORING_RESULT_LABELS: dict[str, tuple[str, str]] = {
    "PASSED": ("Пройден", "green"),
    "FAILED": ("Не пройден", "red"),
    "TECHNICAL_ERROR": ("Техническая ошибка", "orange"),
}

DEMAND_STATUS_LABELS: dict[str, tuple[str, str]] = {
    "CREATED": ("Создан", "secondary"),
    "GENERATED": ("Сформирован", "green"),
    "REVOKED": ("Отозван", "red"),
}

USER_STATUS_LABELS: dict[str, tuple[str, str]] = {
    "ACTIVE": ("Активен", "green"),
    "BLOCKED": ("Заблокирован", "red"),
}

GENDER_LABELS: dict[str, str] = {
    "MALE": "Мужской",
    "FEMALE": "Женский",
}

ROLE_COLORS: dict[str, str] = {
    "SUPER_ADMIN": "red",
    "FUND_OPERATOR": "blue",
    "BANK_EMPLOYEE": "indigo",
    "COUNCIL_MEMBER": "orange",
    "APPLICANT": "teal",
}

# Событие истории статусов → подпись (msgid). Неизвестные события выводятся как есть.
EVENT_LABELS: dict[str, str] = {
    "created": "Заявка создана",
    "submitted": "Заявка отправлена",
    "scoring_started": "Запущен скоринг KATM",
    "scoring_passed": "Скоринг пройден",
    "scoring_failed": "Скоринг не пройден",
    "scoring_technical_error": "Техническая ошибка KATM",
    "scoring_retry": "Повтор скоринга",
    "eligibility_failed": "Не соответствует требованиям Фонда",
    "sent_to_bank": "Направлена в банк",
    "bank_accepted": "Банк принял заявку",
    "bank_approved": "Банк одобрил",
    "bank_rejected": "Банк отказал",
    "sent_to_council": "Направлена в Совет",
    "council_vote": "Голос члена Совета",
    "council_approved": "Совет утвердил",
    "council_rejected": "Совет отказал",
    "demand_document_created": "Создан документ «Требование подтверждено»",
    "resources_allocated": "Ресурсы выделены",
    "completed": "Заявка завершена",
}


def _key(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def badge(label: str, color: str, extra_class: str = "") -> Markup:
    return Markup(f'<span class="badge bg-{color}-lt {extra_class}">{escape(label)}</span>')


def status_label(value) -> str:
    key = _key(value)
    return _(STATUS_LABELS.get(key, (key, ""))[0])


def status_color(value) -> str:
    return STATUS_LABELS.get(_key(value), ("", "secondary"))[1]


def status_badge(value) -> Markup:
    if value is None:
        return Markup("—")
    return badge(status_label(value), status_color(value))


def labeled_badge(table: dict[str, tuple[str, str]], value) -> Markup | str:
    if value is None:
        return "—"
    key = _key(value)
    label, color = table.get(key, (key, "secondary"))
    return badge(_(label), color)


def subject_label(value) -> str:
    if value is None:
        return "—"
    key = _key(value)
    return _(SUBJECT_LABELS.get(key, key))


def gender_label(value) -> str:
    if value is None:
        return "—"
    key = _key(value)
    return _(GENDER_LABELS.get(key, key))


def event_label(event: str | None) -> str:
    if not event:
        return "—"
    return _(EVENT_LABELS.get(event, event))


def role_badge(role) -> Markup | str:
    if role is None:
        return "—"
    return badge(str(role.name), ROLE_COLORS.get(str(role.code), "secondary"))
