"""ModelView-ы SQLAdmin: русские подписи, фильтры, поиск, значки."""

from markupsafe import Markup
from sqladmin import ModelView
from sqladmin.filters import BooleanFilter, ForeignKeyFilter, StaticValuesFilter

from src.account.models.user_model import UserORM, UserStatus
from src.application.enums import ApplicationStatus, SubjectType
from src.application.models.application_model import ApplicationORM
from src.application.models.bank_model import BankORM
from src.application.models.council_assignment_model import CouncilAssignmentORM
from src.application.models.demand_document_model import DemandDocumentORM
from src.application.models.photo_model import ApplicationPhotoORM
from src.application.models.resource_allocation_model import ResourceAllocationORM
from src.application.models.scoring_model import ScoringAttemptORM
from src.application.models.status_history_model import StatusHistoryORM
from src.auth.models.refresh_token_model import RefreshTokenORM
from src.rbac.models.permission_model import PermissionORM
from src.rbac.models.role_model import RoleORM

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

SUBJECT_LABELS = {"YATT": "ИП", "MCHJ": "ООО", "SELF_EMPLOYED": "Самозанятый"}


def badge(label: str, color: str) -> Markup:
    return Markup(f'<span class="badge bg-{color}-lt">{label}</span>')


def fmt_status(model, attribute) -> Markup:
    value = getattr(model, "status", None)
    key = value.value if hasattr(value, "value") else str(value)
    label, color = STATUS_LABELS.get(key, (key, "secondary"))
    return badge(label, color)


def fmt_user_status(model, attribute) -> Markup:
    if model.status == UserStatus.ACTIVE:
        return badge("Активен", "green")
    return badge("Заблокирован", "red")


def fmt_subject(model, attribute) -> str:
    value = getattr(model, "subject_type", None)
    if value is None:
        return "—"
    key = value.value if hasattr(value, "value") else str(value)
    return SUBJECT_LABELS.get(key, key)


def fmt_bool(model, attribute):
    value = getattr(model, attribute.key if hasattr(attribute, "key") else attribute, None)
    if value is None:
        return "—"
    return (
        Markup('<i class="fa fa-check text-success"></i>')
        if value
        else Markup('<i class="fa fa-minus text-muted"></i>')
    )


def fmt_datetime(model, attribute):
    value = getattr(model, attribute.key if hasattr(attribute, "key") else attribute, None)
    return value.strftime("%d.%m.%Y %H:%M") if value else "—"


# ---------- Пользователи и доступ ----------


class UserAdmin(ModelView, model=UserORM):
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-users"
    category = "Пользователи и доступ"

    column_list = [
        UserORM.id,
        UserORM.username,
        UserORM.full_name,
        UserORM.role,
        UserORM.bank,
        UserORM.status,
        UserORM.last_login_at,
    ]
    column_details_exclude_list = [UserORM.hashed_password]
    column_searchable_list = [UserORM.username, UserORM.full_name, UserORM.phone, UserORM.pinfl]
    column_sortable_list = [UserORM.id, UserORM.username, UserORM.last_login_at, UserORM.created_at]
    column_default_sort = [(UserORM.id, True)]
    column_filters = [
        StaticValuesFilter(
            UserORM.status, [(s.value, s.value) for s in UserStatus], title="Статус"
        ),
        ForeignKeyFilter(UserORM.role_id, RoleORM.name, title="Роль"),
        ForeignKeyFilter(UserORM.bank_id, BankORM.name, title="Банк"),
    ]
    column_labels = {
        UserORM.id: "ID",
        UserORM.username: "Логин",
        UserORM.full_name: "Ф.И.О.",
        UserORM.phone: "Телефон",
        UserORM.email: "Email",
        UserORM.passport_number: "Паспорт",
        UserORM.pinfl: "ПИНФЛ",
        UserORM.inn: "ИНН",
        UserORM.status: "Статус",
        UserORM.role: "Роль",
        UserORM.role_id: "Роль",
        UserORM.bank: "Банк (scope)",
        UserORM.bank_id: "Банк (scope)",
        UserORM.organization: "Организация",
        UserORM.region: "Регион",
        UserORM.oneid_sub: "OneID sub",
        UserORM.last_login_at: "Последний вход",
        UserORM.created_at: "Создан",
        UserORM.updated_at: "Обновлён",
    }
    column_formatters = {
        UserORM.status: fmt_user_status,
        UserORM.last_login_at: fmt_datetime,
    }
    column_formatters_detail = {
        UserORM.status: fmt_user_status,
        UserORM.last_login_at: fmt_datetime,
        UserORM.created_at: fmt_datetime,
        UserORM.updated_at: fmt_datetime,
    }
    # Пароль задаётся через API или CLI (хеш нельзя вводить руками).
    form_excluded_columns = [
        UserORM.hashed_password,
        UserORM.created_at,
        UserORM.updated_at,
        UserORM.last_login_at,
    ]
    page_size = 25


