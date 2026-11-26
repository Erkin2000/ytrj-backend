"""Акты исполнителя: черновик, строки работ, скриншоты приложения, подпись E-IMZO и отправка."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form
from fastapi.responses import FileResponse, Response

from src.act.apis.examples import CHECK, DETAIL, LIST_ITEM, MY_COUNTERS
from src.act.schemas.act_schema import (
    ActAttachmentForm,
    ActAttachmentOrderDTO,
    ActAttachmentUpdateDTO,
    ActCreateDTO,
    ActItemsDTO,
    ActSignDTO,
    ActUpdateDTO,
    MyActFilterDTO,
)
from src.act.services.act_service import ActService
from src.common.dependencies import CurrentUserDep, DBDep, PaginationDep, require_permission
from src.common.responses.exceptions import (
    ActAttachmentNotFoundException,
    ActLimitException,
    ActNotEditableException,
    ActNotFoundException,
    ActNotReadyException,
    ActPeriodException,
    ActPeriodOverlapException,
    ActStatusException,
    ContractClosedException,
    ContractNotFoundException,
    EimzoInvalidCodeException,
    EimzoSignerMismatchException,
    InvalidPhotoException,
    PhotoTooLargeException,
)
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import (
    COMMON_ERRORS,
    READ_ERRORS,
    error_examples,
    paginated_example,
    success_example,
)
from src.rbac.permissions import Action, Module

router = APIRouter(prefix="/my/acts", tags=["Мои акты выполненных работ"])

FilterDep = Annotated[MyActFilterDTO, Depends()]
read_dep = Depends(require_permission(Module.ACTS, Action.READ))
create_dep = Depends(require_permission(Module.ACTS, Action.CREATE))
update_dep = Depends(require_permission(Module.ACTS, Action.UPDATE))
delete_dep = Depends(require_permission(Module.ACTS, Action.DELETE))

NOT_FOUND = {404: error_examples(ActNotFoundException)}
NOT_EDITABLE = {400: error_examples(ActNotEditableException)}
PDF_RESPONSE = {200: {"content": {"application/pdf": {}}, "description": "PDF"}}


def pdf_response(content: bytes, file_name: str) -> Response:
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{file_name}"',
            "Cache-Control": "no-store",
        },
    )


@router.get(
    "",
    summary="Мои акты: по статусу и договору, новые периоды сверху",
    dependencies=[read_dep],
    responses={200: paginated_example(LIST_ITEM), **READ_ERRORS},
)
async def get_my_acts(
    db: DBDep, user: CurrentUserDep, pagination: PaginationDep, filters: FilterDep
):
    data = await ActService(db).my_list(user, filters, pagination.page, pagination.per_page)
    return ResponseBuilder.success(data=data, message="Acts retrieved.")


@router.get(
    "/counters",
    summary="Мои акты: счётчики по статусам",
    dependencies=[read_dep],
    responses={200: success_example(MY_COUNTERS, "Counters retrieved."), **READ_ERRORS},
)
async def get_my_counters(db: DBDep, user: CurrentUserDep):
    data = await ActService(db).my_counters(user)
    return ResponseBuilder.success(data=data, message="Counters retrieved.")


@router.post(
    "",
    status_code=201,
    summary="Новый акт по своему договору (черновик)",
    description=(
        "Период — внутри срока договора и без пересечения с другими актами договора (409). "
        "Вводная часть берётся из предмета договора. `copy_from_id` — скопировать строки "
        "из прошлого акта."
    ),
    dependencies=[create_dep],
    responses={
        201: success_example({**DETAIL, "status": "DRAFT"}, "Act created."),
        **COMMON_ERRORS,
        400: error_examples(ActPeriodException, ContractClosedException),
        404: error_examples(ContractNotFoundException, ActNotFoundException),
        409: error_examples(ActPeriodOverlapException),
    },
)
async def create_act(data: ActCreateDTO, db: DBDep, user: CurrentUserDep):
    result = await ActService(db).create(data, user)
    return ResponseBuilder.success(data=result, message="Act created.", status_code=201)


@router.get(
    "/{act_id}",
    summary="Мой акт: строки, приложение, подписи, история и доступные действия",
    dependencies=[read_dep],
    responses={200: success_example(DETAIL, "Act retrieved."), **READ_ERRORS, **NOT_FOUND},
)
async def get_my_act(act_id: int, db: DBDep, user: CurrentUserDep):
    data = await ActService(db).my_detail(act_id, user)
    return ResponseBuilder.success(data=data, message="Act retrieved.")


@router.patch(
    "/{act_id}",
    summary="Изменить период, дату, вводную часть или заголовок приложения",
    dependencies=[update_dep],
    responses={
        200: success_example(DETAIL, "Act updated."),
        **COMMON_ERRORS,
        400: error_examples(ActNotEditableException, ActPeriodException),
        409: error_examples(ActPeriodOverlapException),
        **NOT_FOUND,
    },
)
async def update_act(act_id: int, data: ActUpdateDTO, db: DBDep, user: CurrentUserDep):
    result = await ActService(db).update(act_id, data, user)
    return ResponseBuilder.success(data=result, message="Act updated.")


@router.delete(
    "/{act_id}",
    summary="Удалить черновик (не отправлявшийся)",
    dependencies=[delete_dep],
    responses={
        200: success_example(None, "Act deleted."),
        **COMMON_ERRORS,
        **NOT_EDITABLE,
        **NOT_FOUND,
    },
)
async def delete_act(act_id: int, db: DBDep, user: CurrentUserDep):
    await ActService(db).delete(act_id, user)
    return ResponseBuilder.success(message="Act deleted.")


@router.put(
    "/{act_id}/items",
    summary="Строки таблицы выполненных работ: список заменяется целиком",
    dependencies=[update_dep],
    responses={
        200: success_example(DETAIL, "Act items saved."),
        **COMMON_ERRORS,
        **NOT_EDITABLE,
        **NOT_FOUND,
    },
)
async def set_items(act_id: int, data: ActItemsDTO, db: DBDep, user: CurrentUserDep):
    result = await ActService(db).set_items(act_id, data, user)
    return ResponseBuilder.success(data=result, message="Act items saved.")


@router.post(
    "/{act_id}/attachments",
    summary="Добавить скриншот в приложение (multipart/form-data)",
    description="JPEG или PNG до 5 МБ; `caption` — подпись, `url` — адрес страницы (необязательно).",
    dependencies=[update_dep],
    responses={
        200: success_example(DETAIL, "Attachment added."),
        **COMMON_ERRORS,
        400: error_examples(
            ActNotEditableException,
            ActLimitException,
            InvalidPhotoException,
            PhotoTooLargeException,
        ),
        **NOT_FOUND,
    },
)
async def add_attachment(
    act_id: int,
    db: DBDep,
    user: CurrentUserDep,
    form: Annotated[ActAttachmentForm, Form(media_type="multipart/form-data")],
):
    result = await ActService(db).add_attachment(act_id, form, user)
    return ResponseBuilder.success(data=result, message="Attachment added.")


@router.put(
    "/{act_id}/attachments/order",
    summary="Порядок файлов приложения",
    dependencies=[update_dep],
    responses={
        200: success_example(DETAIL, "Attachments reordered."),
        **COMMON_ERRORS,
        400: error_examples(ActNotEditableException, ActLimitException),
        **NOT_FOUND,
    },
)
async def order_attachments(
    act_id: int, data: ActAttachmentOrderDTO, db: DBDep, user: CurrentUserDep
):
    result = await ActService(db).order_attachments(act_id, data, user)
    return ResponseBuilder.success(data=result, message="Attachments reordered.")


@router.patch(
    "/{act_id}/attachments/{attachment_id}",
    summary="Изменить подпись или адрес скриншота",
    dependencies=[update_dep],
    responses={
        200: success_example(DETAIL, "Attachment updated."),
        **COMMON_ERRORS,
        **NOT_EDITABLE,
        404: error_examples(ActNotFoundException, ActAttachmentNotFoundException),
    },
)
async def update_attachment(
    act_id: int,
    attachment_id: int,
    data: ActAttachmentUpdateDTO,
    db: DBDep,
    user: CurrentUserDep,
):
    result = await ActService(db).update_attachment(act_id, attachment_id, data, user)
    return ResponseBuilder.success(data=result, message="Attachment updated.")


@router.delete(
    "/{act_id}/attachments/{attachment_id}",
    summary="Удалить скриншот из приложения",
    dependencies=[update_dep],
    responses={
        200: success_example(DETAIL, "Attachment deleted."),
        **COMMON_ERRORS,
        **NOT_EDITABLE,
        404: error_examples(ActNotFoundException, ActAttachmentNotFoundException),
    },
)
async def delete_attachment(act_id: int, attachment_id: int, db: DBDep, user: CurrentUserDep):
    result = await ActService(db).delete_attachment(act_id, attachment_id, user)
    return ResponseBuilder.success(data=result, message="Attachment deleted.")


@router.get(
    "/{act_id}/attachments/{attachment_id}",
    summary="Файл скриншота",
    dependencies=[read_dep],
    response_class=FileResponse,
    responses={
        **READ_ERRORS,
        404: error_examples(ActNotFoundException, ActAttachmentNotFoundException),
    },
)
async def get_attachment(act_id: int, attachment_id: int, db: DBDep, user: CurrentUserDep):
    path, content_type, name = await ActService(db).my_attachment_file(act_id, attachment_id, user)
    return FileResponse(path, media_type=content_type, filename=name)


@router.get(
    "/{act_id}/pdf",
    summary="PDF акта: до подписи руководителя — с водяным знаком «QORALAMA»",
    dependencies=[read_dep],
    response_class=Response,
    responses={**PDF_RESPONSE, **READ_ERRORS, **NOT_FOUND},
)
async def get_pdf(act_id: int, db: DBDep, user: CurrentUserDep):
    content, name = await ActService(db).my_pdf(act_id, user)
    return pdf_response(content, name)


@router.get(
    "/{act_id}/submission-check",
    summary="Чего не хватает для отправки",
    dependencies=[read_dep],
    responses={200: success_example(CHECK, "Check done."), **READ_ERRORS, **NOT_FOUND},
)
async def submission_check(act_id: int, db: DBDep, user: CurrentUserDep):
    data = await ActService(db).submission_check(act_id, user)
    return ResponseBuilder.success(data=data, message="Check done.")


@router.post(
    "/{act_id}/submit",
    summary="Подписать акт ключом E-IMZO и отправить в Фонд",
    description=(
        "`code` — с моста E-IMZO; ПИНФЛ сертификата должен совпасть с ПИНФЛ исполнителя. "
        "Фиксируется SHA-256 содержимого акта: строки, файлы приложения и реквизиты договора."
    ),
    dependencies=[update_dep],
    responses={
        200: success_example(DETAIL, "Act submitted."),
        **COMMON_ERRORS,
        400: error_examples(
            ActNotEditableException,
            ActNotReadyException,
            ActPeriodException,
            EimzoInvalidCodeException,
        ),
        403: error_examples(EimzoSignerMismatchException),
        409: error_examples(ActPeriodOverlapException),
        **NOT_FOUND,
    },
)
async def submit_act(act_id: int, data: ActSignDTO, db: DBDep, user: CurrentUserDep):
    result = await ActService(db).submit(act_id, data.code, user)
    return ResponseBuilder.success(data=result, message="Act submitted.")


@router.post(
    "/{act_id}/withdraw",
    summary="Отозвать отправленный акт, пока Фонд его не принял",
    description="Подпись исполнителя снимается, акт снова становится черновиком.",
    dependencies=[update_dep],
    responses={
        200: success_example({**DETAIL, "status": "DRAFT"}, "Act withdrawn."),
        **COMMON_ERRORS,
        400: error_examples(ActStatusException),
        **NOT_FOUND,
    },
)
async def withdraw_act(act_id: int, db: DBDep, user: CurrentUserDep):
    result = await ActService(db).withdraw(act_id, user)
    return ResponseBuilder.success(data=result, message="Act withdrawn.")
