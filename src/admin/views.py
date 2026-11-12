from __future__ import annotations

import re

from markupsafe import Markup, escape
from sqladmin import BaseView, ModelView, expose
from sqladmin.filters import BooleanFilter, ForeignKeyFilter, StaticValuesFilter
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse

from src.account.models.user_model import UserORM, UserStatus
from src.admin.i18n import _, _l, fmt_dt, fmt_money, fmt_size
from src.admin.labels import (
    DECISION_LABELS,
    DEMAND_STATUS_LABELS,
    PRODUCT_STATUS_LABELS,
    SCORING_RESULT_LABELS,
    STATUS_LABELS,
    SUBJECT_LABELS,
    USER_STATUS_LABELS,
    badge,
    gender_label,
    labeled_badge,
    language_label,
    role_badge,
    status_badge,
    subject_label,
)
from src.application.enums import ApplicationStatus, SubjectType
from src.application.models.answer_model import ApplicationFieldFileORM
from src.application.models.application_model import ApplicationORM
from src.application.models.bank_model import BankORM
from src.application.models.council_assignment_model import CouncilAssignmentORM
from src.application.models.demand_document_model import DemandDocumentORM
from src.application.models.document_model import ApplicationDocumentORM
from src.application.models.founder_model import ApplicationFounderORM
from src.application.models.photo_model import ApplicationPhotoORM
from src.application.models.resource_allocation_model import ResourceAllocationORM
from src.application.models.scoring_model import ScoringAttemptORM
from src.application.models.status_history_model import StatusHistoryORM
from src.application.services.photo_storage import (
    DocumentStorage,
    FieldPhotoStorage,
    PhotoStorage,
)
from src.application.services.purge_service import ApplicationPurgeService
from src.auth.models.refresh_token_model import RefreshTokenORM
from src.database import async_session_maker
from src.product.enums import ProductStatus
from src.product.models.product_model import (
    ProductCategoryORM,
    ProductFieldORM,
    ProductORM,
    ProductStageORM,
    ProductTranslationORM,
    ru_name,
)
from src.rbac.access import DIRECTION_ROLES, uses_personal_permissions
from src.rbac.models.permission_model import PermissionORM
from src.rbac.models.role_model import RoleORM
from src.utils.db_manager import DBManager

CATEGORY_ACCESS = _l("Пользователи и доступ")
CATEGORY_DICTS = _l("Справочники")
CATEGORY_APPLICATIONS = _l("Заявки")
CATEGORY_PRODUCTS = _l("Продукты")




class LocalizedLabelsMixin:
    """``column_labels`` содержит msgid; ``_column_labels`` отдаёт перевод
    для языка текущего запроса. SQLAdmin читает ``_column_labels`` в шаблонах,
    экспорте и плейсхолдере поиска (там нужны именно строки, не прокси)."""

    @property
    def _column_labels(self) -> dict:
        source = self.__dict__.get("_column_labels_source", {})
        return {key: _(value) for key, value in source.items()}

    @_column_labels.setter
    def _column_labels(self, value: dict) -> None:
        self.__dict__["_column_labels_source"] = value



def _attr_value(model, attribute):
    key = attribute.key if hasattr(attribute, "key") else attribute
    return getattr(model, key, None)


def fmt_status(model, attribute) -> Markup:
    return status_badge(getattr(model, "status", None))


def fmt_history_status(model, attribute) -> Markup:
    return status_badge(_attr_value(model, attribute))


def fmt_user_status(model, attribute) -> Markup | str:
    return labeled_badge(USER_STATUS_LABELS, model.status)


def fmt_role(model, attribute) -> Markup | str:
    return role_badge(getattr(model, "role", None))


def fmt_subject(model, attribute) -> str:
    return subject_label(getattr(model, "subject_type", None))


def fmt_gender(model, attribute) -> str:
    return gender_label(_attr_value(model, attribute))


def fmt_date(model, attribute) -> str:
    value = _attr_value(model, attribute)
    return value.strftime("%d.%m.%Y") if value else "—"


def fmt_decision(model, attribute) -> Markup | str:
    return labeled_badge(DECISION_LABELS, _attr_value(model, attribute))


def fmt_scoring_result(model, attribute) -> Markup | str:
    return labeled_badge(SCORING_RESULT_LABELS, _attr_value(model, attribute))


def fmt_demand_status(model, attribute) -> Markup | str:
    return labeled_badge(DEMAND_STATUS_LABELS, _attr_value(model, attribute))


def fmt_bool(model, attribute):
    value = _attr_value(model, attribute)
    if value is None:
        return "—"
    return (
        Markup('<i class="fa fa-check text-success"></i>')
        if value
        else Markup('<i class="fa fa-minus text-muted"></i>')
    )


def fmt_datetime(model, attribute) -> str:
    return fmt_dt(_attr_value(model, attribute))


def fmt_amount(model, attribute) -> str:
    return fmt_money(getattr(model, "amount", None), getattr(model, "currency", None))


def fmt_uzs(model, attribute) -> str:
    return fmt_money(_attr_value(model, attribute))


