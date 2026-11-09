"""Каталог продуктов для заявителя: только опубликованные и принимающие заявки."""

from fastapi import APIRouter, Depends, Query

from src.application.enums import SubjectType
from src.common.dependencies import DBDep, require_permission
from src.common.responses.exceptions import ProductNotFoundException
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import READ_ERRORS, error_examples, success_example
from src.product.apis.examples import FIELD_TYPES_EXAMPLE, PRODUCT_DETAIL_EXAMPLE, PRODUCT_EXAMPLE
from src.product.field_types import field_types
from src.product.services.product_service import ProductService
from src.rbac.permissions import Action, Module

router = APIRouter(prefix="/products", tags=["Продукты: каталог заявителя"])

read_dep = Depends(require_permission(Module.PRODUCTS, Action.READ))


@router.get(
    "/field-types",
    summary="Типы полей анкеты: названия на ru/uz/en и правила заполнения",
    description=(
        "Справочник для конструктора продукта (Фонд) и формы заявки (заявитель): какие типы "
        "полей можно добавить в этап, как их заполнять и какие ограничения у файлов. "
        "Значения `type` передаются в `field_type` при создании поля."
    ),
    dependencies=[read_dep],
    responses={200: success_example(FIELD_TYPES_EXAMPLE, "Field types retrieved."), **READ_ERRORS},
)
async def get_field_types():
    return ResponseBuilder.success(data=field_types(), message="Field types retrieved.")


@router.get(
    "",
    summary="Продукты, по которым сейчас принимаются заявки",
    description=(
        "Опубликованные продукты в сроках приёма. С `subject_type` — только продукты для этого "
        "типа субъекта. В `banks` — только активные банки продукта."
    ),
    dependencies=[read_dep],
    responses={200: success_example([PRODUCT_EXAMPLE], "Products retrieved."), **READ_ERRORS},
)
async def get_available_products(
    db: DBDep,
    subject_type: SubjectType | None = Query(
        None, description="Тип субъекта: YATT, MCHJ, SELF_EMPLOYED"
    ),
):
    data = await ProductService(db).get_available(subject_type)
    return ResponseBuilder.success(data=data, message="Products retrieved.")


@router.get(
    "/{product_id}",
    summary="Продукт с этапами и полями анкеты",
    dependencies=[read_dep],
    responses={
        200: success_example(PRODUCT_DETAIL_EXAMPLE, "Product found."),
        **READ_ERRORS,
        404: error_examples(ProductNotFoundException),
    },
)
async def get_available_product(product_id: int, db: DBDep):
    data = await ProductService(db).get_available_detail(product_id)
    return ResponseBuilder.success(data=data, message="Product found.")
