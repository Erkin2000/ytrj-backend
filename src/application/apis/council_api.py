"""Рабочее окно члена Совета: только направленные ему заявки."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.application.schemas.application_schema import ApplicationFilterDTO, CouncilDecisionDTO
from src.application.services.council_service import CouncilService
from src.common.dependencies import CurrentUserDep, DBDep, PaginationDep, require_permission
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import COMMON_ERRORS, paginated_example, success_example
from src.rbac.permissions import Action, Module

router = APIRouter(prefix="/council/applications", tags=["Заявки: рабочее окно Совета"])

FilterDep = Annotated[ApplicationFilterDTO, Depends()]

ITEM = {
    "id": 12,
    "number": "JG-2026-000012",
    "status": "COUNCIL_REVIEW",
    "subject_type": "YATT",
    "bank": {"id": 1, "code": "microcreditbank", "name": "Microcreditbank"},
    "applicant_full_name": "Алиев Али Алиевич",
}


@router.get(
    "",
    summary="Направленные мне заявки (нерассмотренные — pending_only=true)",
    dependencies=[Depends(require_permission(Module.COUNCIL_REVIEW, Action.READ))],
    responses={200: paginated_example(ITEM), **COMMON_ERRORS},
)
async def get_assigned_applications(
    db: DBDep,
    user: CurrentUserDep,
    pagination: PaginationDep,
    filters: FilterDep,
    pending_only: bool = Query(False),
):
    data = await CouncilService(db).get_assigned_applications(
        user, filters, pagination.page, pagination.per_page, pending_only=pending_only
    )
    return ResponseBuilder.success(data=data, message="Applications retrieved successfully.")


@router.get(
    "/counters",
    summary="Счётчики рабочего окна Совета",
    dependencies=[Depends(require_permission(Module.COUNCIL_REVIEW, Action.READ))],
    responses={
        200: success_example({"pending": 1, "approved": 4, "rejected": 1}, "Counters retrieved."),
        **COMMON_ERRORS,
    },
)
async def get_counters(db: DBDep, user: CurrentUserDep):
    data = await CouncilService(db).get_counters(user)
    return ResponseBuilder.success(data=data, message="Counters retrieved.")


@router.post(
    "/{application_id}/decision",
    summary="Решение члена Совета: «Согласен» / «Отклоняю» (причина обязательна)",
    dependencies=[Depends(require_permission(Module.COUNCIL_REVIEW, Action.APPROVE))],
    responses={
        200: success_example(
            {**ITEM, "status": "DEMAND_DOCUMENT_CREATED"}, "Council decision recorded."
        ),
        **COMMON_ERRORS,
    },
)
async def council_decision(
    application_id: int, data: CouncilDecisionDTO, db: DBDep, user: CurrentUserDep
):
    result = await CouncilService(db).decide(application_id, user, data)
    return ResponseBuilder.success(data=result, message="Council decision recorded.")