def fmt_file_size(model, attribute) -> str:
    return fmt_size(getattr(model, "size", None))


def fmt_photo_preview(model, attribute) -> Markup:
    url = f"/admin/application-photo/{model.id}"
    return Markup(
        f'<a href="{url}" target="_blank"><img src="{url}" alt="{escape(model.file_name)}" '
        'class="jg-thumb"></a>'
    )


def fmt_document_link(model, attribute) -> Markup:
    return Markup(
        f'<a href="/admin/application-document/{model.id}" target="_blank">'
        f'<i class="fa-solid fa-file-arrow-down me-1"></i>{escape(model.file_name)}</a>'
    )


def fmt_subject_types(model, attribute) -> Markup | str:
    values = getattr(model, "allowed_subject_types", None) or []
    if not values:
        return "—"
    return Markup(" ").join(badge(subject_label(v), "blue") for v in values)


def fmt_product_name(model, attribute) -> str:
    return ru_name(getattr(model, "translations", None) or []) or "—"


def fmt_product_status(model, attribute) -> Markup | str:
    return labeled_badge(PRODUCT_STATUS_LABELS, getattr(model, "status", None))


def fmt_product_banks(model, attribute) -> Markup | str:
    banks = getattr(model, "banks", None) or []
    if not banks:
        return "—"
    return Markup(" ").join(badge(b.name, "indigo" if b.is_active else "secondary") for b in banks)


def fmt_stages_count(model, attribute) -> str:
    return str(len(getattr(model, "stages", None) or []))


def fmt_application_product(model, attribute) -> Markup | str:
    product = getattr(model, "product", None)
    if product is None:
        return "—"
    return Markup(
        f'<a href="/admin/product-orm/details/{product.id}">'
        f"{escape(ru_name(product.translations))}</a>"
    )


def fmt_translation_product(model, attribute) -> Markup | str:
    product = getattr(model, "product", None)
    if product is None:
        return "—"
    return Markup(f'<a href="/admin/product-orm/details/{product.id}">#{product.id}</a>')


def fmt_product_category(model, attribute) -> Markup | str:
    category = getattr(model, "category", None)
    if category is None:
        return "—"
    return Markup(
        f'<a href="/admin/product-category-orm/details/{category.id}">'
        f"{escape(ru_name(category.translations))}</a>"
    )


def fmt_translations(model, attribute) -> Markup | str:
    items = getattr(model, "translations", None) or []
    if not items:
        return "—"
    return Markup("<br>").join(
        Markup("{}: {}").format(language_label(t.language), t.name) for t in items
    )


def fmt_language(model, attribute) -> str:
    return language_label(_attr_value(model, attribute))



PINFL_RE = re.compile(r"\d{14}")


