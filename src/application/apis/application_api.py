"""Кабинет заявителя: свои заявки."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from src.application.schemas.application_schema import (
    ApplicationCreateDTO,
    ApplicationFilterDTO,
    ApplicationUpdateDTO,
    LocationDTO,
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
    summary="Редактирование черновика: тип субъекта, юр. наименование, банк",
    description="При смене типа субъекта банк, не подходящий новому типу, сбрасывается.",
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
    "/{application_id}/location",
    summary="Место осуществления деятельности (не текущее местоположение!)",
    description="Отправка заявки невозможна без confirmed=true.",
    dependencies=[update_dep],
    responses={
        200: success_example(
            {"lat": 41.311081, "lng": 69.240562, "address": "Ташкент", "confirmed": True},
            "Location saved.",
        ),
        **COMMON_ERRORS,
    },
)
async def set_location(application_id: int, data: LocationDTO, db: DBDep, user: CurrentUserDep):
    location = await ApplicationService(db).set_location(application_id, user, data)
    return ResponseBuilder.success(data=location, message="Location saved.")


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
