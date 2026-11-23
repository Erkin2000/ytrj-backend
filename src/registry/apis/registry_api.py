"""Реестр профинансированных проектов и аналитика отдела финансирования (права registry.*)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from src.common.dependencies import CurrentUserDep, DBDep, PaginationDep, require_permission
from src.common.responses.exceptions import (
    RegistryImportFileException,
    RegistryImportTemplateException,
    RegistryProgramCodeTakenException,
    RegistryProgramInUseException,
    RegistryProgramNotFoundException,
    RegistryProjectNotFoundException,
)
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import (
    COMMON_ERRORS,
    error_examples,
    paginated_example,
    success_example,
)
from src.rbac.permissions import Action, Module
from src.registry.enums import GroupBy
from src.registry.schemas.registry_schema import (
    PROGRAM_TRANSLATIONS_EXAMPLE,
    ProgramCreateDTO,
    ProgramUpdateDTO,
    ProjectCreateDTO,
    ProjectFilterDTO,
    ProjectUpdateDTO,
)
from src.registry.services.registry_service import (
    RegistryAnalyticsService,
    RegistryImportService,
    RegistryProgramService,
    RegistryProjectService,
)

router = APIRouter(prefix="/registry", tags=["Реестр проектов и аналитика"])
FilterDep = Annotated[ProjectFilterDTO, Depends()]


def perm(action: Action):
    return Depends(require_permission(Module.REGISTRY, action))


LABELS = lambda ru, uz, en: [  # noqa: E731
    {"language": "ru", "name": ru},
    {"language": "uz", "name": uz},
    {"language": "en", "name": en},
]
PROGRAM_SHORT = {
    "id": 1,
    "code": "PQ60",
    "kind": "CREDIT",
    "translations": PROGRAM_TRANSLATIONS_EXAMPLE,
}
PROGRAM = {
    **PROGRAM_SHORT,
    "import_template": "PQ60",
    "is_active": True,
    "sort_order": 0,
    "projects_count": 2463,
    "last_import_file": "ЛОЙИҲАЛАР_19_ноябр.xlsx",
    "last_import_at": "2026-11-23T12:00:00Z",
}
PROJECT = {
    "id": 101,
    "program": PROGRAM_SHORT,
    "source": "IMPORT",
    "number": 1,
    "applicant_name": "Yusupov Javohirbek Jasurbek oʻgʻli",
    "organization": None,
    "tin": "50205050005127",
    "subject_type": "INDIVIDUAL",
    "head_info": "Yusupov Javohirbek, AD 0451489, 02.05.2005",
    "gender": "MALE",
    "age": 21,
    "phone": "998905434411",
    "region": {
        "code": "ANDIJAN",
        "translations": LABELS("Андижанская область", "Andijon viloyati", "Andijan region"),
    },
    "district": "Buloqboshi tumani",
    "mahalla": None,
    "purpose": "Milliy shirinliklarni rivojlantirish",
    "sector": "PRODUCTION",
    "direction": "Shirinlik",
    "jobs": 2,
    "project_cost": None,
    "requested_amount": "100000000.00",
    "allocated_amount": "100000000.00",
    "credit_amount": "100000000.00",
    "term_months": 60,
    "collateral": "Sugʻurta",
    "bank": {"code": "AGROBANK", "translations": LABELS("Агробанк", "Agrobank", "Agrobank")},
    "bank_branch": "Agrobank",
    "bank_letter_date": None,
    "bank_request": "09.09.2025 11-1/15/742",
    "order_info": None,
    "application_date": "2025-08-28",
    "decision": "APPROVED",
    "council_protocol": "05.09.2025 6 son",
    "council_date": "2025-09-05",
    "status": "CREDIT_ISSUED",
    "note": None,
    "extra": None,
    "created_by": None,
    "updated_by": None,
    "created_at": "2026-11-23T12:00:00Z",
    "updated_at": "2026-11-23T12:00:00Z",
}
TOTALS = {
    "projects": 2463,
    "requested_amount": "242647562000.00",
    "allocated_count": 2401,
    "allocated_amount": "237191562000.00",
    "credit_count": 2015,
    "credit_amount": "207755701000.00",
    "returned_count": 368,
    "returned_amount": "27811000000.00",
    "jobs": 3647,
}
PROGRAM_NOT_FOUND = {404: error_examples(RegistryProgramNotFoundException)}
PROJECT_NOT_FOUND = {404: error_examples(RegistryProjectNotFoundException)}


# ---------- справочники ----------


@router.get(
    "/dictionaries",
    summary="Справочники реестра: регионы, банки, статусы, отрасли, разрезы аналитики",
    dependencies=[perm(Action.READ)],
    responses={**COMMON_ERRORS},
)
async def get_dictionaries(db: DBDep):
    data = await RegistryAnalyticsService(db).dictionaries()
    return ResponseBuilder.success(data=data, message="Dictionaries retrieved.")


# ---------- программы ----------


@router.get(
    "/programs",
    summary="Программы финансирования (ПҚ-60, ПҚ-400, «Кўмак», …) с числом проектов",
    dependencies=[perm(Action.READ)],
    responses={200: success_example([PROGRAM], "Programs retrieved."), **COMMON_ERRORS},
)
async def get_programs(db: DBDep):
    data = await RegistryProgramService(db).get_list()
    return ResponseBuilder.success(data=data, message="Programs retrieved.")


@router.post(
    "/programs",
    status_code=201,
    summary="Создать программу: код, направление, шаблон импорта, название на ru / uz / en",
    dependencies=[perm(Action.CREATE)],
    responses={
        201: success_example(PROGRAM, "Program created."),
        **COMMON_ERRORS,
        409: error_examples(RegistryProgramCodeTakenException),
    },
)
async def create_program(data: ProgramCreateDTO, db: DBDep):
    program = await RegistryProgramService(db).create(data)
    return ResponseBuilder.success(data=program, message="Program created.", status_code=201)


@router.get(
    "/programs/{program_id}",
    summary="Программа по ID",
    dependencies=[perm(Action.READ)],
    responses={
        200: success_example(PROGRAM, "Program found."),
        **COMMON_ERRORS,
        **PROGRAM_NOT_FOUND,
    },
)
async def get_program(program_id: int, db: DBDep):
    data = await RegistryProgramService(db).get_detail(program_id)
    return ResponseBuilder.success(data=data, message="Program found.")


@router.patch(
    "/programs/{program_id}",
    summary="Изменить программу",
    dependencies=[perm(Action.UPDATE)],
    responses={
        200: success_example(PROGRAM, "Program updated."),
        **COMMON_ERRORS,
        **PROGRAM_NOT_FOUND,
        409: error_examples(RegistryProgramCodeTakenException),
    },
)
async def update_program(program_id: int, data: ProgramUpdateDTO, db: DBDep):
    program = await RegistryProgramService(db).update(program_id, data)
    return ResponseBuilder.success(data=program, message="Program updated.")


@router.delete(
    "/programs/{program_id}",
    summary="Удалить программу без проектов",
    dependencies=[perm(Action.DELETE)],
    responses={
        200: success_example(None, "Program deleted."),
        **COMMON_ERRORS,
        **PROGRAM_NOT_FOUND,
        409: error_examples(RegistryProgramInUseException),
    },
)
async def delete_program(program_id: int, db: DBDep):
    await RegistryProgramService(db).delete(program_id)
    return ResponseBuilder.success(message="Program deleted.")


# ---------- импорт ----------


@router.post(
    "/import",
    summary="Загрузить Excel отдела: проекты программы заменяются данными файла",
    description=(
        "multipart/form-data: `program_id`, `file` (.xlsx, до 30 МБ). Файл разбирается по шаблону "
        "программы (`import_template`): ПҚ-60 — лист «буюртмалар номма ном», ПҚ-400 — «Свод», "
        "«Кўмак» — лист со списком «… рухсат берилган», инкубация — «Svod»; лист ищется по "
        "заголовкам. Все ранее импортированные проекты программы удаляются, созданные вручную "
        "(`source = MANUAL`) остаются. Суммы приводятся к сўм, регионы, туманы и банки — к "
        "справочникам; нераспознанные названия возвращаются в ответе."
    ),
    dependencies=[perm(Action.APPROVE)],
    responses={
        200: success_example(
            {
                "program": PROGRAM_SHORT,
                "file_name": "ЛОЙИҲАЛАР_19_ноябр.xlsx",
                "sheet": "буюртмалар номма ном",
                "imported": 2463,
                "replaced": 2463,
                "skipped": 0,
                "unknown_regions": [],
                "unknown_banks": [],
            },
            "Import completed.",
        ),
        **COMMON_ERRORS,
        400: error_examples(RegistryImportFileException, RegistryImportTemplateException),
        **PROGRAM_NOT_FOUND,
    },
)
async def import_projects(
    db: DBDep,
    user: CurrentUserDep,
    program_id: Annotated[int, Form()],
    file: Annotated[UploadFile, File(description="Excel (.xlsx) отдела финансирования.")],
):
    data = await RegistryImportService(db).import_file(user, program_id, file)
    return ResponseBuilder.success(data=data, message="Import completed.")


# ---------- проекты ----------


@router.get(
    "/projects",
    summary="Проекты реестра: фильтры, поиск, постранично",
    dependencies=[perm(Action.READ)],
    responses={200: paginated_example(PROJECT, "Projects retrieved."), **COMMON_ERRORS},
)
async def get_projects(db: DBDep, filters: FilterDep, pagination: PaginationDep):
    data = await RegistryProjectService(db).get_page(filters, pagination.page, pagination.per_page)
    return ResponseBuilder.success(data=data, message="Projects retrieved.")


@router.post(
    "/projects",
    status_code=201,
    summary="Добавить проект вручную",
    dependencies=[perm(Action.CREATE)],
    responses={
        201: success_example(PROJECT, "Project created."),
        **COMMON_ERRORS,
        **PROGRAM_NOT_FOUND,
    },
)
async def create_project(data: ProjectCreateDTO, db: DBDep, user: CurrentUserDep):
    project = await RegistryProjectService(db).create(user, data)
    return ResponseBuilder.success(data=project, message="Project created.", status_code=201)


@router.get(
    "/projects/{project_id}",
    summary="Проект по ID",
    dependencies=[perm(Action.READ)],
    responses={
        200: success_example(PROJECT, "Project found."),
        **COMMON_ERRORS,
        **PROJECT_NOT_FOUND,
    },
)
async def get_project(project_id: int, db: DBDep):
    data = await RegistryProjectService(db).get_detail(project_id)
    return ResponseBuilder.success(data=data, message="Project found.")


@router.patch(
    "/projects/{project_id}",
    summary="Изменить проект",
    description=(
        "Передаются только изменяемые поля. Проект из импорта тоже можно править, но следующий "
        "импорт программы заменит его данными файла."
    ),
    dependencies=[perm(Action.UPDATE)],
    responses={
        200: success_example(PROJECT, "Project updated."),
        **COMMON_ERRORS,
        **PROJECT_NOT_FOUND,
    },
)
async def update_project(project_id: int, data: ProjectUpdateDTO, db: DBDep, user: CurrentUserDep):
    project = await RegistryProjectService(db).update(user, project_id, data)
    return ResponseBuilder.success(data=project, message="Project updated.")


@router.delete(
    "/projects/{project_id}",
    summary="Удалить проект",
    dependencies=[perm(Action.DELETE)],
    responses={
        200: success_example(None, "Project deleted."),
        **COMMON_ERRORS,
        **PROJECT_NOT_FOUND,
    },
)
async def delete_project(project_id: int, db: DBDep):
    await RegistryProjectService(db).delete(project_id)
    return ResponseBuilder.success(message="Project deleted.")


# ---------- аналитика ----------


@router.get(
    "/analytics/summary",
    summary="Итоги: проекты, запрошено, выделено, выдано, возвраты, рабочие места",
    description="Те же фильтры, что у списка проектов. Суммы — в сўм.",
    dependencies=[perm(Action.READ)],
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
        **COMMON_ERRORS,
    },
)
async def get_summary(db: DBDep, filters: FilterDep):
    data = await RegistryAnalyticsService(db).summary(filters)
    return ResponseBuilder.success(data=data, message="Summary retrieved.")


@router.get(
    "/analytics/breakdown",
    summary="Разрез: по программе, региону, туману, банку, отрасли, полу, статусу, году, месяцу",
    description=(
        "`group_by` — разрез; фильтры — как у списка проектов (например, `region=ANDIJAN&"
        "group_by=district` — туманы области). Строки отсортированы по выделенной сумме, "
        "год и месяц — по возрастанию. `total` — итог по тем же фильтрам."
    ),
    dependencies=[perm(Action.READ)],
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
        **COMMON_ERRORS,
    },
)
async def get_breakdown(
    db: DBDep,
    filters: FilterDep,
    group_by: Annotated[GroupBy, Query(description="Разрез аналитики.")],
):
    data = await RegistryAnalyticsService(db).breakdown(group_by, filters)
    return ResponseBuilder.success(data=data, message="Breakdown retrieved.")