class UserAdmin(LocalizedLabelsMixin, ModelView, model=UserORM):
    name = _l("Пользователь")
    name_plural = _l("Пользователи")
    icon = "fa-solid fa-users"
    category = CATEGORY_ACCESS

    column_list = [
        UserORM.id,
        UserORM.username,
        UserORM.full_name,
        UserORM.role,
        UserORM.bank,
        UserORM.is_direction_admin,
        UserORM.status,
        UserORM.last_login_at,
    ]
    column_details_exclude_list = [UserORM.hashed_password]
    column_searchable_list = [UserORM.username, UserORM.full_name, UserORM.phone, UserORM.pinfl]
    column_sortable_list = [UserORM.id, UserORM.username, UserORM.last_login_at, UserORM.created_at]
    column_default_sort = [(UserORM.id, True)]
    column_filters = [
        StaticValuesFilter(
            UserORM.status,
            [(s.value, _l(USER_STATUS_LABELS[s.value][0])) for s in UserStatus],
            title=_l("Статус"),
        ),
        ForeignKeyFilter(UserORM.role_id, RoleORM.name, title=_l("Роль")),
        ForeignKeyFilter(UserORM.bank_id, BankORM.name, title=_l("Банк")),
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
        UserORM.gender: "Пол",
        UserORM.date_of_birth: "Дата рождения",
        UserORM.status: "Статус",
        UserORM.role: "Роль",
        UserORM.role_id: "Роль",
        UserORM.bank: "Банк (scope)",
        UserORM.bank_id: "Банк (scope)",
        UserORM.organization: "Организация",
        UserORM.region: "Регион",
        UserORM.sso_sub: "YIA SSO sub",
        UserORM.is_direction_admin: "Админ направления",
        UserORM.permissions: "Личные права",
        UserORM.last_login_at: "Последний вход",
        UserORM.created_at: "Создан",
        UserORM.updated_at: "Обновлён",
    }
    column_formatters = {
        UserORM.status: fmt_user_status,
        UserORM.role: fmt_role,
        UserORM.is_direction_admin: fmt_bool,
        UserORM.last_login_at: fmt_datetime,
    }
    column_formatters_detail = {
        UserORM.is_direction_admin: fmt_bool,
        UserORM.status: fmt_user_status,
        UserORM.role: fmt_role,
        UserORM.gender: fmt_gender,
        UserORM.date_of_birth: fmt_date,
        UserORM.last_login_at: fmt_datetime,
        UserORM.created_at: fmt_datetime,
        UserORM.updated_at: fmt_datetime,
    }
    form_excluded_columns = [
        UserORM.hashed_password,
        UserORM.created_at,
        UserORM.updated_at,
        UserORM.last_login_at,
    ]
    form_ajax_refs = {
        "permissions": {"fields": ("code", "name"), "order_by": "code"},
    }
    page_size = 25

    async def on_model_change(self, data: dict, model, is_created: bool, request: Request) -> None:
        await self._check_direction_admin(data, model)
        await self._default_permissions(data, model, is_created)

        if "pinfl" not in data:
            return
        pinfl = (data["pinfl"] or "").strip() or None
        if pinfl is not None and not PINFL_RE.fullmatch(pinfl):
            raise ValueError(_("ПИНФЛ должен состоять из 14 цифр"))
        data["pinfl"] = pinfl

        if pinfl is not None:
            async with async_session_maker() as session:
                owner_id = await session.scalar(select(UserORM.id).where(UserORM.pinfl == pinfl))
            if owner_id is not None and (is_created or owner_id != model.id):
                raise ValueError(_("Пользователь с таким ПИНФЛ уже существует"))

        if not is_created and pinfl != model.pinfl:
            data["sso_sub"] = None

    @staticmethod
    async def _check_direction_admin(data: dict, model) -> None:
        is_admin = data.get("is_direction_admin", getattr(model, "is_direction_admin", False))
        if not is_admin:
            return
        role = data["role"] if "role" in data else getattr(model, "role", None)
        if role is not None and not hasattr(role, "code"):
            async with async_session_maker() as session:
                role = await session.get(RoleORM, int(role))
        if role is None or role.code not in DIRECTION_ROLES:
            raise ValueError(_("Админ направления должен иметь роль направления"))

    @staticmethod
    async def _default_permissions(data: dict, model, is_created: bool) -> None:
        if "permissions" not in data or data["permissions"]:
            return
        role_value = data.get("role")
        if not role_value:
            return
        role_id = int(role_value.id if hasattr(role_value, "id") else role_value)
        if not (is_created or role_id != model.role_id or not model.permissions):
            return
        async with async_session_maker() as session:
            role = await session.get(RoleORM, role_id)
            if role is None or not uses_personal_permissions(role):
                return
            data["permissions"] = [str(permission.id) for permission in role.permissions]


class RoleAdmin(LocalizedLabelsMixin, ModelView, model=RoleORM):
    name = _l("Роль")
    name_plural = _l("Роли")
    icon = "fa-solid fa-user-shield"
    category = CATEGORY_ACCESS

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


class PermissionAdmin(LocalizedLabelsMixin, ModelView, model=PermissionORM):
    name = _l("Право")
    name_plural = _l("Права")
    icon = "fa-solid fa-key"
    category = CATEGORY_ACCESS

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


class RefreshTokenAdmin(LocalizedLabelsMixin, ModelView, model=RefreshTokenORM):
    name = _l("Сессия")
    name_plural = _l("Сессии (refresh-токены)")
    icon = "fa-solid fa-right-to-bracket"
    category = CATEGORY_ACCESS

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




class BankAdmin(LocalizedLabelsMixin, ModelView, model=BankORM):
    name = _l("Банк")
    name_plural = _l("Банки")
    icon = "fa-solid fa-building-columns"
    category = CATEGORY_DICTS

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
    column_formatters = {
        BankORM.is_active: fmt_bool,
        BankORM.allowed_subject_types: fmt_subject_types,
    }
    column_formatters_detail = {
        BankORM.is_active: fmt_bool,
        BankORM.allowed_subject_types: fmt_subject_types,
    }
    form_excluded_columns = [BankORM.created_at, BankORM.updated_at]



