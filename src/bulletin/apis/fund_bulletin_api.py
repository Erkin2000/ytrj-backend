"""Бюллетени Совета — рабочее окно Фонда (и Super Admin)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, Response

from src.bulletin.apis.examples import CALENDAR, DETAIL, LIST_ITEM
from src.bulletin.schemas.bulletin_schema import (
    BulletinCancelDTO,
    BulletinCreateForm,
    BulletinFilterDTO,
    BulletinUpdateDTO,
)
from src.bulletin.services.bulletin_service import BulletinService
from src.common.dependencies import CurrentUserDep, DBDep, PaginationDep, require_permission
from src.common.responses.exceptions import (
    ApplicationNotFoundException,
    BulletinApplicationException,
    BulletinFileNotFoundException,
    BulletinNotEditableException,
    BulletinNotFoundException,
    BulletinScheduleException,
    BulletinStatusException,
    DocumentTooLargeException,
    InvalidDocumentException,
    NoCouncilMembersException,
)
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import (
    COMMON_ERRORS,
    error_examples,
    paginated_example,
    success_example,
)
from src.rbac.permissions import Action, Module

router = APIRouter(prefix="/fund/bulletins", tags=["Бюллетени: рабочее окно Фонда"])

FilterDep = Annotated[BulletinFilterDTO, Depends()]

read_dep = Depends(require_permission(Module.BULLETINS, Action.READ))
create_dep = Depends(require_permission(Module.BULLETINS, Action.CREATE))
update_dep = Depends(require_permission(Module.BULLETINS, Action.UPDATE))
delete_dep = Depends(require_permission(Module.BULLETINS, Action.DELETE))
approve_dep = Depends(require_permission(Module.BULLETINS, Action.APPROVE))

NOT_FOUND = {404: error_examples(BulletinNotFoundException)}

DATE_FROM = Query(None, description="Первый день (по Ташкенту); по умолчанию — начало месяца.")
DATE_TO = Query(None, description="Последний день включительно; по умолчанию — конец месяца.")


@router.get(
    "",
    summary="Бюллетени: поиск по статусу, заявке, номеру или названию",
    dependencies=[read_dep],
    responses={200: paginated_example(LIST_ITEM), **COMMON_ERRORS},
)
async def get_bulletins(
    db: DBDep, user: CurrentUserDep, pagination: PaginationDep, filters: FilterDep
):
    data = await BulletinService(db).get_list(user, filters, pagination.page, pagination.per_page)
    return ResponseBuilder.success(data=data, message="Bulletins retrieved.")


@router.get(
    "/counters",
    summary="Счётчики бюллетеней по статусам и просроченные",
    dependencies=[read_dep],
    responses={
        200: success_example(
            {
                "pending": 1,
                "published": 2,
                "partially_signed": 3,
                "completed": 10,
                "cancelled": 1,
                "overdue": 1,
            },
            "Counters retrieved.",
        ),
        **COMMON_ERRORS,
    },
)
async def get_counters(db: DBDep, user: CurrentUserDep):
    data = await BulletinService(db).get_counters(user)
    return ResponseBuilder.success(data=data, message="Counters retrieved.")


@router.get(
    "/calendar",
    summary="Календарь Фонда: даты отправки (и плановые) и сроки подписания",
    description="Дни без событий не возвращаются. Диапазон — не больше 93 дней.",
    dependencies=[read_dep],
    responses={200: success_example(CALENDAR, "Calendar retrieved."), **COMMON_ERRORS},
)
async def get_calendar(
    db: DBDep,
    user: CurrentUserDep,
    date_from: date | None = DATE_FROM,
    date_to: date | None = DATE_TO,
):
    data = await BulletinService(db).get_calendar(user, date_from, date_to)
    return ResponseBuilder.success(data=data, message="Calendar retrieved.")


@router.post(
    "",
    status_code=201,
    summary="Создать бюллетень (multipart/form-data): сразу отправить или отложить",
    description=(
        "`status=PUBLISHED` — бюллетень сразу уходит всем активным членам Совета; "
        "`status=PENDING` — уйдёт автоматически в `send_at`. Файл `file` — PDF или DOCX "
        "до 10 МБ, необязателен. Если указан `application_id`, заявка должна быть на "
        "рассмотрении Фонда: она переходит в COUNCIL_REVIEW, а подписи членов Совета "
        "решают её («Против» любого — отказ, «Согласен» всех — отправка в банк). "
        "QR-код страницы проверки доступен сразу: `qr_url`, `verify_url`."
    ),
    dependencies=[create_dep],
    responses={
        201: success_example({**DETAIL, "status": "PUBLISHED"}, "Bulletin created."),
        **COMMON_ERRORS,
        400: error_examples(
            BulletinScheduleException,
            BulletinApplicationException,
            NoCouncilMembersException,
            InvalidDocumentException,
            DocumentTooLargeException,
        ),
        404: error_examples(ApplicationNotFoundException),
    },
)
async def create_bulletin(
    db: DBDep,
    user: CurrentUserDep,
    form: Annotated[BulletinCreateForm, Form(media_type="multipart/form-data")],
):
    data = await BulletinService(db).create(user, form, form.file)
    return ResponseBuilder.success(data=data, message="Bulletin created.", status_code=201)


@router.get(
    "/{bulletin_id}",
    summary="Бюллетень: кто подписал, а кто нет, решения и сертификаты ЭЦП",
    dependencies=[read_dep],
    responses={200: success_example(DETAIL, "Bulletin retrieved."), **COMMON_ERRORS, **NOT_FOUND},
)
async def get_bulletin(bulletin_id: int, db: DBDep, user: CurrentUserDep):
    data = await BulletinService(db).get_detail(bulletin_id, user)
    return ResponseBuilder.success(data=data, message="Bulletin retrieved.")


@router.patch(
    "/{bulletin_id}",
    summary="Изменить бюллетень: до отправки — всё, после — только срок подписания",
    dependencies=[update_dep],
    responses={
        200: success_example(DETAIL, "Bulletin updated."),
        **COMMON_ERRORS,
        400: error_examples(BulletinNotEditableException, BulletinScheduleException),
        **NOT_FOUND,
    },
)
async def update_bulletin(
    bulletin_id: int, data: BulletinUpdateDTO, db: DBDep, user: CurrentUserDep
):
    result = await BulletinService(db).update(bulletin_id, user, data)
    return ResponseBuilder.success(data=result, message="Bulletin updated.")


@router.put(
    "/{bulletin_id}/file",
    summary="Прикрепить или заменить файл (PDF / DOCX) — только до отправки",
    dependencies=[update_dep],
    responses={
        200: success_example(DETAIL, "Bulletin file uploaded."),
        **COMMON_ERRORS,
        400: error_examples(
            BulletinNotEditableException, InvalidDocumentException, DocumentTooLargeException
        ),
        **NOT_FOUND,
    },
)
async def upload_file(
    bulletin_id: int,
    db: DBDep,
    user: CurrentUserDep,
    file: UploadFile = File(..., description="PDF или DOCX, до 10 МБ."),
):
    data = await BulletinService(db).set_file(bulletin_id, user, file)
    return ResponseBuilder.success(data=data, message="Bulletin file uploaded.")


@router.delete(
    "/{bulletin_id}/file",
    summary="Убрать файл — только до отправки",
    dependencies=[update_dep],
    responses={
        200: success_example({**DETAIL, "file": None, "has_file": False}, "Bulletin file deleted."),
        **COMMON_ERRORS,
        400: error_examples(BulletinNotEditableException),
        404: error_examples(BulletinNotFoundException, BulletinFileNotFoundException),
    },
)
async def delete_file(bulletin_id: int, db: DBDep, user: CurrentUserDep):
    data = await BulletinService(db).delete_file(bulletin_id, user)
    return ResponseBuilder.success(data=data, message="Bulletin file deleted.")


@router.get(
    "/{bulletin_id}/file",
    summary="Скачать файл бюллетеня",
    dependencies=[read_dep],
    response_class=FileResponse,
    responses={
        **COMMON_ERRORS,
        404: error_examples(BulletinNotFoundException, BulletinFileNotFoundException),
    },
)
async def get_file(bulletin_id: int, db: DBDep, user: CurrentUserDep):
    path, content_type, file_name = await BulletinService(db).get_file_path(bulletin_id, user)
    return FileResponse(path, media_type=content_type, filename=file_name)


@router.get(
    "/{bulletin_id}/qr",
    summary="QR-код страницы проверки бюллетеня (SVG)",
    description="QR ведёт на `verify_url`: название, описание, данные файла, кто подписал и статус.",
    dependencies=[read_dep],
    response_class=Response,
    responses={
        200: {"content": {"image/svg+xml": {}}, "description": "SVG"},
        **COMMON_ERRORS,
        **NOT_FOUND,
    },
)
async def get_qr(bulletin_id: int, db: DBDep, user: CurrentUserDep):
    svg = await BulletinService(db).get_qr(bulletin_id, user)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Content-Disposition": f'inline; filename="bulletin-{bulletin_id}-qr.svg"'},
    )


@router.post(
    "/{bulletin_id}/publish",
    summary="Отправить отложенный бюллетень сейчас (PENDING → PUBLISHED)",
    description="Получатели — все активные члены Совета с правом решения и ПИНФЛ.",
    dependencies=[approve_dep],
    responses={
        200: success_example({**DETAIL, "status": "PUBLISHED"}, "Bulletin sent."),
        **COMMON_ERRORS,
        400: error_examples(
            BulletinStatusException, BulletinScheduleException, NoCouncilMembersException
        ),
        **NOT_FOUND,
    },
)
async def publish_bulletin(bulletin_id: int, db: DBDep, user: CurrentUserDep):
    data = await BulletinService(db).publish(bulletin_id, user)
    return ResponseBuilder.success(data=data, message="Bulletin sent.")


@router.post(
    "/{bulletin_id}/cancel",
    summary="Аннулировать бюллетень",
    description=(
        "Подписи сохраняются, страница проверки по QR показывает «Аннулирован». "
        "Заявка, которую Совет ещё не решил, возвращается Фонду (COUNCIL_REVIEW → FUND_REVIEW)."
    ),
    dependencies=[approve_dep],
    responses={
        200: success_example({**DETAIL, "status": "CANCELLED"}, "Bulletin cancelled."),
        **COMMON_ERRORS,
        400: error_examples(BulletinStatusException),
        **NOT_FOUND,
    },
)
async def cancel_bulletin(
    bulletin_id: int, data: BulletinCancelDTO, db: DBDep, user: CurrentUserDep
):
    result = await BulletinService(db).cancel(bulletin_id, user, data)
    return ResponseBuilder.success(data=result, message="Bulletin cancelled.")


@router.delete(
    "/{bulletin_id}",
    summary="Удалить неотправленный бюллетень (PENDING)",
    description="Связанная заявка возвращается Фонду (COUNCIL_REVIEW → FUND_REVIEW).",
    dependencies=[delete_dep],
    responses={
        200: success_example(None, "Bulletin deleted."),
        **COMMON_ERRORS,
        400: error_examples(BulletinStatusException),
        **NOT_FOUND,
    },
)
async def delete_bulletin(bulletin_id: int, db: DBDep, user: CurrentUserDep):
    await BulletinService(db).delete(bulletin_id, user)
    return ResponseBuilder.success(message="Bulletin deleted.")