class RoleAdmin(ModelView, model=RoleORM):
    name = "Роль"
    name_plural = "Роли"
    icon = "fa-solid fa-user-shield"
    category = "Пользователи и доступ"

    column_list = [
        RoleORM.id,
        RoleORM.code,
        RoleORM.name,
        RoleORM.is_superuser,
        RoleORM.is_system,
        RoleORM.permissions,
    ]
    column_searchable_list = [RoleORM.code, RoleORM.name]
    column_labels = {
        RoleORM.id: "ID",
        RoleORM.code: "Код",
        RoleORM.name: "Название",
        RoleORM.description: "Описание",
        RoleORM.is_superuser: "Суперпользователь",
        RoleORM.is_system: "Системная",
        RoleORM.permissions: "Права",
        RoleORM.users: "Пользователи",
        RoleORM.created_at: "Создана",
        RoleORM.updated_at: "Обновлена",
    }
    column_formatters = {RoleORM.is_superuser: fmt_bool, RoleORM.is_system: fmt_bool}
    form_excluded_columns = [RoleORM.users, RoleORM.created_at, RoleORM.updated_at]
    form_ajax_refs = {
        "permissions": {"fields": ("code", "name"), "order_by": "code"},
    }


class PermissionAdmin(ModelView, model=PermissionORM):
    name = "Право"
    name_plural = "Права"
    icon = "fa-solid fa-key"
    category = "Пользователи и доступ"

    column_list = [
        PermissionORM.id,
        PermissionORM.code,
        PermissionORM.name,
        PermissionORM.description,
    ]
    column_searchable_list = [PermissionORM.code, PermissionORM.name]
    column_labels = {
        PermissionORM.id: "ID",
        PermissionORM.code: "Код",
        PermissionORM.name: "Название",
        PermissionORM.description: "Описание",
        PermissionORM.roles: "Роли",
    }
    form_excluded_columns = [PermissionORM.roles]
    can_delete = False
    page_size = 50


class RefreshTokenAdmin(ModelView, model=RefreshTokenORM):
    name = "Сессия"
    name_plural = "Сессии (refresh-токены)"
    icon = "fa-solid fa-right-to-bracket"
    category = "Пользователи и доступ"

    column_list = [
        RefreshTokenORM.id,
        RefreshTokenORM.user,
        RefreshTokenORM.ip_address,
        RefreshTokenORM.user_agent,
        RefreshTokenORM.created_at,
        RefreshTokenORM.expires_at,
        RefreshTokenORM.is_revoked,
    ]
    column_details_exclude_list = [RefreshTokenORM.refresh_token]
    column_default_sort = [(RefreshTokenORM.created_at, True)]
    column_labels = {
        RefreshTokenORM.id: "ID",
        RefreshTokenORM.user: "Пользователь",
        RefreshTokenORM.user_id: "Пользователь",
        RefreshTokenORM.ip_address: "IP",
        RefreshTokenORM.user_agent: "User-Agent",
        RefreshTokenORM.created_at: "Вход",
        RefreshTokenORM.expires_at: "Истекает",
        RefreshTokenORM.is_revoked: "Отозван",
    }
    column_formatters = {
        RefreshTokenORM.created_at: fmt_datetime,
        RefreshTokenORM.expires_at: fmt_datetime,
        RefreshTokenORM.is_revoked: fmt_bool,
    }
    can_create = False
    can_edit = False
    page_size = 25


# ---------- Заявки ----------


class BankAdmin(ModelView, model=BankORM):
    name = "Банк"
    name_plural = "Банки"
    icon = "fa-solid fa-building-columns"
    category = "Справочники"

    column_list = [
        BankORM.id,
        BankORM.sort_order,
        BankORM.code,
        BankORM.name,
        BankORM.allowed_subject_types,
        BankORM.is_active,
    ]
    column_searchable_list = [BankORM.code, BankORM.name, BankORM.official_name]
    column_default_sort = [(BankORM.sort_order, False)]
    column_labels = {
        BankORM.id: "ID",
        BankORM.sort_order: "Порядок",
        BankORM.code: "Код",
        BankORM.name: "Название",
        BankORM.official_name: "Официальное название",
        BankORM.allowed_subject_types: "Типы субъектов",
        BankORM.is_active: "Активен",
        BankORM.created_at: "Создан",
        BankORM.updated_at: "Обновлён",
    }
    column_formatters = {BankORM.is_active: fmt_bool}
    form_excluded_columns = [BankORM.created_at, BankORM.updated_at]