class ApplicationAdmin(LocalizedLabelsMixin, ModelView, model=ApplicationORM):
    name = _l("Заявка")
    name_plural = _l("Заявки")
    icon = "fa-solid fa-file-lines"
    category = CATEGORY_APPLICATIONS
    details_template = "sqladmin/application_details.html"

    column_list = [
        ApplicationORM.id,
        ApplicationORM.number,
        ApplicationORM.status,
        ApplicationORM.applicant_full_name,
        ApplicationORM.product,
        ApplicationORM.subject_type,
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
            [(s.value, _l(STATUS_LABELS[s.value][0])) for s in ApplicationStatus],
            title=_l("Статус"),
        ),
        StaticValuesFilter(
            ApplicationORM.subject_type,
            [(s.value, _l(SUBJECT_LABELS[s.value])) for s in SubjectType],
            title=_l("Тип субъекта"),
        ),
        ForeignKeyFilter(ApplicationORM.bank_id, BankORM.name, title=_l("Банк")),
        BooleanFilter(ApplicationORM.scoring_retry_required, title=_l("Ожидает повтора KATM")),
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
        ApplicationORM.applicant_email: "Email",
        ApplicationORM.applicant_gender: "Пол",
        ApplicationORM.applicant_date_of_birth: "Дата рождения",
        ApplicationORM.subject_type: "Тип субъекта",
        ApplicationORM.legal_name: "Юр. наименование",
        ApplicationORM.company_inn: "СТИР предприятия",
        ApplicationORM.director_full_name: "Ф.И.О. руководителя",
        ApplicationORM.director_passport: "Паспорт руководителя",
        ApplicationORM.director_phone: "Телефон руководителя",
        ApplicationORM.director_date_of_birth: "Дата рождения руководителя",
        ApplicationORM.founders: "Учредители",
        ApplicationORM.project_requested_amount: "Запрашиваемая сумма",
        ApplicationORM.project_loan_term_months: "Срок кредита, мес.",
        ApplicationORM.project_total_cost: "Стоимость проекта",
        ApplicationORM.project_jobs_count: "Рабочие места",
        ApplicationORM.project_description: "Описание проекта",
        ApplicationORM.bank: "Банк",
        ApplicationORM.bank_id: "Банк",
        ApplicationORM.location_lat: "Широта",
        ApplicationORM.location_lng: "Долгота",
        ApplicationORM.location_region: "Область",
        ApplicationORM.location_district: "Район",
        ApplicationORM.location_makhalla: "Махалля",
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
        ApplicationORM.fund_decided_at: "Решение Фонда (дата)",
        ApplicationORM.fund_reject_reason: "Причина Фонда",
        ApplicationORM.council_decided_at: "Решение Совета (дата)",
        ApplicationORM.council_reject_reason: "Причина Совета",
        ApplicationORM.completed_at: "Завершена",
        ApplicationORM.photos: "Фотографии",
        ApplicationORM.documents: "Документы",
        ApplicationORM.status_history: "История",
        ApplicationORM.scoring_attempts: "Скоринг",
        ApplicationORM.council_assignments: "Члены Совета",
        ApplicationORM.demand_document: "Документ-требование",
        ApplicationORM.resource_allocation: "Выделение ресурсов",
        ApplicationORM.product: "Продукт",
        ApplicationORM.product_id: "Продукт",
        ApplicationORM.created_at: "Создана",
        ApplicationORM.updated_at: "Обновлена",
    }
    column_formatters = {
        ApplicationORM.status: fmt_status,
        ApplicationORM.product: fmt_application_product,
        ApplicationORM.subject_type: fmt_subject,
        ApplicationORM.scoring_retry_required: fmt_bool,
        ApplicationORM.submitted_at: fmt_datetime,
        ApplicationORM.updated_at: fmt_datetime,
    }
    column_formatters_detail = {
        ApplicationORM.status: fmt_status,
        ApplicationORM.subject_type: fmt_subject,
        ApplicationORM.applicant_gender: fmt_gender,
        ApplicationORM.applicant_date_of_birth: fmt_date,
        ApplicationORM.director_date_of_birth: fmt_date,
        ApplicationORM.project_requested_amount: fmt_uzs,
        ApplicationORM.project_total_cost: fmt_uzs,
        ApplicationORM.bank_decision: fmt_decision,
        ApplicationORM.scoring_retry_required: fmt_bool,
        ApplicationORM.location_confirmed: fmt_bool,
        ApplicationORM.submitted_at: fmt_datetime,
        ApplicationORM.sent_to_bank_at: fmt_datetime,
        ApplicationORM.bank_accepted_at: fmt_datetime,
        ApplicationORM.bank_decided_at: fmt_datetime,
        ApplicationORM.sent_to_council_at: fmt_datetime,
        ApplicationORM.fund_decided_at: fmt_datetime,
        ApplicationORM.council_decided_at: fmt_datetime,
        ApplicationORM.completed_at: fmt_datetime,
        ApplicationORM.created_at: fmt_datetime,
        ApplicationORM.updated_at: fmt_datetime,
    }
    can_create = False
    can_delete = True
    form_columns = [
        ApplicationORM.subject_type,
        ApplicationORM.legal_name,
        ApplicationORM.bank,
        ApplicationORM.location_region,
        ApplicationORM.location_district,
        ApplicationORM.location_makhalla,
        ApplicationORM.location_address,
    ]
    page_size = 25

    async def delete_model(self, request: Request, pk) -> None:
        """Удаление заявки целиком: записи в БД (каскадом) и файлы на диске."""
        async with DBManager(async_session_maker) as db:
            await ApplicationPurgeService(db).purge(int(pk))

    async def get_object_for_details(self, request: Request):
        # Карточка заявки показывает таймлайн, фото, решения Совета и т.д.
        # Вложенные связи подгружаем заранее: ленивая загрузка в async-шаблоне невозможна.
        stmt = self.details_query(request).options(
            selectinload(ApplicationORM.status_history).selectinload(StatusHistoryORM.actor),
            selectinload(ApplicationORM.photos),
            selectinload(ApplicationORM.product).selectinload(ProductORM.translations),
            selectinload(ApplicationORM.product)
            .selectinload(ProductORM.stages)
            .selectinload(ProductStageORM.translations),
            selectinload(ApplicationORM.product)
            .selectinload(ProductORM.stages)
            .selectinload(ProductStageORM.fields)
            .selectinload(ProductFieldORM.translations),
            selectinload(ApplicationORM.field_values),
            selectinload(ApplicationORM.field_files),
            selectinload(ApplicationORM.scoring_attempts).selectinload(
                ScoringAttemptORM.recorded_by
            ),
            selectinload(ApplicationORM.council_assignments).selectinload(
                CouncilAssignmentORM.council_member
            ),
            selectinload(ApplicationORM.council_assignments).selectinload(
                CouncilAssignmentORM.assigned_by
            ),
            selectinload(ApplicationORM.demand_document),
            selectinload(ApplicationORM.resource_allocation).selectinload(
                ResourceAllocationORM.allocated_by
            ),
            selectinload(ApplicationORM.bank_accepted_by),
            selectinload(ApplicationORM.bank_decided_by),
            selectinload(ApplicationORM.sent_to_council_by),
        )
        return await self._get_object_by_pk(stmt)


