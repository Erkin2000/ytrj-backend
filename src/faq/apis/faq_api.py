"""FAQ сайта: публичный список и ведение вопросов отделом маркетинга."""

from fastapi import APIRouter, Depends

from src.common.dependencies import CurrentUserDep, DBDep, require_permission
from src.common.responses.exceptions import FaqNotFoundException
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import (
    COMMON_ERRORS,
    PUBLIC_ERRORS,
    error_examples,
    success_example,
)
from src.faq.schemas.faq_schema import FAQ_TRANSLATIONS_EXAMPLE, FaqCreateDTO, FaqUpdateDTO
from src.faq.services.faq_service import FaqService
from src.rbac.permissions import Action, Module

PUBLIC_EXAMPLE = {"id": 1, "translations": FAQ_TRANSLATIONS_EXAMPLE, "sort_order": 0}
FAQ_EXAMPLE = {
    **PUBLIC_EXAMPLE,
    "is_active": True,
    "created_by": {"id": 12, "full_name": "Marketing Operator", "username": "marketing1"},
    "updated_by": {"id": 12, "full_name": "Marketing Operator", "username": "marketing1"},
    "created_at": "2026-11-20T09:00:00Z",
    "updated_at": "2026-11-20T09:00:00Z",
}
NOT_FOUND = {404: error_examples(FaqNotFoundException)}

public_router = APIRouter(prefix="/faq", tags=["FAQ: сайт"])
router = APIRouter(prefix="/marketing/faq", tags=["FAQ: управление (маркетинг)"])


@public_router.get(
    "",
    summary="Вопросы и ответы для сайта (только активные)",
    description="Без авторизации. Порядок — по `sort_order`, затем по `id`. Переводы ru / uz / en.",
    responses={200: success_example([PUBLIC_EXAMPLE], "FAQ retrieved."), **PUBLIC_ERRORS},
)
async def get_public_faq(db: DBDep):
    data = await FaqService(db).get_public_list()
    return ResponseBuilder.success(data=data, message="FAQ retrieved.")


@router.get(
    "",
    summary="Все вопросы, включая неактивные",
    dependencies=[Depends(require_permission(Module.FAQ, Action.READ))],
    responses={200: success_example([FAQ_EXAMPLE], "FAQ retrieved."), **COMMON_ERRORS},
)
async def get_faq_list(db: DBDep):
    data = await FaqService(db).get_list()
    return ResponseBuilder.success(data=data, message="FAQ retrieved.")


@router.post(
    "",
    status_code=201,
    summary="Создать вопрос: вопрос и ответ на ru / uz / en",
    dependencies=[Depends(require_permission(Module.FAQ, Action.CREATE))],
    responses={201: success_example(FAQ_EXAMPLE, "FAQ created."), **COMMON_ERRORS},
)
async def create_faq(data: FaqCreateDTO, db: DBDep, user: CurrentUserDep):
    faq = await FaqService(db).create(user, data)
    return ResponseBuilder.success(data=faq, message="FAQ created.", status_code=201)


@router.get(
    "/{faq_id}",
    summary="Вопрос по ID",
    dependencies=[Depends(require_permission(Module.FAQ, Action.READ))],
    responses={200: success_example(FAQ_EXAMPLE, "FAQ found."), **COMMON_ERRORS, **NOT_FOUND},
)
async def get_faq(faq_id: int, db: DBDep):
    faq = await FaqService(db).get_detail(faq_id)
    return ResponseBuilder.success(data=faq, message="FAQ found.")


@router.patch(
    "/{faq_id}",
    summary="Изменить переводы, активность или порядок вопроса",
    dependencies=[Depends(require_permission(Module.FAQ, Action.UPDATE))],
    responses={200: success_example(FAQ_EXAMPLE, "FAQ updated."), **COMMON_ERRORS, **NOT_FOUND},
)
async def update_faq(faq_id: int, data: FaqUpdateDTO, db: DBDep, user: CurrentUserDep):
    faq = await FaqService(db).update(user, faq_id, data)
    return ResponseBuilder.success(data=faq, message="FAQ updated.")


@router.delete(
    "/{faq_id}",
    summary="Удалить вопрос",
    description="Чтобы временно скрыть вопрос с сайта, достаточно `is_active=false`.",
    dependencies=[Depends(require_permission(Module.FAQ, Action.DELETE))],
    responses={200: success_example(None, "FAQ deleted."), **COMMON_ERRORS, **NOT_FOUND},
)
async def delete_faq(faq_id: int, db: DBDep):
    await FaqService(db).delete(faq_id)
    return ResponseBuilder.success(message="FAQ deleted.")
