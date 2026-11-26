"""Акты исполнителей в рабочем окне Фонда: проверка, возврат, аннулирование и подпись руководителя."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, Response

from src.act.apis.examples import DETAIL, FUND_COUNTERS, LIST_ITEM
from src.act.apis.my_act_api import PDF_RESPONSE, pdf_response
from src.act.schemas.act_schema import ActCancelDTO, ActReturnDTO, ActSignDTO, FundActFilterDTO
from src.act.services.act_service import ActService
from src.common.dependencies import (
    CurrentUserDep,
    DBDep,
    PaginationDep,
    require_any_permission,
    require_permission,
)
from src.common.responses.exceptions import (
    ActAttachmentNotFoundException,
    ActContentChangedException,
    ActNotApproverException,
    ActNotFoundException,
    ActPdfNotFoundException,
    ActStatusException,
    EimzoInvalidCodeException,
    EimzoSignerMismatchException,
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

router = APIRouter(prefix="/fund/acts", tags=["Акты выполненных работ: рабочее окно Фонда"])

FilterDep = Annotated[FundActFilterDTO, Depends()]
# Окно открыто проверяющему и руководителю, который подписывает акты.
read_dep = Depends(require_any_permission("act_review.read", "act_signing.approve"))
review_dep = Depends(require_permission(Module.ACT_REVIEW, Action.APPROVE))
sign_dep = Depends(require_permission(Module.ACT_SIGNING, Action.APPROVE))
NOT_FOUND = {404: error_examples(ActNotFoundException)}


@router.get(
    "",
    summary="Акты исполнителей: вкладки, статус, договор, исполнитель, поиск",
    description=(
        "Черновики исполнителей не показываются. Руководитель без права act_review.read "
        "видит только акты по договорам, где он подписывает (`mine=true`)."
    ),
    dependencies=[read_dep],
    responses={200: paginated_example(LIST_ITEM), **READ_ERRORS},
)
async def get_acts(db: DBDep, user: CurrentUserDep, pagination: PaginationDep, filters: FilterDep):
    data = await ActService(db).fund_list(user, filters, pagination.page, pagination.per_page)
    return ResponseBuilder.success(data=data, message="Acts retrieved.")


@router.get(
    "/counters",
    summary="Счётчики по статусам и акты, ждущие моей подписи",
    dependencies=[read_dep],
    responses={200: success_example(FUND_COUNTERS, "Counters retrieved."), **READ_ERRORS},
)
async def get_counters(db: DBDep, user: CurrentUserDep):
    data = await ActService(db).fund_counters(user)
    return ResponseBuilder.success(data=data, message="Counters retrieved.")


@router.get(
    "/{act_id}",
    summary="Акт: строки, приложение, подписи E-IMZO, история и доступные действия",
    dependencies=[read_dep],
    responses={200: success_example(DETAIL, "Act retrieved."), **READ_ERRORS, **NOT_FOUND},
)
async def get_act(act_id: int, db: DBDep, user: CurrentUserDep):
    data = await ActService(db).fund_detail(act_id, user)
    return ResponseBuilder.success(data=data, message="Act retrieved.")


@router.get(
    "/{act_id}/pdf",
    summary="PDF акта; у подписанного — сохранённый итоговый документ",
    dependencies=[read_dep],
    response_class=Response,
    responses={
        **PDF_RESPONSE,
        **READ_ERRORS,
        404: error_examples(ActNotFoundException, ActPdfNotFoundException),
    },
)
async def get_pdf(act_id: int, db: DBDep, user: CurrentUserDep):
    content, name = await ActService(db).fund_pdf(act_id, user)
    return pdf_response(content, name)


@router.get(
    "/{act_id}/attachments/{attachment_id}",
    summary="Файл скриншота из приложения",
    dependencies=[read_dep],
    response_class=FileResponse,
    responses={
        **READ_ERRORS,
        404: error_examples(ActNotFoundException, ActAttachmentNotFoundException),
    },
)
async def get_attachment(act_id: int, attachment_id: int, db: DBDep, user: CurrentUserDep):
    path, content_type, name = await ActService(db).fund_attachment_file(
        act_id, attachment_id, user
    )
    return FileResponse(path, media_type=content_type, filename=name)


@router.post(
    "/{act_id}/accept",
    summary="Принять акт после проверки: он уходит на подпись руководителю",
    dependencies=[review_dep],
    responses={
        200: success_example({**DETAIL, "status": "ACCEPTED"}, "Act accepted."),
        **COMMON_ERRORS,
        400: error_examples(ActStatusException),
        409: error_examples(ActContentChangedException),
        **NOT_FOUND,
    },
)
async def accept_act(act_id: int, db: DBDep, user: CurrentUserDep):
    result = await ActService(db).accept(act_id, user)
    return ResponseBuilder.success(data=result, message="Act accepted.")


@router.post(
    "/{act_id}/return",
    summary="Вернуть акт исполнителю с замечанием",
    description=(
        "Проверяющий — из SUBMITTED или ACCEPTED; руководитель — из ACCEPTED по своему договору. "
        "Подписи снимаются: исправленный акт исполнитель подписывает заново."
    ),
    dependencies=[read_dep],
    responses={
        200: success_example({**DETAIL, "status": "RETURNED"}, "Act returned."),
        **COMMON_ERRORS,
        400: error_examples(ActStatusException),
        **NOT_FOUND,
    },
)
async def return_act(act_id: int, data: ActReturnDTO, db: DBDep, user: CurrentUserDep):
    result = await ActService(db).send_back(act_id, data.comment, user)
    return ResponseBuilder.success(data=result, message="Act returned.")


@router.post(
    "/{act_id}/cancel",
    summary="Аннулировать акт (до подписи руководителя)",
    dependencies=[review_dep],
    responses={
        200: success_example({**DETAIL, "status": "CANCELLED"}, "Act cancelled."),
        **COMMON_ERRORS,
        400: error_examples(ActStatusException),
        **NOT_FOUND,
    },
)
async def cancel_act(act_id: int, data: ActCancelDTO, db: DBDep, user: CurrentUserDep):
    result = await ActService(db).cancel(act_id, data.reason, user)
    return ResponseBuilder.success(data=result, message="Act cancelled.")


@router.post(
    "/{act_id}/sign",
    summary="Подписать принятый акт ключом E-IMZO (руководитель по договору)",
    description=(
        "Подписывает только руководитель, указанный в договоре; ПИНФЛ сертификата должен "
        "совпасть с его ПИНФЛ. Подпись связана с подписью исполнителя. Итоговый PDF "
        "формируется один раз и больше не меняется."
    ),
    dependencies=[sign_dep],
    responses={
        200: success_example({**DETAIL, "status": "SIGNED"}, "Act signed."),
        **COMMON_ERRORS,
        400: error_examples(ActStatusException, EimzoInvalidCodeException),
        403: error_examples(ActNotApproverException, EimzoSignerMismatchException),
        409: error_examples(ActContentChangedException),
        **NOT_FOUND,
    },
)
async def sign_act(act_id: int, data: ActSignDTO, db: DBDep, user: CurrentUserDep):
    result = await ActService(db).sign(act_id, data.code, user)
    return ResponseBuilder.success(data=result, message="Act signed.")