class StatusHistoryAdmin(LocalizedLabelsMixin, ModelView, model=StatusHistoryORM):
    name = _l("Запись истории")
    name_plural = _l("История статусов")
    icon = "fa-solid fa-clock-rotate-left"
    category = CATEGORY_APPLICATIONS

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
            [(s.value, _l(STATUS_LABELS[s.value][0])) for s in ApplicationStatus],
            title=_l("Новый статус"),
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
    column_formatters = {
        StatusHistoryORM.from_status: fmt_history_status,
        StatusHistoryORM.to_status: fmt_history_status,
        StatusHistoryORM.created_at: fmt_datetime,
    }
    column_formatters_detail = column_formatters
    # История неизменяема.
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 50


class ScoringAttemptAdmin(LocalizedLabelsMixin, ModelView, model=ScoringAttemptORM):
    name = _l("Попытка скоринга")
    name_plural = _l("Скоринг KATM")
    icon = "fa-solid fa-magnifying-glass-chart"
    category = CATEGORY_APPLICATIONS

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
        ScoringAttemptORM.recorded_by: "Запустил повтор",
        ScoringAttemptORM.recorded_by_id: "Запустил повтор",
        ScoringAttemptORM.created_at: "Когда",
    }
    column_formatters = {
        ScoringAttemptORM.result: fmt_scoring_result,
        ScoringAttemptORM.eligibility_passed: fmt_bool,
        ScoringAttemptORM.created_at: fmt_datetime,
    }
    column_formatters_detail = column_formatters
    can_create = False
    can_edit = False
    can_delete = False


class CouncilAssignmentAdmin(LocalizedLabelsMixin, ModelView, model=CouncilAssignmentORM):
    name = _l("Назначение Совета")
    name_plural = _l("Решения Совета")
    icon = "fa-solid fa-gavel"
    category = CATEGORY_APPLICATIONS

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
        CouncilAssignmentORM.decision: fmt_decision,
        CouncilAssignmentORM.assigned_at: fmt_datetime,
        CouncilAssignmentORM.decided_at: fmt_datetime,
    }
    column_formatters_detail = column_formatters
    can_create = False
    can_edit = False
    can_delete = False


class FounderAdmin(LocalizedLabelsMixin, ModelView, model=ApplicationFounderORM):
    name = _l("Учредитель")
    name_plural = _l("Учредители")
    icon = "fa-solid fa-people-group"
    category = CATEGORY_APPLICATIONS

    column_list = [
        ApplicationFounderORM.id,
        ApplicationFounderORM.application,
        ApplicationFounderORM.full_name,
        ApplicationFounderORM.passport_number,
        ApplicationFounderORM.date_of_birth,
        ApplicationFounderORM.created_at,
    ]
    column_searchable_list = [
        ApplicationFounderORM.full_name,
        ApplicationFounderORM.passport_number,
    ]
    column_sortable_list = [ApplicationFounderORM.id, ApplicationFounderORM.created_at]
    column_default_sort = [(ApplicationFounderORM.id, True)]
    column_labels = {
        ApplicationFounderORM.id: "ID",
        ApplicationFounderORM.application: "Заявка",
        ApplicationFounderORM.application_id: "Заявка",
        ApplicationFounderORM.full_name: "Ф.И.О.",
        ApplicationFounderORM.passport_number: "Паспорт",
        ApplicationFounderORM.date_of_birth: "Дата рождения",
        ApplicationFounderORM.created_at: "Добавлен",
    }
    column_formatters = {
        ApplicationFounderORM.date_of_birth: fmt_date,
        ApplicationFounderORM.created_at: fmt_datetime,
    }
    column_formatters_detail = {
        ApplicationFounderORM.date_of_birth: fmt_date,
        ApplicationFounderORM.created_at: fmt_datetime,
    }
    form_excluded_columns = [ApplicationFounderORM.created_at]
    page_size = 25


