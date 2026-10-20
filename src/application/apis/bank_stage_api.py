"""Рабочее окно ответственного сотрудника банка: только заявки своего банка."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from src.application.schemas.application_schema import ApplicationFilterDTO, BankDecisionDTO
from src.application.services.bank_service import BankService
from src.common.dependencies import CurrentUserDep, DBDep, PaginationDep, require_permission
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import COMMON_ERRORS, paginated_example, success_example
from src.rbac.permissions import Action, Module

router = APIRouter(prefix="/bank/applications", tags=["Заявки: рабочее окно банка"])

FilterDep = Annotated[ApplicationFilterDTO, Depends()]

ITEM = {
    "id": 12,
    "number": "JG-2026-000012",
    "status": "SENT_TO_BANK",
    "subject_type": "MCHJ",
    "legal_name": "ООО «Навруз»",
    "applicant_full_name": "Алиев Али Алиевич",
    "submitted_at": "2026-10-19T10:05:00Z",
}


@router.get(
    "",
    summary="Заявки банка: новые / на рассмотрении / завершённые",
    dependencies=[Depends(require_permission(Module.BANK_REVIEW, Action.READ))],
    responses={200: paginated_example(ITEM), **COMMON_ERRORS},
)
async def get_bank_applications(
    db: DBDep,
    user: CurrentUserDep,
    pagination: PaginationDep,
    filters: FilterDep,
    bucket: Literal["new", "in_review", "completed"] | None = Query(
        None, description="Раздел рабочего окна"
    ),
):
    data = await BankService(db).get_bank_applications(
        user, bucket, filters, pagination.page, pagination.per_page
    )
    return ResponseBuilder.success(data=data, message="Applications retrieved successfully.")


@router.get(
    "/counters",
    summary="Счётчики рабочего окна банка",
    dependencies=[Depends(require_permission(Module.BANK_REVIEW, Action.READ))],
    responses={
        200: success_example({"new": 2, "in_review": 1, "completed": 5}, "Counters retrieved."),
        **COMMON_ERRORS,
    },
)
async def get_counters(db: DBDep, user: CurrentUserDep):
    data = await BankService(db).get_counters(user)
    return ResponseBuilder.success(data=data, message="Counters retrieved.")


@router.post(
    "/{application_id}/accept",
    summary="Принять заявку в рассмотрение (SENT_TO_BANK → BANK_REVIEW)",
    dependencies=[Depends(require_permission(Module.BANK_REVIEW, Action.UPDATE))],
    responses={
        200: success_example({**ITEM, "status": "BANK_REVIEW"}, "Application accepted."),
        **COMMON_ERRORS,
    },
)
async def accept_application(application_id: int, db: DBDep, user: CurrentUserDep):
    data = await BankService(db).accept(application_id, user)
    return ResponseBuilder.success(data=data, message="Application accepted.")


@router.post(
    "/{application_id}/decision",
    summary="Результат банка: одобрение или отказ с причиной (изменить нельзя)",
    dependencies=[Depends(require_permission(Module.BANK_REVIEW, Action.APPROVE))],
    responses={
        200: success_example({**ITEM, "status": "BANK_APPROVED"}, "Bank decision recorded."),
        **COMMON_ERRORS,
    },
)
async def bank_decision(
    application_id: int, data: BankDecisionDTO, db: DBDep, user: CurrentUserDep
):
    result = await BankService(db).decide(application_id, user, data)
    return ResponseBuilder.success(data=result, message="Bank decision recorded.")
