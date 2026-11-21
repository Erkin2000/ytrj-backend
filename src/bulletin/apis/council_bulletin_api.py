"""Бюллетени Совета — личное рабочее окно члена Совета."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, Response

from src.bulletin.apis.examples import CALENDAR, COUNCIL_DETAIL, COUNCIL_ITEM
from src.bulletin.apis.fund_bulletin_api import PDF_RESPONSE, pdf_response
from src.bulletin.enums import CouncilBulletinTab
from src.bulletin.schemas.bulletin_schema import BulletinSignDTO
from src.bulletin.services.council_bulletin_service import CouncilBulletinService
from src.common.dependencies import CurrentUserDep, DBDep, PaginationDep, require_permission
from src.common.responses.exceptions import (
    BulletinAlreadySignedException,
    BulletinDeadlinePassedException,
    BulletinFileNotFoundException,
    BulletinFileNotViewedException,
    BulletinNotFoundException,
    BulletinNotOpenForSigningException,
    BulletinNotViewedException,
    EimzoInvalidCodeException,
    EimzoSignerMismatchException,
)
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import (
    COMMON_ERRORS,
    error_examples,
    paginated_example,
    success_example,
)
from src.rbac.permissions import Action, Module

router = APIRouter(prefix="/council/bulletins", tags=["Бюллетени: рабочее окно Совета"])

read_dep = Depends(require_permission(Module.COUNCIL_REVIEW, Action.READ))
sign_dep = Depends(require_permission(Module.COUNCIL_REVIEW, Action.APPROVE))

NOT_FOUND = {404: error_examples(BulletinNotFoundException)}

TAB_DESCRIPTION = (
    "`new` — ещё не открытые; `to_sign` — ждут моей подписи (срок не прошёл); "
    "`signed` — подписанные; `overdue` — срок прошёл без подписи; `all` — все."
)


@router.get(
    "",
    summary="Мои бюллетени: новые, на подпись, подписанные, просроченные",
    description=(
        "Только бюллетени, отправленные этому члену Совета. Видны только собственный "
        "статус и решение — чужие подписи не показываются."
    ),
    dependencies=[read_dep],
    responses={200: paginated_example(COUNCIL_ITEM), **COMMON_ERRORS},
)
async def get_my_bulletins(
    db: DBDep,
    user: CurrentUserDep,
    pagination: PaginationDep,
    tab: CouncilBulletinTab = Query(CouncilBulletinTab.ALL, description=TAB_DESCRIPTION),
):
    data = await CouncilBulletinService(db).get_list(
        user, tab, pagination.page, pagination.per_page
    )
    return ResponseBuilder.success(data=data, message="Bulletins retrieved.")


@router.get(
    "/counters",
    summary="Счётчики вкладок: новые, на подпись, подписанные, просроченные",
    dependencies=[read_dep],
    responses={
        200: success_example(
            {"new": 1, "to_sign": 2, "signed": 7, "overdue": 0}, "Counters retrieved."
        ),
        **COMMON_ERRORS,
    },
)
async def get_counters(db: DBDep, user: CurrentUserDep):
    data = await CouncilBulletinService(db).get_counters(user)
    return ResponseBuilder.success(data=data, message="Counters retrieved.")


@router.get(
    "/calendar",
    summary="Мой календарь: когда пришёл бюллетень и до какого дня его подписать",
    description="Дни без событий не возвращаются. Диапазон — не больше 93 дней.",
    dependencies=[read_dep],
    responses={200: success_example(CALENDAR, "Calendar retrieved."), **COMMON_ERRORS},
)
async def get_calendar(
    db: DBDep,
    user: CurrentUserDep,
    date_from: date | None = Query(
        None, description="Первый день (по Ташкенту); по умолчанию — начало месяца."
    ),
    date_to: date | None = Query(
        None, description="Последний день включительно; по умолчанию — конец месяца."
    ),
):
    data = await CouncilBulletinService(db).get_calendar(user, date_from, date_to)
    return ResponseBuilder.success(data=data, message="Calendar retrieved.")


@router.get(
    "/{bulletin_id}",
    summary="Открыть бюллетень (просмотр фиксируется)",
    description=(
        "`my.can_sign` и `my.sign_blockers` показывают, можно ли подписать. Если бюллетень "
        "относится к заявке, её можно открыть по `application.url`."
    ),
    dependencies=[read_dep],
    responses={
        200: success_example(COUNCIL_DETAIL, "Bulletin retrieved."),
        **COMMON_ERRORS,
        **NOT_FOUND,
    },
)
async def open_bulletin(bulletin_id: int, db: DBDep, user: CurrentUserDep):
    data = await CouncilBulletinService(db).open(bulletin_id, user)
    return ResponseBuilder.success(data=data, message="Bulletin retrieved.")


@router.get(
    "/{bulletin_id}/file",
    summary="Открыть файл бюллетеня (просмотр файла фиксируется)",
    dependencies=[read_dep],
    response_class=FileResponse,
    responses={
        **COMMON_ERRORS,
        404: error_examples(BulletinNotFoundException, BulletinFileNotFoundException),
    },
)
async def open_file(bulletin_id: int, db: DBDep, user: CurrentUserDep):
    path, content_type, file_name = await CouncilBulletinService(db).open_file(bulletin_id, user)
    return FileResponse(path, media_type=content_type, filename=file_name)


@router.get(
    "/{bulletin_id}/pdf",
    summary="PDF бюллетеня: все сведения, решения членов Совета и QR-код внизу",
    description="Документ из текущих данных. Просмотр PDF не заменяет просмотр файла для подписи.",
    dependencies=[read_dep],
    response_class=Response,
    responses={**PDF_RESPONSE, **COMMON_ERRORS, 404: error_examples(BulletinNotFoundException)},
)
async def get_pdf(bulletin_id: int, db: DBDep, user: CurrentUserDep):
    content, file_name = await CouncilBulletinService(db).get_pdf(bulletin_id, user)
    return pdf_response(content, file_name)


@router.post(
    "/{bulletin_id}/sign",
    summary="Подписать бюллетень ключом E-IMZO: «Согласен» или «Против»",
    description=(
        "Сначала откройте бюллетень и прикреплённый файл. Затем фронтенд открывает "
        "страницу-мост E-IMZO (`GET /auth/eimzo/config`), член Совета подписывает своим "
        "ключом, и полученный `code` передаётся сюда вместе с решением. ПИНФЛ сертификата "
        "должен совпасть с ПИНФЛ члена Совета. Подписать можно один раз и до срока. "
        "Если бюллетень относится к заявке: «Против» — заявка отклоняется Советом, "
        "«Согласен» всех членов — заявка уходит в банк."
    ),
    dependencies=[sign_dep],
    responses={
        200: success_example(
            {
                **COUNCIL_DETAIL,
                "status": "PARTIALLY_SIGNED",
                "my_status": "SIGNED",
                "my_decision": "AGREE",
                "signed_at": "2026-11-20T06:15:00Z",
                "my": {
                    **COUNCIL_DETAIL["my"],
                    "status": "SIGNED",
                    "file_viewed_at": "2026-11-20T06:11:00Z",
                    "decision": "AGREE",
                    "signed_at": "2026-11-20T06:15:00Z",
                    "sign_blockers": ["already_signed"],
                },
            },
            "Bulletin signed.",
        ),
        **COMMON_ERRORS,
        400: error_examples(
            BulletinNotViewedException,
            BulletinFileNotViewedException,
            BulletinAlreadySignedException,
            BulletinDeadlinePassedException,
            BulletinNotOpenForSigningException,
            EimzoInvalidCodeException,
        ),
        403: error_examples(EimzoSignerMismatchException),
        **NOT_FOUND,
    },
)
async def sign_bulletin(bulletin_id: int, data: BulletinSignDTO, db: DBDep, user: CurrentUserDep):
    result = await CouncilBulletinService(db).sign(bulletin_id, user, data)
    return ResponseBuilder.success(data=result, message="Bulletin signed.")