class DocumentAdmin(LocalizedLabelsMixin, ModelView, model=ApplicationDocumentORM):
    name = _l("Документ заявки")
    name_plural = _l("Документы заявок")
    icon = "fa-solid fa-file-pdf"
    category = CATEGORY_APPLICATIONS

    can_create = False
    can_edit = False

    column_list = [
        ApplicationDocumentORM.id,
        ApplicationDocumentORM.application,
        ApplicationDocumentORM.file_name,
        ApplicationDocumentORM.content_type,
        ApplicationDocumentORM.size,
        ApplicationDocumentORM.created_at,
    ]
    column_searchable_list = [ApplicationDocumentORM.file_name]
    column_sortable_list = [ApplicationDocumentORM.id, ApplicationDocumentORM.created_at]
    column_default_sort = [(ApplicationDocumentORM.id, True)]
    column_labels = {
        ApplicationDocumentORM.id: "ID",
        ApplicationDocumentORM.application: "Заявка",
        ApplicationDocumentORM.application_id: "Заявка",
        ApplicationDocumentORM.file_name: "Файл",
        ApplicationDocumentORM.storage_path: "Путь",
        ApplicationDocumentORM.content_type: "Тип",
        ApplicationDocumentORM.size: "Размер",
        ApplicationDocumentORM.created_at: "Загружен",
    }
    column_formatters = {
        ApplicationDocumentORM.file_name: lambda m, a: fmt_document_link(m, a),
        ApplicationDocumentORM.size: fmt_file_size,
        ApplicationDocumentORM.created_at: fmt_datetime,
    }
    column_formatters_detail = {
        ApplicationDocumentORM.file_name: lambda m, a: fmt_document_link(m, a),
        ApplicationDocumentORM.size: fmt_file_size,
        ApplicationDocumentORM.created_at: fmt_datetime,
    }
    page_size = 25


class PhotoAdmin(LocalizedLabelsMixin, ModelView, model=ApplicationPhotoORM):
    name = _l("Фотография")
    name_plural = _l("Фотографии заявок")
    icon = "fa-solid fa-image"
    category = CATEGORY_APPLICATIONS

    column_list = [
        ApplicationPhotoORM.id,
        ApplicationPhotoORM.storage_path,
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
        ApplicationPhotoORM.storage_path: "Превью",
        ApplicationPhotoORM.content_type: "Тип",
        ApplicationPhotoORM.size: "Размер",
        ApplicationPhotoORM.created_at: "Загружена",
    }
    column_formatters = {
        ApplicationPhotoORM.storage_path: fmt_photo_preview,
        ApplicationPhotoORM.size: fmt_file_size,
        ApplicationPhotoORM.created_at: fmt_datetime,
    }
    column_formatters_detail = column_formatters
    can_create = False
    can_edit = False


class DemandDocumentAdmin(LocalizedLabelsMixin, ModelView, model=DemandDocumentORM):
    name = _l("Документ-требование")
    name_plural = _l("Документы «Требование подтверждено»")
    icon = "fa-solid fa-file-signature"
    category = CATEGORY_APPLICATIONS

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
    column_formatters = {
        DemandDocumentORM.status: fmt_demand_status,
        DemandDocumentORM.issued_at: fmt_datetime,
    }
    column_formatters_detail = column_formatters
    can_create = False
    can_delete = False


