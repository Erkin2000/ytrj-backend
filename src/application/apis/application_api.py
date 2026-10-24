"""Кабинет заявителя: свои заявки."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from src.application.schemas.application_schema import (
    ApplicationBankDTO,
    ApplicationCreateDTO,
    ApplicationFilterDTO,
    ApplicationUpdateDTO,
    FounderCreateDTO,
    FounderUpdateDTO,
    LocationDTO,
    ProjectDTO,
)
from src.application.services.application_service import ApplicationService
from src.common.dependencies import CurrentUserDep, DBDep, PaginationDep, require_permission
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import COMMON_ERRORS, paginated_example, success_example
from src.rbac.permissions import Action, Module

router = APIRouter(prefix="/applications", tags=["Заявки: кабинет заявителя"])

FilterDep = Annotated[ApplicationFilterDTO, Depends()]

APPLICATION_EXAMPLE = {
    "id": 12,
    "number": "JG-2026-000012",
    "status": "DRAFT",
    "subject_type": "YATT",
    "legal_name": "ИП Алиев",
    "bank": {"id": 1, "code": "microcreditbank", "name": "Microcreditbank"},
    "applicant_full_name": "Алиев Али Алиевич",
    "submitted_at": None,
    "created_at": "2026-10-19T10:00:00Z",
}

FOUNDER_EXAMPLE = {
    "id": 3,
    "full_name": "Усманов Жасур Абдуллаевич",
    "passport_number": "AC1122334",
    "date_of_birth": "1990-07-14",
    "created_at": "2026-10-24T10:00:00Z",
}

read_dep = Depends(require_permission(Module.APPLICATIONS, Action.READ))
create_dep = Depends(require_permission(Module.APPLICATIONS, Action.CREATE))
update_dep = Depends(require_permission(Module.APPLICATIONS, Action.UPDATE))
delete_dep = Depends(require_permission(Module.APPLICATIONS, Action.DELETE))


@router.get(
    "",
    summary="Мои заявки: номер, дата, банк, статус",
    dependencies=[read_dep],
    responses={200: paginated_example(APPLICATION_EXAMPLE), **COMMON_ERRORS},
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
    summary="Подать заявку: создаётся номер и черновик (DRAFT)",
    description=(
        "Данные заявителя берутся из профиля (`/auth/me`). Банк выбирается отдельным шагом "
        "(`PUT /applications/{id}/bank`). Для ООО в `company` передаются СТИР предприятия и данные "
        "руководителя (он может не совпадать с заявителем) и список учредителей `founders`. "
        "Для ИП и самозанятого `company` и `founders` не используются."
    ),
    dependencies=[create_dep],
    responses={201: success_example(APPLICATION_EXAMPLE, "Application created."), **COMMON_ERRORS},
)
async def create_application(data: ApplicationCreateDTO, db: DBDep, user: CurrentUserDep):
    application = await ApplicationService(db).create(user, data)
    return ResponseBuilder.success(
        data=application, message="Application created.", status_code=201
    )


@router.get(
    "/{application_id}",
    summary="Карточка заявки: данные, место деятельности, фото, этапы",
    dependencies=[read_dep],
    responses={200: success_example(APPLICATION_EXAMPLE, "Application found."), **COMMON_ERRORS},
)
async def get_application(application_id: int, db: DBDep, user: CurrentUserDep):
    application = await ApplicationService(db).get_detail(application_id, user)
    return ResponseBuilder.success(data=application, message="Application found.")


@router.patch(
    "/{application_id}",
    summary="Редактирование черновика: тип субъекта, юр. наименование, предприятие",
    description=(
        "При смене типа субъекта с ООО на ИП или самозанятого очищаются реквизиты "
        "предприятия и список учредителей."
    ),
    dependencies=[update_dep],
    responses={200: success_example(APPLICATION_EXAMPLE, "Application updated."), **COMMON_ERRORS},
)
async def update_application(
    application_id: int, data: ApplicationUpdateDTO, db: DBDep, user: CurrentUserDep
):
    application = await ApplicationService(db).update(application_id, user, data)
    return ResponseBuilder.success(data=application, message="Application updated.")


@router.delete(
    "/{application_id}",
    summary="Удаление черновика",
    dependencies=[delete_dep],
    responses={200: success_example(None, "Draft deleted."), **COMMON_ERRORS},
)
async def delete_draft(application_id: int, db: DBDep, user: CurrentUserDep):
    await ApplicationService(db).delete_draft(application_id, user)
    return ResponseBuilder.success(message="Draft deleted.")


@router.put(
    "/{application_id}/bank",
    summary="Выбор банка для заявки",
    description=(
        "Банк берётся из каталога `GET /banks?subject_type=...`: он должен быть активен и "
        "работать с типом субъекта заявки. После успешного скоринга заявка автоматически "
        "направляется в выбранный банк. При смене типа субъекта неподходящий банк сбрасывается."
    ),
    dependencies=[update_dep],
    responses={
        200: success_example(
            {"id": 1, "code": "microcreditbank", "name": "Microcreditbank"}, "Bank selected."
        ),
        **COMMON_ERRORS,
    },
)
async def set_bank(application_id: int, data: ApplicationBankDTO, db: DBDep, user: CurrentUserDep):
    bank = await ApplicationService(db).set_bank(application_id, user, data)
    return ResponseBuilder.success(data=bank, message="Bank selected.")


@router.put(
    "/{application_id}/project",
    summary="Информация о проекте: сумма, срок кредита, стоимость, рабочие места, описание",
    description=(
        "Заполняется целиком. Срок кредита — в месяцах, в пределах LOAN_TERM_MIN_MONTHS…"
        "LOAN_TERM_MAX_MONTHS (по умолчанию 12–36). Запрашиваемая сумма не больше общей стоимости "
        "проекта. Без этого блока заявку отправить нельзя."
    ),
    dependencies=[update_dep],
    responses={
        200: success_example(
            {
                "requested_amount": 150000000,
                "loan_term_months": 24,
                "total_cost": 200000000,
                "jobs_count": 5,
                "description": "Открытие швейного цеха: закупка 10 машин и аренда помещения.",
            },
            "Project saved.",
        ),
        **COMMON_ERRORS,
    },
)
async def set_project(application_id: int, data: ProjectDTO, db: DBDep, user: CurrentUserDep):
    project = await ApplicationService(db).set_project(application_id, user, data)
    return ResponseBuilder.success(data=project, message="Project saved.")


@router.put(
    "/{application_id}/location",
    summary="Место осуществления деятельности (не текущее местоположение!)",
    description=(
        "Координаты плюс область, район и махалля; адрес — уточнение. "
        "Отправка заявки невозможна без confirmed=true."
    ),
    dependencies=[update_dep],
    responses={
        200: success_example(
            {
                "lat": 41.311081,
                "lng": 69.240562,
                "region": "Ташкент",
                "district": "Яккасарайский район",
                "makhalla": "Махалля Кушбеги",
                "address": "ул. Бабура, 12",
                "confirmed": True,
            },
            "Location saved.",
        ),
        **COMMON_ERRORS,
    },
)
async def set_location(application_id: int, data: LocationDTO, db: DBDep, user: CurrentUserDep):
    location = await ApplicationService(db).set_location(application_id, user, data)
    return ResponseBuilder.success(data=location, message="Location saved.")


@router.post(
    "/{application_id}/founders",
    summary="Добавить учредителя (только для ООО)",
    dependencies=[update_dep],
    responses={201: success_example(FOUNDER_EXAMPLE, "Founder added."), **COMMON_ERRORS},
)
async def add_founder(application_id: int, data: FounderCreateDTO, db: DBDep, user: CurrentUserDep):
    founder = await ApplicationService(db).add_founder(application_id, user, data)
    return ResponseBuilder.success(data=founder, message="Founder added.", status_code=201)


@router.patch(
    "/{application_id}/founders/{founder_id}",
    summary="Изменить данные учредителя",
    dependencies=[update_dep],
    responses={200: success_example(FOUNDER_EXAMPLE, "Founder updated."), **COMMON_ERRORS},
)
async def update_founder(
    application_id: int,
    founder_id: int,
    data: FounderUpdateDTO,
    db: DBDep,
    user: CurrentUserDep,
):
    founder = await ApplicationService(db).update_founder(application_id, user, founder_id, data)
    return ResponseBuilder.success(data=founder, message="Founder updated.")


@router.delete(
    "/{application_id}/founders/{founder_id}",
    summary="Удалить учредителя из черновика",
    dependencies=[update_dep],
    responses={200: success_example(None, "Founder deleted."), **COMMON_ERRORS},
)
async def delete_founder(application_id: int, founder_id: int, db: DBDep, user: CurrentUserDep):
    await ApplicationService(db).delete_founder(application_id, user, founder_id)
    return ResponseBuilder.success(message="Founder deleted.")


@router.post(
    "/{application_id}/photos",
    summary="Прикрепить фотографию (максимум 4; JPG/PNG/WEBP)",
    dependencies=[update_dep],
    responses={
        201: success_example(
            {
                "id": 1,
                "file_name": "shop.jpg",
                "content_type": "image/jpeg",
                "size": 120000,
                "url": "/api/v1/applications/12/photos/1/file",
            },
            "Photo uploaded.",
        ),
        **COMMON_ERRORS,
    },
)
async def upload_photo(
    application_id: int, db: DBDep, user: CurrentUserDep, file: UploadFile = File(...)
):
    photo = await ApplicationService(db).add_photo(application_id, user, file)
    return ResponseBuilder.success(data=photo, message="Photo uploaded.", status_code=201)


@router.delete(
    "/{application_id}/photos/{photo_id}",
    summary="Удалить фотографию черновика",
    dependencies=[update_dep],
    responses={200: success_example(None, "Photo deleted."), **COMMON_ERRORS},
)
async def delete_photo(application_id: int, photo_id: int, db: DBDep, user: CurrentUserDep):
    await ApplicationService(db).delete_photo(application_id, user, photo_id)
    return ResponseBuilder.success(message="Photo deleted.")


@router.get(
    "/{application_id}/photos/{photo_id}/file",
    summary="Файл фотографии (только для тех, кто имеет доступ к заявке)",
    dependencies=[read_dep],
    response_class=FileResponse,
    responses={**COMMON_ERRORS},
)
async def get_photo_file(application_id: int, photo_id: int, db: DBDep, user: CurrentUserDep):
    path, content_type, file_name = await ApplicationService(db).get_photo_path(
        application_id, user, photo_id
    )
    return FileResponse(path, media_type=content_type, filename=file_name)


@router.post(
    "/{application_id}/documents",
    summary="Прикрепить документ (максимум 4; PDF/DOCX до 10 МБ)",
    dependencies=[update_dep],
    responses={
        201: success_example(
            {
                "id": 1,
                "file_name": "business-plan.pdf",
                "content_type": "application/pdf",
                "size": 2400000,
                "url": "/api/v1/applications/12/documents/1/file",
            },
            "Document uploaded.",
        ),
        **COMMON_ERRORS,
    },
)
async def upload_document(
    application_id: int, db: DBDep, user: CurrentUserDep, file: UploadFile = File(...)
):
    document = await ApplicationService(db).add_document(application_id, user, file)
    return ResponseBuilder.success(data=document, message="Document uploaded.", status_code=201)


@router.delete(
    "/{application_id}/documents/{document_id}",
    summary="Удалить документ черновика",
    dependencies=[update_dep],
    responses={200: success_example(None, "Document deleted."), **COMMON_ERRORS},
)
async def delete_document(application_id: int, document_id: int, db: DBDep, user: CurrentUserDep):
    await ApplicationService(db).delete_document(application_id, user, document_id)
    return ResponseBuilder.success(message="Document deleted.")


@router.get(
    "/{application_id}/documents/{document_id}/file",
    summary="Файл документа (только для тех, кто имеет доступ к заявке)",
    dependencies=[read_dep],
    response_class=FileResponse,
    responses={**COMMON_ERRORS},
)
async def get_document_file(application_id: int, document_id: int, db: DBDep, user: CurrentUserDep):
    path, content_type, file_name = await ApplicationService(db).get_document_path(
        application_id, user, document_id
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
                "missing": ["location.confirmed"],
                "subject_type": "YATT",
                "legal_name": "ИП Алиев",
                "bank": {"id": 1, "name": "Microcreditbank"},
                "photos_count": 2,
                "max_photos": 4,
                "documents_count": 1,
                "max_documents": 4,
            },
            "Submission check completed.",
        ),
        **COMMON_ERRORS,
    },
)
async def submission_check(application_id: int, db: DBDep, user: CurrentUserDep):
    data = await ApplicationService(db).check_submission(application_id, user)
    return ResponseBuilder.success(data=data, message="Submission check completed.")


@router.post(
    "/{application_id}/submit",
    summary="Отправить заявку: проверка обязательных полей → SUBMITTED → скоринг",
    dependencies=[update_dep],
    responses={
        200: success_example(
            {**APPLICATION_EXAMPLE, "status": "SENT_TO_BANK"}, "Application submitted."
        ),
        **COMMON_ERRORS,
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
                        "description": "...",
                    }
                ],
            },
            "Progress retrieved.",
        ),
        **COMMON_ERRORS,
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
                    "actor_role": "APPLICANT",
                    "created_at": "2026-10-19T10:00:00Z",
                }
            ],
            "History retrieved.",
        ),
        **COMMON_ERRORS,
    },
)
async def get_history(application_id: int, db: DBDep, user: CurrentUserDep):
    data = await ApplicationService(db).get_history(application_id, user)
    return ResponseBuilder.success(data=data, message="History retrieved.")
