"""Аналитика реестра для сайта — без токена, только GET.

Отдаются только агрегаты по активным программам: итоги и разрезы. Список проектов,
имена, ПИНФЛ, телефоны и поиск сюда не попадают (они — в `/registry/...` с правами).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.common.dependencies import DBDep
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import PUBLIC_ERRORS, success_example
from src.registry.apis.registry_api import LABELS, PROGRAM_SHORT, TOTALS
from src.registry.enums import GroupBy
from src.registry.schemas.registry_schema import PublicAnalyticsFilterDTO
from src.registry.services.registry_service import PublicAnalyticsService

router = APIRouter(prefix="/public/analytics", tags=["Аналитика: сайт"])
FilterDep = Annotated[PublicAnalyticsFilterDTO, Depends()]

SCOPE_NOTE = "Без авторизации. Только активные программы; суммы — в сўм."


@router.get(
    "/programs",
    summary="Программы финансирования для сайта: название, число проектов, дата обновления",
    description=SCOPE_NOTE,
    responses={
        200: success_example(
            [{**PROGRAM_SHORT, "projects_count": 2463, "last_import_at": "2026-11-23T12:00:00Z"}],
            "Programs retrieved.",
        ),
        **PUBLIC_ERRORS,
    },
)
async def get_public_programs(db: DBDep):
    data = await PublicAnalyticsService(db).programs()
    return ResponseBuilder.success(data=data, message="Programs retrieved.")


@router.get(
    "/dictionaries",
    summary="Справочники для фильтров: регионы, банки, отрасли, статусы, разрезы",
    description="Без авторизации.",
    responses={**PUBLIC_ERRORS},
)
async def get_public_dictionaries(db: DBDep):
    data = await PublicAnalyticsService(db).dictionaries()
    return ResponseBuilder.success(data=data, message="Dictionaries retrieved.")


@router.get(
    "/summary",
    summary="Итоги для сайта: проекты, запрошено, выделено, выдано, возвраты, рабочие места",
    description=SCOPE_NOTE
    + " Фильтры — программа, регион, туман, банк, отрасль, пол, год, период.",
    responses={
        200: success_example(
            {
                **TOTALS,
                "average_allocated": "98788655.56",
                "by_gender": {"MALE": 1351, "FEMALE": 1112},
                "by_subject_type": {
                    "INDIVIDUAL": 1581,
                    "SOLE_PROPRIETOR": 705,
                    "LEGAL_ENTITY": 177,
                },
                "by_status": {"CREDIT_ISSUED": 2015, "RETURNED": 368},
                "date_min": "2025-09-05",
                "date_max": "2026-11-10",
            },
            "Summary retrieved.",
        ),
        **PUBLIC_ERRORS,
    },
)
async def get_public_summary(db: DBDep, filters: FilterDep):
    data = await PublicAnalyticsService(db).summary(filters)
    return ResponseBuilder.success(data=data, message="Summary retrieved.")


@router.get(
    "/breakdown",
    summary="Разрез для сайта: по программе, региону, туману, банку, отрасли, полу, году, месяцу",
    description=(
        SCOPE_NOTE + " `group_by` — разрез, например `region` для карты или `month` для графика; "
        "`region=ANDIJAN&group_by=district` — туманы области."
    ),
    responses={
        200: success_example(
            {
                "group_by": "region",
                "rows": [
                    {
                        "key": "KHOREZM",
                        "translations": LABELS(
                            "Хорезмская область", "Xorazm viloyati", "Khorezm region"
                        ),
                        **TOTALS,
                    }
                ],
                "total": TOTALS,
            },
            "Breakdown retrieved.",
        ),
        **PUBLIC_ERRORS,
    },
)
async def get_public_breakdown(
    db: DBDep,
    filters: FilterDep,
    group_by: Annotated[GroupBy, Query(description="Разрез аналитики.")],
):
    data = await PublicAnalyticsService(db).breakdown(group_by, filters)
    return ResponseBuilder.success(data=data, message="Breakdown retrieved.")