class ResourceAllocationAdmin(LocalizedLabelsMixin, ModelView, model=ResourceAllocationORM):
    name = _l("Выделение ресурсов")
    name_plural = _l("Выделение ресурсов")
    icon = "fa-solid fa-coins"
    category = CATEGORY_APPLICATIONS

    column_list = [
        ResourceAllocationORM.id,
        ResourceAllocationORM.application,
        ResourceAllocationORM.amount,
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
    column_formatters = {
        ResourceAllocationORM.amount: fmt_amount,
        ResourceAllocationORM.allocated_at: fmt_datetime,
    }
    column_formatters_detail = column_formatters
    can_create = False
    can_delete = False


# ---------- Продукты ----------


class ProductAdmin(LocalizedLabelsMixin, ModelView, model=ProductORM):
    """Продукты Фонда. Этапы, поля и публикация — через API Фонда (`/fund/products`):
    там проверяются три языка, блокировка продукта с заявками и готовность к публикации.
    Здесь — просмотр и правка банков, типов субъекта и сроков приёма."""

    name = _l("Продукт")
    name_plural = _l("Продукты")
    icon = "fa-solid fa-box-open"
    category = CATEGORY_PRODUCTS
    details_template = "sqladmin/product_details.html"

    column_list = [
        ProductORM.id,
        ProductORM.translations,
        ProductORM.category,
        ProductORM.status,
        ProductORM.allowed_subject_types,
        ProductORM.accept_from,
        ProductORM.accept_to,
        ProductORM.banks,
        ProductORM.stages,
        ProductORM.updated_at,
    ]
    column_sortable_list = [ProductORM.id, ProductORM.accept_from, ProductORM.updated_at]
    column_default_sort = [(ProductORM.id, True)]
    column_filters = [
        StaticValuesFilter(
            ProductORM.status,
            [(s.value, _l(PRODUCT_STATUS_LABELS[s.value][0])) for s in ProductStatus],
            title=_l("Статус"),
        ),
    ]
    column_labels = {
        ProductORM.id: "ID",
        ProductORM.translations: "Название",
        ProductORM.category: "Категория",
        ProductORM.category_id: "Категория",
        ProductORM.status: "Статус",
        ProductORM.allowed_subject_types: "Типы субъектов",
        ProductORM.accept_from: "Приём с",
        ProductORM.accept_to: "Приём по",
        ProductORM.banks: "Банки",
        ProductORM.stages: "Этапов",
        ProductORM.created_at: "Создан",
        ProductORM.updated_at: "Обновлён",
    }
    column_formatters = {
        ProductORM.translations: fmt_product_name,
        ProductORM.category: fmt_product_category,
        ProductORM.status: fmt_product_status,
        ProductORM.allowed_subject_types: fmt_subject_types,
        ProductORM.accept_from: fmt_date,
        ProductORM.accept_to: fmt_date,
        ProductORM.banks: fmt_product_banks,
        ProductORM.stages: fmt_stages_count,
        ProductORM.updated_at: fmt_datetime,
    }
    can_create = False
    can_delete = False
    form_columns = [
        ProductORM.category,
        ProductORM.allowed_subject_types,
        ProductORM.accept_from,
        ProductORM.accept_to,
        ProductORM.banks,
    ]
    page_size = 25

    async def on_model_change(self, data: dict, model, is_created: bool, request: Request) -> None:
        category = data.get("category")
        if category is not None and str(getattr(category, "id", category)) != str(
            model.category_id
        ):
            async with async_session_maker() as session:
                chosen = await session.get(
                    ProductCategoryORM, int(getattr(category, "id", category))
                )
            if chosen is None or not chosen.is_active:
                raise ValueError(_("Выберите активную категорию"))
        accept_from = data.get("accept_from", model.accept_from)
        accept_to = data.get("accept_to", model.accept_to)
        if accept_from and accept_to and accept_from > accept_to:
            raise ValueError(_("Начало приёма не может быть позже окончания"))
        if "allowed_subject_types" in data:
            values = list(data["allowed_subject_types"] or [])
            if not values:
                raise ValueError(_("Укажите хотя бы один тип субъекта"))
            unknown = [v for v in values if v not in {t.value for t in SubjectType}]
            if unknown:
                raise ValueError(_("Неизвестный тип субъекта: %s") % ", ".join(unknown))

    async def get_object_for_details(self, request: Request):
        stmt = self.details_query(request).options(
            selectinload(ProductORM.translations),
            selectinload(ProductORM.category).selectinload(ProductCategoryORM.translations),
            selectinload(ProductORM.banks),
            selectinload(ProductORM.stages).selectinload(ProductStageORM.translations),
            selectinload(ProductORM.stages)
            .selectinload(ProductStageORM.fields)
            .selectinload(ProductFieldORM.translations),
        )
        product = await self._get_object_by_pk(stmt)
        if product is not None:
            async with async_session_maker() as session:
                product.applications_count = await session.scalar(
                    select(func.count()).where(ApplicationORM.product_id == product.id)
                )
        return product


class ProductCategoryAdmin(LocalizedLabelsMixin, ModelView, model=ProductCategoryORM):
    """Категории продуктов. Создание и названия на ru / uz / en — через API Фонда
    (`/fund/product-categories`); здесь — активность и порядок."""

    name = _l("Категория продуктов")
    name_plural = _l("Категории продуктов")
    icon = "fa-solid fa-folder-tree"
    category = CATEGORY_PRODUCTS

    column_list = [
        ProductCategoryORM.id,
        ProductCategoryORM.translations,
        ProductCategoryORM.is_active,
        ProductCategoryORM.sort_order,
        ProductCategoryORM.updated_at,
    ]
    column_details_list = [
        ProductCategoryORM.id,
        ProductCategoryORM.translations,
        ProductCategoryORM.is_active,
        ProductCategoryORM.sort_order,
        ProductCategoryORM.created_at,
        ProductCategoryORM.updated_at,
    ]
    column_default_sort = [(ProductCategoryORM.sort_order, False)]
    column_labels = {
        ProductCategoryORM.id: "ID",
        ProductCategoryORM.translations: "Название",
        ProductCategoryORM.is_active: "Активна",
        ProductCategoryORM.sort_order: "Порядок",
        ProductCategoryORM.created_at: "Создана",
        ProductCategoryORM.updated_at: "Обновлена",
    }
    column_formatters = {
        ProductCategoryORM.translations: fmt_product_name,
        ProductCategoryORM.is_active: fmt_bool,
        ProductCategoryORM.updated_at: fmt_datetime,
    }
    column_formatters_detail = {
        ProductCategoryORM.translations: fmt_translations,
        ProductCategoryORM.is_active: fmt_bool,
        ProductCategoryORM.created_at: fmt_datetime,
        ProductCategoryORM.updated_at: fmt_datetime,
    }
    can_create = False
    can_delete = False
    form_columns = [ProductCategoryORM.is_active, ProductCategoryORM.sort_order]


class ProductTranslationAdmin(LocalizedLabelsMixin, ModelView, model=ProductTranslationORM):
    """Исправление названий и описаний продукта. Язык и продукт не меняются,
    строки не создаются и не удаляются: у продукта всегда ровно ru, uz, en."""

    name = _l("Перевод продукта")
    name_plural = _l("Переводы продуктов")
    icon = "fa-solid fa-language"
    category = CATEGORY_PRODUCTS

    column_list = [
        ProductTranslationORM.id,
        ProductTranslationORM.product,
        ProductTranslationORM.language,
        ProductTranslationORM.name,
    ]
    column_searchable_list = [ProductTranslationORM.name]
    column_default_sort = [(ProductTranslationORM.product_id, True)]
    column_labels = {
        ProductTranslationORM.id: "ID",
        ProductTranslationORM.product: "Продукт",
        ProductTranslationORM.product_id: "Продукт",
        ProductTranslationORM.language: "Язык",
        ProductTranslationORM.name: "Название",
        ProductTranslationORM.description: "Описание",
    }
    column_formatters = {
        ProductTranslationORM.product: fmt_translation_product,
        ProductTranslationORM.language: fmt_language,
    }
    column_formatters_detail = column_formatters
    can_create = False
    can_delete = False
    form_columns = [ProductTranslationORM.name, ProductTranslationORM.description]

    async def on_model_change(self, data: dict, model, is_created: bool, request: Request) -> None:
        name = (data.get("name") or "").strip()
        if len(name) < 2:
            raise ValueError(_("Название — не короче 2 символов"))
        data["name"] = name
        description = (data.get("description") or "").strip() or None
        if (description is None) != (model.description is None):
            raise ValueError(
                _("Описание задаётся на всех трёх языках или ни на одном — меняйте его через API")
            )
        data["description"] = description


# ---------- Файлы фотографий (только для авторизованных в админке) ----------


class ApplicationPhotoFileView(BaseView):
    """Отдаёт файл фотографии заявки под cookie-сессией админки.
    В меню не показывается; используется превью в списках и карточке заявки."""

    name = _l("Файл фотографии")

    def is_visible(self, request: Request) -> bool:
        return False

    @expose("/application-photo/{pk}", methods=["GET"], include_in_schema=False)
    async def photo_file(self, request: Request):
        try:
            pk = int(request.path_params["pk"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=404) from None

        async with async_session_maker() as session:
            photo = await session.get(ApplicationPhotoORM, pk)

        if photo is None:
            raise HTTPException(status_code=404)

        path = PhotoStorage().absolute_path(photo.storage_path)
        if not path.is_file():
            raise HTTPException(status_code=404)

        return FileResponse(
            path,
            media_type=photo.content_type,
            filename=photo.file_name,
            content_disposition_type="inline",
        )


class ApplicationDocumentFileView(BaseView):
    """Отдаёт документ заявки (PDF/DOCX) под cookie-сессией админки."""

    name = _l("Файл документа")

    def is_visible(self, request: Request) -> bool:
        return False

    @expose("/application-document/{pk}", methods=["GET"], include_in_schema=False)
    async def document_file(self, request: Request):
        try:
            pk = int(request.path_params["pk"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=404) from None

        async with async_session_maker() as session:
            document = await session.get(ApplicationDocumentORM, pk)

        if document is None:
            raise HTTPException(status_code=404)

        path = DocumentStorage().absolute_path(document.storage_path)
        if not path.is_file():
            raise HTTPException(status_code=404)

        return FileResponse(
            path,
            media_type=document.content_type,
            filename=document.file_name,
            content_disposition_type="attachment",
        )


class ApplicationFieldFileView(BaseView):
    """Отдаёт файл поля анкеты продукта (PHOTO / FILE) под cookie-сессией админки."""

    name = _l("Файл анкеты")

    def is_visible(self, request: Request) -> bool:
        return False

    @expose("/application-field-file/{pk}", methods=["GET"], include_in_schema=False)
    async def field_file(self, request: Request):
        try:
            pk = int(request.path_params["pk"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=404) from None

        async with async_session_maker() as session:
            file = await session.get(ApplicationFieldFileORM, pk)

        if file is None:
            raise HTTPException(status_code=404)

        path = FieldPhotoStorage().absolute_path(file.storage_path)
        if not path.is_file():
            raise HTTPException(status_code=404)

        inline = file.content_type.startswith("image/")
        return FileResponse(
            path,
            media_type=file.content_type,
            filename=file.file_name,
            content_disposition_type="inline" if inline else "attachment",
        )


ALL_VIEWS = [
    UserAdmin,
    RoleAdmin,
    PermissionAdmin,
    RefreshTokenAdmin,
    BankAdmin,
    ProductCategoryAdmin,
    ProductAdmin,
    ProductTranslationAdmin,
    ApplicationAdmin,
    StatusHistoryAdmin,
    ScoringAttemptAdmin,
    CouncilAssignmentAdmin,
    FounderAdmin,
    PhotoAdmin,
    DocumentAdmin,
    DemandDocumentAdmin,
    ResourceAllocationAdmin,
    ApplicationPhotoFileView,
    ApplicationDocumentFileView,
    ApplicationFieldFileView,
]
