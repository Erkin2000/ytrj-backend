"""Категории продуктов (Фонд): каждый продукт относится к одной категории."""

from fastapi import APIRouter, Depends

from src.common.dependencies import CurrentUserDep, DBDep, require_permission
from src.common.responses.exceptions import (
    ProductCategoryInUseException,
    ProductCategoryNotFoundException,
)
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import (
    COMMON_ERRORS,
    PUBLIC_ERRORS,
    error_examples,
    success_example,
)
from src.product.apis.examples import CATEGORY_EXAMPLE
from src.product.schemas.product_schema import CategoryCreateDTO, CategoryUpdateDTO
from src.product.services.product_service import ProductService
from src.rbac.permissions import Action, Module

router = APIRouter(prefix="/fund/product-categories", tags=["Продукты: категории (Фонд)"])

NOT_FOUND = {404: error_examples(ProductCategoryNotFoundException)}


@router.get(
    "",
    summary="Все категории продуктов (с числом продуктов)",
    description="Без авторизации.",
    responses={200: success_example([CATEGORY_EXAMPLE], "Categories retrieved."), **PUBLIC_ERRORS},
)
async def get_categories(db: DBDep):
    data = await ProductService(db).get_categories()
    return ResponseBuilder.success(data=data, message="Categories retrieved.")


@router.post(
    "",
    status_code=201,
    summary="Создать категорию: название (и описание) на ru / uz / en",
    dependencies=[Depends(require_permission(Module.PRODUCTS, Action.CREATE))],
    responses={
        201: success_example({**CATEGORY_EXAMPLE, "products_count": 0}, "Category created."),
        **COMMON_ERRORS,
    },
)
async def create_category(data: CategoryCreateDTO, db: DBDep, user: CurrentUserDep):
    category = await ProductService(db).create_category(user, data)
    return ResponseBuilder.success(data=category, message="Category created.", status_code=201)


@router.get(
    "/{category_id}",
    summary="Категория по ID",
    description="Без авторизации.",
    responses={
        200: success_example(CATEGORY_EXAMPLE, "Category found."),
        **PUBLIC_ERRORS,
        **NOT_FOUND,
    },
)
async def get_category(category_id: int, db: DBDep):
    category = await ProductService(db).get_category(category_id)
    return ResponseBuilder.success(data=category, message="Category found.")


@router.patch(
    "/{category_id}",
    summary="Изменить переводы, активность или порядок категории",
    description=(
        "Неактивную категорию нельзя выбрать для продукта, а её продукты перестают быть "
        "видны заявителям и не принимают заявки."
    ),
    dependencies=[Depends(require_permission(Module.PRODUCTS, Action.UPDATE))],
    responses={
        200: success_example(CATEGORY_EXAMPLE, "Category updated."),
        **COMMON_ERRORS,
        **NOT_FOUND,
    },
)
async def update_category(
    category_id: int, data: CategoryUpdateDTO, db: DBDep, user: CurrentUserDep
):
    category = await ProductService(db).update_category(user, category_id, data)
    return ResponseBuilder.success(data=category, message="Category updated.")


@router.delete(
    "/{category_id}",
    summary="Удалить категорию без продуктов",
    description="Категорию с продуктами удалить нельзя — деактивируйте её или перенесите продукты.",
    dependencies=[Depends(require_permission(Module.PRODUCTS, Action.DELETE))],
    responses={
        200: success_example(None, "Category deleted."),
        **COMMON_ERRORS,
        **NOT_FOUND,
        409: error_examples(ProductCategoryInUseException),
    },
)
async def delete_category(category_id: int, db: DBDep, user: CurrentUserDep):
    await ProductService(db).delete_category(user, category_id)
    return ResponseBuilder.success(message="Category deleted.")
