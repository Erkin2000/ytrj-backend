"""Кабинет заявителя: свои заявки."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from src.application.schemas.application_schema import (
    ApplicationBankDTO,
    ApplicationCreateDTO,
    ApplicationFilterDTO,
    ApplicationUpdateDTO,
    StageValuesDTO,
)
from src.application.services.application_service import ApplicationService
from src.common.dependencies import CurrentUserDep, DBDep, PaginationDep, require_permission
from src.common.responses.exceptions import (
    ApplicantProfileIncompleteException,
    ApplicationAccessDeniedException,
    ApplicationNotEditableException,
    ApplicationNotFoundException,
    ApplicationValidationException,
    BankNotFoundException,
    BankNotInProductException,
    BankSubjectTypeMismatchException,
    DocumentTooLargeException,
    FieldFileLimitExceededException,
    FieldFileNotFoundException,
    FieldValueInvalidException,
    FileFieldException,
    InvalidDocumentException,
    InvalidPhotoException,
    PhotoTooLargeException,
    ProductFieldNotFoundException,
    ProductNotAvailableException,
    ProductStageNotFoundException,
    ProductWithoutBankException,
)
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import (
    COMMON_ERRORS,
    READ_ERRORS,
    error_examples,
    paginated_example,
    success_example,
)
from src.product.apis.examples import FIELD_EXAMPLES, PRODUCT_BRIEF_EXAMPLE, STAGE_EXAMPLE
from src.rbac.permissions import Action, Module

router = APIRouter(prefix="/applications", tags=["Заявки: кабинет заявителя"])

FilterDep = Annotated[ApplicationFilterDTO, Depends()]

BANK_EXAMPLE = {
    "id": 1,
    "code": "microcreditbank",
    "name": "Microcreditbank",
    "official_name": "АКБ «Микрокредитбанк»",
    "allowed_subject_types": ["YATT", "MCHJ", "SELF_EMPLOYED"],
    "is_active": True,
    "sort_order": 1,
}

APPLICANT_EXAMPLE = {
    "full_name": "Алиев Али Алиевич",
    "phone": "+998901234567",
    "passport_number": "AA1234567",
    "pinfl": "30101900000011",
    "inn": "123456789",
    "email": "aliev@example.com",
    "gender": "MALE",
    "date_of_birth": "1998-05-20",
}

FILE_EXAMPLE = {
    "id": 21,
    "file_name": "shop.jpg",
    "content_type": "image/jpeg",
    "size": 120000,
    "url": "/api/v1/applications/12/fields/12/files/21",
    "created_at": "2026-11-06T10:00:00Z",
}

FORM_STAGE_EXAMPLE = {
    "id": 5,
    "number": 1,
    "translations": STAGE_EXAMPLE["translations"],
    "is_complete": True,
    "fields": [
        {**FIELD_EXAMPLES[0], "value": "150000000", "files": []},
        {**FIELD_EXAMPLES[1], "value": None, "files": [FILE_EXAMPLE]},
    ],
}

# Элемент списка «Мои заявки».
APPLICATION_EXAMPLE = {
    "id": 12,
    "number": "JG-2026-000012",
    "status": "DRAFT",
    "product": PRODUCT_BRIEF_EXAMPLE,
    "subject_type": "YATT",
    "bank": BANK_EXAMPLE,
    "applicant_full_name": "Алиев Али Алиевич",
    "form_progress": {"stages_total": 2, "stages_complete": 1, "is_complete": False},
    "scoring_retry_required": False,
    "submitted_at": None,
    "created_at": "2026-11-06T10:00:00Z",
    "updated_at": "2026-11-06T10:05:00Z",
}

# Полная карточка заявки (ответ создания, PATCH, GET /{id}, submit).
APPLICATION_DETAIL_EXAMPLE = {
    **APPLICATION_EXAMPLE,
    "applicant_id": 7,
    "applicant": APPLICANT_EXAMPLE,
    "form": [FORM_STAGE_EXAMPLE],
    "bank_stage": {
        "sent_to_bank_at": None,
        "accepted_by": None,
        "accepted_at": None,
        "decision": None,
        "decision_reason": None,
        "decided_by": None,
        "decided_at": None,
    },
    "fund_decided_at": None,
    "fund_reject_reason": None,
    "council_assignments": [],
    "council_decided_at": None,
    "council_reject_reason": None,
    "demand_document": None,
    "resource_allocation": None,
    "completed_at": None,
    "rejection_reason": None,
}

SUBMITTED_EXAMPLE = {
    **APPLICATION_DETAIL_EXAMPLE,
    "status": "FUND_REVIEW",
    "submitted_at": "2026-11-06T11:00:00Z",
}


# Ошибки доступа к заявке по id — одинаковы для всех ручек с {application_id}.
BY_ID_ERRORS = {
    403: error_examples(ApplicationAccessDeniedException),
    404: error_examples(ApplicationNotFoundException),
}


def draft_errors(*extra):
    """400-ошибки ручек, меняющих черновик: «не черновик» плюс специфичные для ручки."""
    return {400: error_examples(ApplicationNotEditableException, *extra), **BY_ID_ERRORS}


read_dep = Depends(require_permission(Module.APPLICATIONS, Action.READ))
create_dep = Depends(require_permission(Module.APPLICATIONS, Action.CREATE))
update_dep = Depends(require_permission(Module.APPLICATIONS, Action.UPDATE))
delete_dep = Depends(require_permission(Module.APPLICATIONS, Action.DELETE))


@router.get(
    "",
    summary="Мои заявки: номер, продукт, банк, статус",
    dependencies=[read_dep],
    responses={
        200: paginated_example(APPLICATION_EXAMPLE, "Applications retrieved successfully."),
        **READ_ERRORS,
    },
)
async def get_my_applications(
    db: DBDep, user: CurrentUserDep, pagination: PaginationDep, filters: FilterDep
):
    data = await ApplicationService(db).get_my_applications(
        user, filters, pagination.page, pagination.per_page
    )
    return ResponseBuilder.success(data=data, message="Applications retrieved successfully.")


@router.post(
    "",
    summary="Подать заявку по продукту: создаётся номер и черновик (DRAFT)",
    description=(
        "Продукт берётся из `GET /products`: опубликован, в сроках приёма и рассчитан на "
        "`subject_type`. Данные заявителя — из профиля (`/auth/me`). Банк — из `banks` продукта, "
        "сразу (`bank_id`) или позже (`PUT /applications/{id}/bank`). Дальше заявитель "
        "заполняет этапы продукта (`PUT /applications/{id}/stages/{stage_id}`)."
    ),
    dependencies=[create_dep],
    responses={
        201: success_example(APPLICATION_DETAIL_EXAMPLE, "Application created."),
        **COMMON_ERRORS,
        400: error_examples(
            ApplicantProfileIncompleteException,
            ProductNotAvailableException,
            BankNotInProductException,
            ProductWithoutBankException,
            BankSubjectTypeMismatchException,
        ),
        404: error_examples(BankNotFoundException),
    },
)
async def create_application(data: ApplicationCreateDTO, db: DBDep, user: CurrentUserDep):
    application = await ApplicationService(db).create(user, data)
    return ResponseBuilder.success(
        data=application, message="Application created.", status_code=201
    )


@router.get(
    "/{application_id}",
    summary="Карточка заявки: заявитель, продукт, ответы анкеты, этапы рассмотрения",
    dependencies=[read_dep],
    responses={
        200: success_example(APPLICATION_DETAIL_EXAMPLE, "Application found."),
        **READ_ERRORS,
        **BY_ID_ERRORS,
    },
)
async def get_application(application_id: int, db: DBDep, user: CurrentUserDep):
    application = await ApplicationService(db).get_detail(application_id, user)
    return ResponseBuilder.success(data=application, message="Application found.")


@router.patch(
    "/{application_id}",
    summary="Редактирование черновика: продукт или тип субъекта",
    description=(
        "Смена продукта очищает ответы анкеты, файлы и выбранный банк. Если выбранный банк "
        "не работает с новым типом субъекта, он сбрасывается."
    ),
    dependencies=[update_dep],
    responses={
        200: success_example(APPLICATION_DETAIL_EXAMPLE, "Application updated."),
        **COMMON_ERRORS,
        **draft_errors(ProductNotAvailableException),
    },
)
async def update_application(
    application_id: int, data: ApplicationUpdateDTO, db: DBDep, user: CurrentUserDep
):
    application = await ApplicationService(db).update(application_id, user, data)
    return ResponseBuilder.success(data=application, message="Application updated.")


@router.delete(
    "/{application_id}",
    summary="Удаление черновика (вместе с файлами анкеты)",
    dependencies=[delete_dep],
    responses={
        200: success_example(None, "Draft deleted."),
        **COMMON_ERRORS,
        **draft_errors(),
    },
)
async def delete_draft(application_id: int, db: DBDep, user: CurrentUserDep):
    await ApplicationService(db).delete_draft(application_id, user)
    return ResponseBuilder.success(message="Draft deleted.")


@router.put(
    "/{application_id}/bank",
    summary="Выбор банка из банков продукта",
    description=(
        "Банк берётся из `banks` продукта (`GET /products/{id}`): он должен быть активен и "
        "работать с типом субъекта заявки. После утверждения Советом заявка автоматически "
        "уходит в этот банк."
    ),
    dependencies=[update_dep],
    responses={
        200: success_example(BANK_EXAMPLE, "Bank selected."),
        **COMMON_ERRORS,
        400: error_examples(
            ApplicationNotEditableException,
            ProductNotAvailableException,
            BankNotInProductException,
            ProductWithoutBankException,
            BankSubjectTypeMismatchException,
        ),
        403: BY_ID_ERRORS[403],
        404: error_examples(ApplicationNotFoundException, BankNotFoundException),
    },
)
async def set_bank(application_id: int, data: ApplicationBankDTO, db: DBDep, user: CurrentUserDep):
    bank = await ApplicationService(db).set_bank(application_id, user, data)
    return ResponseBuilder.success(data=bank, message="Bank selected.")


@router.put(
    "/{application_id}/stages/{stage_id}",
    summary="Сохранить ответы этапа продукта",
    description=(
        "`values` — словарь «id поля → значение». Меняются только переданные поля; `null` или "
        "пустая строка очищает поле. Проверка по типу: NUMBER — число, DATE — ГГГГ-ММ-ДД, "
        "PHONE — +998XXXXXXXXX, EMAIL — адрес почты. Обязательность проверяется при отправке "
        "заявки. Файлы полей PHOTO / FILE загружаются через `POST .../fields/{field_id}/files`."
    ),
    dependencies=[update_dep],
    responses={
        200: success_example(FORM_STAGE_EXAMPLE, "Stage saved."),
        **COMMON_ERRORS,
        **draft_errors(FieldValueInvalidException),
        404: error_examples(ApplicationNotFoundException, ProductStageNotFoundException),
    },
)
async def save_stage(
    application_id: int, stage_id: int, data: StageValuesDTO, db: DBDep, user: CurrentUserDep
):
    stage = await ApplicationService(db).save_stage(application_id, user, stage_id, data)
    return ResponseBuilder.success(data=stage, message="Stage saved.")


@router.post(
    "/{application_id}/fields/{field_id}/files",
    summary="Загрузить файл в поле PHOTO или FILE",
    description=(
        "PHOTO — JPG/PNG/WEBP до 5 МБ, FILE — PDF/DOCX до 10 МБ. "
        "Не больше `max_files` файлов на поле."
    ),
    dependencies=[update_dep],
    responses={
        201: success_example(FILE_EXAMPLE, "File uploaded."),
        **COMMON_ERRORS,
        **draft_errors(
            FileFieldException,
            FieldFileLimitExceededException,
            InvalidPhotoException,
            PhotoTooLargeException,
            InvalidDocumentException,
            DocumentTooLargeException,
        ),
        404: error_examples(ApplicationNotFoundException, ProductFieldNotFoundException),
    },
)
async def upload_field_file(
    application_id: int,
    field_id: int,
    db: DBDep,
    user: CurrentUserDep,
    file: UploadFile = File(...),
):
    data = await ApplicationService(db).add_field_file(application_id, user, field_id, file)
    return ResponseBuilder.success(data=data, message="File uploaded.", status_code=201)


@router.delete(
    "/{application_id}/fields/{field_id}/files/{file_id}",
    summary="Удалить файл поля из черновика",
    dependencies=[update_dep],
    responses={
        200: success_example(None, "File deleted."),
        **COMMON_ERRORS,
        **draft_errors(),
        404: error_examples(ApplicationNotFoundException, FieldFileNotFoundException),
    },
)
async def delete_field_file(
    application_id: int, field_id: int, file_id: int, db: DBDep, user: CurrentUserDep
):
    await ApplicationService(db).delete_field_file(application_id, user, field_id, file_id)
    return ResponseBuilder.success(message="File deleted.")


@router.get(
    "/{application_id}/fields/{field_id}/files/{file_id}",
    summary="Скачать файл поля (только для тех, кто имеет доступ к заявке)",
    dependencies=[read_dep],
    response_class=FileResponse,
    responses={
        **READ_ERRORS,
        403: BY_ID_ERRORS[403],
        404: error_examples(ApplicationNotFoundException, FieldFileNotFoundException),
    },
)
async def get_field_file(
    application_id: int, field_id: int, file_id: int, db: DBDep, user: CurrentUserDep
):
    path, content_type, file_name = await ApplicationService(db).get_field_file_path(
        application_id, user, field_id, file_id
    )
    return FileResponse(path, media_type=content_type, filename=file_name)


@router.get(
    "/{application_id}/submission-check",
    summary="Сводка перед отправкой: выбранные параметры и недостающие поля",
    dependencies=[read_dep],
    responses={
        200: success_example(
            {
                "is_ready": False,
                "missing": ["bank_id", "fields.12"],
                "product": PRODUCT_BRIEF_EXAMPLE,
                "product_available": True,
                "subject_type": "YATT",
                "bank": None,
                "stages": [
                    {
                        **FORM_STAGE_EXAMPLE,
                        "is_complete": False,
                        "fields": [
                            FORM_STAGE_EXAMPLE["fields"][0],
                            {**FORM_STAGE_EXAMPLE["fields"][1], "files": []},
                        ],
                    }
                ],
            },
            "Submission check completed.",
        ),
        **READ_ERRORS,
        **BY_ID_ERRORS,
    },
)
async def submission_check(application_id: int, db: DBDep, user: CurrentUserDep):
    data = await ApplicationService(db).check_submission(application_id, user)
    return ResponseBuilder.success(data=data, message="Submission check completed.")


@router.post(
    "/{application_id}/submit",
    summary="Отправить заявку: проверка обязательных полей → SUBMITTED → скоринг",
    description=(
        "Недостающие поля — те же ключи, что в `submission-check`: `product_id`, `subject_type`, "
        "`bank_id`, `fields.<id поля>` (обязательные поля этапов), `applicant.phone` … "
        "После отправки запускается скоринг; при успехе заявка поступает в Фонд (`FUND_REVIEW`), "
        "при техошибке KATM остаётся в `SCORING_IN_PROGRESS` до повтора."
    ),
    dependencies=[update_dep],
    responses={
        200: success_example(SUBMITTED_EXAMPLE, "Application submitted."),
        **COMMON_ERRORS,
        **draft_errors(ApplicationValidationException),
    },
)
async def submit_application(application_id: int, db: DBDep, user: CurrentUserDep):
    application = await ApplicationService(db).submit(application_id, user)
    return ResponseBuilder.success(data=application, message="Application submitted.")


@router.get(
    "/{application_id}/progress",
    summary="Индикатор прогресса: этапы done / active / pending / rejected",
    dependencies=[read_dep],
    responses={
        200: success_example(
            {
                "application_id": 12,
                "number": "JG-2026-000012",
                "status": "BANK_REVIEW",
                "is_rejected": False,
                "rejection_message": None,
                "steps": [
                    {
                        "key": "submitted",
                        "title": "Заявка подана",
                        "state": "done",
                        "description": "Заявка принята и зарегистрирована.",
                        "action_required": None,
                    },
                    {
                        "key": "bank_review",
                        "title": "Банк рассматривает",
                        "state": "active",
                        "description": "Ответственный сотрудник банка проводит рассмотрение.",
                        "action_required": None,
                    },
                ],
            },
            "Progress retrieved.",
        ),
        **READ_ERRORS,
        **BY_ID_ERRORS,
    },
)
async def get_progress(application_id: int, db: DBDep, user: CurrentUserDep):
    data = await ApplicationService(db).get_progress(application_id, user)
    return ResponseBuilder.success(data=data, message="Progress retrieved.")


@router.get(
    "/{application_id}/history",
    summary="Хронологическая история заявки",
    dependencies=[read_dep],
    responses={
        200: success_example(
            [
                {
                    "id": 1,
                    "from_status": None,
                    "to_status": "DRAFT",
                    "event": "created",
                    "comment": "Заявка создана",
                    "actor": {
                        "id": 7,
                        "full_name": "Алиев Али Алиевич",
                        "username": "30101900000011",
                    },
                    "actor_role": "APPLICANT",
                    "created_at": "2026-10-24T10:00:00Z",
                }
            ],
            "History retrieved.",
        ),
        **READ_ERRORS,
        **BY_ID_ERRORS,
    },
)
async def get_history(application_id: int, db: DBDep, user: CurrentUserDep):
    data = await ApplicationService(db).get_history(application_id, user)
    return ResponseBuilder.success(data=data, message="History retrieved.")