class ApplicationAdmin(ModelView, model=ApplicationORM):
    name = "Заявка"
    name_plural = "Заявки"
    icon = "fa-solid fa-file-lines"
    category = "Заявки"

    column_list = [
        ApplicationORM.id,
        ApplicationORM.number,
        ApplicationORM.status,
        ApplicationORM.applicant_full_name,
        ApplicationORM.subject_type,
        ApplicationORM.legal_name,
        ApplicationORM.bank,
        ApplicationORM.scoring_retry_required,
        ApplicationORM.submitted_at,
        ApplicationORM.updated_at,
    ]
    column_searchable_list = [
        ApplicationORM.number,
        ApplicationORM.applicant_full_name,
        ApplicationORM.applicant_pinfl,
        ApplicationORM.legal_name,
    ]
    column_sortable_list = [
        ApplicationORM.id,
        ApplicationORM.number,
        ApplicationORM.submitted_at,
        ApplicationORM.updated_at,
    ]
    column_default_sort = [(ApplicationORM.updated_at, True)]
    column_filters = [
        StaticValuesFilter(
            ApplicationORM.status,
            [(s.value, STATUS_LABELS[s.value][0]) for s in ApplicationStatus],
            title="Статус",
        ),
        StaticValuesFilter(
            ApplicationORM.subject_type,
            [(s.value, SUBJECT_LABELS[s.value]) for s in SubjectType],
            title="Тип субъекта",
        ),
        ForeignKeyFilter(ApplicationORM.bank_id, BankORM.name, title="Банк"),
        BooleanFilter(ApplicationORM.scoring_retry_required, title="Ожидает повтора KATM"),
    ]
    column_labels = {
        ApplicationORM.id: "ID",
        ApplicationORM.number: "Номер",
        ApplicationORM.status: "Статус",
        ApplicationORM.applicant: "Заявитель",
        ApplicationORM.applicant_id: "Заявитель",
        ApplicationORM.applicant_full_name: "Ф.И.О. заявителя",
        ApplicationORM.applicant_phone: "Телефон",
        ApplicationORM.applicant_passport: "Паспорт",
        ApplicationORM.applicant_pinfl: "ПИНФЛ",
        ApplicationORM.applicant_inn: "ИНН",
        ApplicationORM.subject_type: "Тип субъекта",
        ApplicationORM.legal_name: "Юр. наименование",
        ApplicationORM.bank: "Банк",
        ApplicationORM.bank_id: "Банк",
        ApplicationORM.location_lat: "Широта",
        ApplicationORM.location_lng: "Долгота",
        ApplicationORM.location_address: "Адрес деятельности",
        ApplicationORM.location_confirmed: "Место подтверждено",
        ApplicationORM.submitted_at: "Отправлена",
        ApplicationORM.scoring_retry_required: "Ожидает повтора KATM",
        ApplicationORM.scoring_error_message: "Ошибка KATM",
        ApplicationORM.sent_to_bank_at: "В банк",
        ApplicationORM.bank_accepted_by: "Принял (банк)",
        ApplicationORM.bank_accepted_at: "Принята банком",
        ApplicationORM.bank_decision: "Решение банка",
        ApplicationORM.bank_decision_reason: "Причина банка",
        ApplicationORM.bank_decided_by: "Решил (банк)",
        ApplicationORM.bank_decided_at: "Решение банка (дата)",
        ApplicationORM.sent_to_council_at: "В Совет",
        ApplicationORM.sent_to_council_by: "Направил в Совет",
        ApplicationORM.council_decided_at: "Решение Совета (дата)",
        ApplicationORM.council_reject_reason: "Причина Совета",
        ApplicationORM.completed_at: "Завершена",
        ApplicationORM.photos: "Фотографии",
        ApplicationORM.status_history: "История",
        ApplicationORM.scoring_attempts: "Скоринг",
        ApplicationORM.council_assignments: "Члены Совета",
        ApplicationORM.demand_document: "Документ-требование",
        ApplicationORM.resource_allocation: "Выделение ресурсов",
        ApplicationORM.created_at: "Создана",
        ApplicationORM.updated_at: "Обновлена",
    }
    column_formatters = {
        ApplicationORM.status: fmt_status,
        ApplicationORM.subject_type: fmt_subject,
        ApplicationORM.scoring_retry_required: fmt_bool,
        ApplicationORM.submitted_at: fmt_datetime,
        ApplicationORM.updated_at: fmt_datetime,
    }
    column_formatters_detail = {
        ApplicationORM.status: fmt_status,
        ApplicationORM.subject_type: fmt_subject,
        ApplicationORM.scoring_retry_required: fmt_bool,
        ApplicationORM.location_confirmed: fmt_bool,
    }
    # Статусы меняются только через бизнес-операции API — здесь только просмотр
    # и исправление справочных полей черновика.
    can_create = False
    can_delete = False
    form_columns = [
        ApplicationORM.subject_type,
        ApplicationORM.legal_name,
        ApplicationORM.bank,
        ApplicationORM.location_address,
    ]
    page_size = 25


