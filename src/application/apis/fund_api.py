"""Рабочее окно Фонда (и Super Admin): все заявки, скоринг, Совет, финансирование."""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.application.schemas.application_schema import (
    ApplicationFilterDTO,
    CompleteApplicationDTO,
    ResourceAllocationCreateDTO,
    ScoringResultRecordDTO,
    SendToCouncilDTO,
)
from src.application.services.fund_service import FundService
from src.common.dependencies import CurrentUserDep, DBDep, PaginationDep, require_permission
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import COMMON_ERRORS, paginated_example, success_example
from src.rbac.permissions import Action, Module

router = APIRouter(prefix="/fund/applications", tags=["Заявки: рабочее окно Фонда"])

FilterDep = Annotated[ApplicationFilterDTO, Depends()]

ITEM = {
    "id": 12,
    "number": "JG-2026-000012",
    "status": "BANK_APPROVED",
    "subject_type": "YATT",
    "bank": {"id": 1, "code": "microcreditbank", "name": "Microcreditbank"},
    "applicant_full_name": "Алиев Али Алиевич",
    "scoring_retry_required": False,
    "submitted_at": "2026-10-19T10:05:00Z",
}


@router.get(
    "",
    summary="Поиск заявок по статусу, банку, дате, типу субъекта, номеру/ФИО",
    dependencies=[Depends(require_permission(Module.APPLICATIONS, Action.READ))],
    responses={200: paginated_example(ITEM), **COMMON_ERRORS},
)
async def get_applications(
    db: DBDep, user: CurrentUserDep, pagination: PaginationDep, filters: FilterDep
):
    data = await FundService(db).get_applications(
        user, filters, pagination.page, pagination.per_page
    )
    return ResponseBuilder.success(data=data, message="Applications retrieved successfully.")


@router.get(
    "/counters",
    summary="Счётчики главного экрана Фонда",
    dependencies=[Depends(require_permission(Module.APPLICATIONS, Action.READ))],
    responses={
        200: success_example(
            {
                "new": 3,
                "to_council": 2,
                "in_council": 1,
                "to_allocate": 1,
                "in_allocation": 0,
                "completed": 10,
            },
            "Counters retrieved.",
        ),
        **COMMON_ERRORS,
    },
)
async def get_counters(db: DBDep, user: CurrentUserDep):
    data = await FundService(db).get_counters(user)
    return ResponseBuilder.success(data=data, message="Counters retrieved.")


@router.get(
    "/{application_id}",
    summary="Карточка заявки (полные данные, этапы, документы)",
    dependencies=[Depends(require_permission(Module.APPLICATIONS, Action.READ))],
    responses={200: success_example(ITEM, "Application found."), **COMMON_ERRORS},
)
async def get_application(application_id: int, db: DBDep, user: CurrentUserDep):
    data = await FundService(db).get_detail(application_id, user)
    return ResponseBuilder.success(data=data, message="Application found.")


# ---------- скоринг ----------


@router.get(
    "/{application_id}/scoring",
    summary="Полные результаты скоринга KATM: по какой проверке и почему",
    dependencies=[Depends(require_permission(Module.SCORING, Action.READ))],
    responses={
        200: success_example(
            [
                {
                    "id": 1,
                    "provider": "KATM",
                    "result": "FAILED",
                    "eligibility_passed": None,
                    "details": {"check": "credit_history", "reason": "..."},
                    "created_at": "2026-10-19T10:05:00Z",
                }
            ],
            "Scoring attempts retrieved.",
        ),
        **COMMON_ERRORS,
    },
)
async def get_scoring(application_id: int, db: DBDep, user: CurrentUserDep):
    data = await FundService(db).get_scoring(application_id, user)
    return ResponseBuilder.success(data=data, message="Scoring attempts retrieved.")


@router.post(
    "/{application_id}/scoring/retry",
    summary="Повторная обработка после технической ошибки KATM",
    dependencies=[Depends(require_permission(Module.SCORING, Action.UPDATE))],
    responses={200: success_example(ITEM, "Scoring restarted."), **COMMON_ERRORS},
)
async def retry_scoring(application_id: int, db: DBDep, user: CurrentUserDep):
    data = await FundService(db).retry_scoring(application_id, user)
    return ResponseBuilder.success(data=data, message="Scoring restarted.")


@router.post(
    "/{application_id}/scoring/result",
    summary="Внести результат скоринга вручную (режим manual)",
    dependencies=[Depends(require_permission(Module.SCORING, Action.APPROVE))],
    responses={200: success_example(ITEM, "Scoring result recorded."), **COMMON_ERRORS},
)
async def record_scoring_result(
    application_id: int, data: ScoringResultRecordDTO, db: DBDep, user: CurrentUserDep
):
    result = await FundService(db).record_scoring_result(application_id, user, data)
    return ResponseBuilder.success(data=result, message="Scoring result recorded.")


# ---------- Совет ----------


@router.post(
    "/{application_id}/send-to-council",
    summary="Направить заявку в Совет (BANK_APPROVED → COUNCIL_REVIEW)",
    dependencies=[Depends(require_permission(Module.APPLICATIONS, Action.APPROVE))],
    responses={
        200: success_example({**ITEM, "status": "COUNCIL_REVIEW"}, "Application sent to council."),
        **COMMON_ERRORS,
    },
)
async def send_to_council(
    application_id: int, data: SendToCouncilDTO, db: DBDep, user: CurrentUserDep
):
    result = await FundService(db).send_to_council(application_id, user, data)
    return ResponseBuilder.success(data=result, message="Application sent to council.")


# ---------- финансирование ----------


@router.post(
    "/{application_id}/allocate",
    summary="Зафиксировать выделение ресурсов (после документа «Требование подтверждено»)",
    dependencies=[Depends(require_permission(Module.ALLOCATION, Action.CREATE))],
    responses={
        200: success_example({**ITEM, "status": "RESOURCE_ALLOCATION"}, "Resources allocated."),
        **COMMON_ERRORS,
    },
)
async def allocate_resources(
    application_id: int, data: ResourceAllocationCreateDTO, db: DBDep, user: CurrentUserDep
):
    result = await FundService(db).allocate_resources(application_id, user, data)
    return ResponseBuilder.success(data=result, message="Resources allocated.")


@router.post(
    "/{application_id}/complete",
    summary="Завершить заявку (RESOURCE_ALLOCATION → COMPLETED)",
    dependencies=[Depends(require_permission(Module.ALLOCATION, Action.APPROVE))],
    responses={
        200: success_example({**ITEM, "status": "COMPLETED"}, "Application completed."),
        **COMMON_ERRORS,
    },
)
async def complete_application(
    application_id: int, data: CompleteApplicationDTO, db: DBDep, user: CurrentUserDep
):
    result = await FundService(db).complete(application_id, user, data)
    return ResponseBuilder.success(data=result, message="Application completed.")
