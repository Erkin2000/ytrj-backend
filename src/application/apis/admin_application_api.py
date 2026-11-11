"""Действия Super Admin над заявками."""

from fastapi import APIRouter, Depends

from src.application.services.purge_service import ApplicationPurgeService
from src.common.dependencies import DBDep, require_superuser
from src.common.responses.exceptions import ApplicationNotFoundException
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import COMMON_ERRORS, error_examples, success_example

router = APIRouter(prefix="/admin/applications", tags=["Заявки: Super Admin"])


@router.delete(
    "/{application_id}",
    summary="Удалить заявку целиком, в любом статусе (только Super Admin)",
    description=(
        "Удаляет заявку и всё связанное: историю статусов, скоринг, решения Фонда, Совета и "
        "банка, ответы анкеты, файлы на диске, документ-требование. Действие необратимо, "
        "запись об удалении не сохраняется."
    ),
    dependencies=[Depends(require_superuser)],
    responses={
        200: success_example(None, "Application deleted."),
        **COMMON_ERRORS,
        404: error_examples(ApplicationNotFoundException),
    },
)
async def delete_application(application_id: int, db: DBDep):
    await ApplicationPurgeService(db).purge(application_id)
    return ResponseBuilder.success(message="Application deleted.")