class StatusHistoryAdmin(ModelView, model=StatusHistoryORM):
    name = "Запись истории"
    name_plural = "История статусов"
    icon = "fa-solid fa-clock-rotate-left"
    category = "Заявки"

    column_list = [
        StatusHistoryORM.id,
        StatusHistoryORM.application,
        StatusHistoryORM.from_status,
        StatusHistoryORM.to_status,
        StatusHistoryORM.event,
        StatusHistoryORM.actor,
        StatusHistoryORM.actor_role,
        StatusHistoryORM.created_at,
    ]
    column_searchable_list = [StatusHistoryORM.event, StatusHistoryORM.comment]
    column_default_sort = [(StatusHistoryORM.id, True)]
    column_filters = [
        StaticValuesFilter(
            StatusHistoryORM.to_status,
            [(s.value, STATUS_LABELS[s.value][0]) for s in ApplicationStatus],
            title="Новый статус",
        ),
    ]
    column_labels = {
        StatusHistoryORM.id: "ID",
        StatusHistoryORM.application: "Заявка",
        StatusHistoryORM.application_id: "Заявка",
        StatusHistoryORM.from_status: "Из статуса",
        StatusHistoryORM.to_status: "В статус",
        StatusHistoryORM.event: "Событие",
        StatusHistoryORM.comment: "Комментарий",
        StatusHistoryORM.actor: "Кто",
        StatusHistoryORM.actor_id: "Кто",
        StatusHistoryORM.actor_role: "Роль",
        StatusHistoryORM.created_at: "Когда",
    }
    column_formatters = {StatusHistoryORM.created_at: fmt_datetime}
    # История неизменяема.
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 50


class ScoringAttemptAdmin(ModelView, model=ScoringAttemptORM):
    name = "Попытка скоринга"
    name_plural = "Скоринг KATM"
    icon = "fa-solid fa-magnifying-glass-chart"
    category = "Заявки"

    column_list = [
        ScoringAttemptORM.id,
        ScoringAttemptORM.application,
        ScoringAttemptORM.provider,
        ScoringAttemptORM.result,
        ScoringAttemptORM.eligibility_passed,
        ScoringAttemptORM.recorded_by,
        ScoringAttemptORM.created_at,
    ]
    column_default_sort = [(ScoringAttemptORM.id, True)]
    column_labels = {
        ScoringAttemptORM.id: "ID",
        ScoringAttemptORM.application: "Заявка",
        ScoringAttemptORM.application_id: "Заявка",
        ScoringAttemptORM.provider: "Провайдер",
        ScoringAttemptORM.result: "Результат",
        ScoringAttemptORM.eligibility_passed: "Требования Фонда",
        ScoringAttemptORM.details: "Детали",
        ScoringAttemptORM.error_message: "Ошибка",
        ScoringAttemptORM.recorded_by: "Внёс вручную",
        ScoringAttemptORM.recorded_by_id: "Внёс вручную",
        ScoringAttemptORM.created_at: "Когда",
    }
    column_formatters = {
        ScoringAttemptORM.eligibility_passed: fmt_bool,
        ScoringAttemptORM.created_at: fmt_datetime,
    }
    can_create = False
    can_edit = False
    can_delete = False


class CouncilAssignmentAdmin(ModelView, model=CouncilAssignmentORM):
    name = "Назначение Совета"
    name_plural = "Решения Совета"
    icon = "fa-solid fa-gavel"
    category = "Заявки"

    column_list = [
        CouncilAssignmentORM.id,
        CouncilAssignmentORM.application,
        CouncilAssignmentORM.council_member,
        CouncilAssignmentORM.assigned_at,
        CouncilAssignmentORM.decision,
        CouncilAssignmentORM.decided_at,
    ]
    column_default_sort = [(CouncilAssignmentORM.id, True)]
    column_labels = {
        CouncilAssignmentORM.id: "ID",
        CouncilAssignmentORM.application: "Заявка",
        CouncilAssignmentORM.application_id: "Заявка",
        CouncilAssignmentORM.council_member: "Член Совета",
        CouncilAssignmentORM.council_member_id: "Член Совета",
        CouncilAssignmentORM.assigned_by: "Направил",
        CouncilAssignmentORM.assigned_by_id: "Направил",
        CouncilAssignmentORM.assigned_at: "Направлена",
        CouncilAssignmentORM.decision: "Решение",
        CouncilAssignmentORM.reason: "Причина",
        CouncilAssignmentORM.decided_at: "Решение (дата)",
    }
    column_formatters = {
        CouncilAssignmentORM.assigned_at: fmt_datetime,
        CouncilAssignmentORM.decided_at: fmt_datetime,
    }
    can_create = False
    can_edit = False
    can_delete = False


class PhotoAdmin(ModelView, model=ApplicationPhotoORM):
    name = "Фотография"
    name_plural = "Фотографии заявок"
    icon = "fa-solid fa-image"
    category = "Заявки"

    column_list = [
        ApplicationPhotoORM.id,
        ApplicationPhotoORM.application,
        ApplicationPhotoORM.file_name,
        ApplicationPhotoORM.content_type,
        ApplicationPhotoORM.size,
        ApplicationPhotoORM.created_at,
    ]
    column_labels = {
        ApplicationPhotoORM.id: "ID",
        ApplicationPhotoORM.application: "Заявка",
        ApplicationPhotoORM.application_id: "Заявка",
        ApplicationPhotoORM.file_name: "Файл",
        ApplicationPhotoORM.storage_path: "Путь",
        ApplicationPhotoORM.content_type: "Тип",
        ApplicationPhotoORM.size: "Размер, байт",
        ApplicationPhotoORM.created_at: "Загружена",
    }
    column_formatters = {ApplicationPhotoORM.created_at: fmt_datetime}
    can_create = False
    can_edit = False


class DemandDocumentAdmin(ModelView, model=DemandDocumentORM):
    name = "Документ-требование"
    name_plural = "Документы «Требование подтверждено»"
    icon = "fa-solid fa-file-signature"
    category = "Заявки"

    column_list = [
        DemandDocumentORM.id,
        DemandDocumentORM.number,
        DemandDocumentORM.application,
        DemandDocumentORM.status,
        DemandDocumentORM.issued_at,
    ]
    column_labels = {
        DemandDocumentORM.id: "ID",
        DemandDocumentORM.number: "Номер",
        DemandDocumentORM.application: "Заявка",
        DemandDocumentORM.application_id: "Заявка",
        DemandDocumentORM.status: "Статус",
        DemandDocumentORM.file_path: "Файл",
        DemandDocumentORM.issued_at: "Выдан",
    }
    column_formatters = {DemandDocumentORM.issued_at: fmt_datetime}
    can_create = False
    can_delete = False


class ResourceAllocationAdmin(ModelView, model=ResourceAllocationORM):
    name = "Выделение ресурсов"
    name_plural = "Выделение ресурсов"
    icon = "fa-solid fa-coins"
    category = "Заявки"

    column_list = [
        ResourceAllocationORM.id,
        ResourceAllocationORM.application,
        ResourceAllocationORM.amount,
        ResourceAllocationORM.currency,
        ResourceAllocationORM.reference_number,
        ResourceAllocationORM.allocated_by,
        ResourceAllocationORM.allocated_at,
    ]
    column_labels = {
        ResourceAllocationORM.id: "ID",
        ResourceAllocationORM.application: "Заявка",
        ResourceAllocationORM.application_id: "Заявка",
        ResourceAllocationORM.amount: "Сумма",
        ResourceAllocationORM.currency: "Валюта",
        ResourceAllocationORM.reference_number: "Реквизиты",
        ResourceAllocationORM.details: "Детали",
        ResourceAllocationORM.allocated_by: "Зафиксировал",
        ResourceAllocationORM.allocated_by_id: "Зафиксировал",
        ResourceAllocationORM.allocated_at: "Дата",
    }
    column_formatters = {ResourceAllocationORM.allocated_at: fmt_datetime}
    can_create = False
    can_delete = False


ALL_VIEWS = [
    UserAdmin,
    RoleAdmin,
    PermissionAdmin,
    RefreshTokenAdmin,
    BankAdmin,
    ApplicationAdmin,
    StatusHistoryAdmin,
    ScoringAttemptAdmin,
    CouncilAssignmentAdmin,
    PhotoAdmin,
    DemandDocumentAdmin,
    ResourceAllocationAdmin,
]
