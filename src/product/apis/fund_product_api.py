"""Продукты Фонда: создание, этапы, поля анкеты, варианты ответа, условия показа, публикация."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends

from src.common.dependencies import CurrentUserDep, DBDep, PaginationDep, require_permission
from src.common.responses.exceptions import (
    BankNotFoundException,
    FieldConditionException,
    FieldInUseByConditionException,
    FieldOptionsException,
    ProductCategoryInactiveException,
    ProductCategoryNotFoundException,
    ProductFieldNotFoundException,
    ProductFieldOptionNotFoundException,
    ProductInUseException,
    ProductLockedException,
    ProductNotFoundException,
    ProductNotReadyException,
    ProductStageNotFoundException,
    ProductStatusException,
    StageNumberTakenException,
)
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import (
    COMMON_ERRORS,
    PUBLIC_ERRORS,
    error_examples,
    paginated_example,
    success_example,
)
from src.product.apis.examples import (
    FIELD_CREATE_EXAMPLES,
    FIELD_UPDATE_EXAMPLES,
    OPTION_CREATE_EXAMPLES,
    PRODUCT_DETAIL_EXAMPLE,
    PRODUCT_EXAMPLE,
    STAGE_CREATE_EXAMPLES,
)
from src.product.schemas.product_schema import (
    FieldCreateDTO,
    FieldUpdateDTO,
    OptionCreateDTO,
    OptionUpdateDTO,
    ProductCreateDTO,
    ProductFilterDTO,
    ProductUpdateDTO,
    StageCreateDTO,
    StageUpdateDTO,
)
from src.product.services.product_service import ProductService
from src.rbac.permissions import Action, Module

router = APIRouter(prefix="/fund/products", tags=["Продукты: управление (Фонд)"])

FilterDep = Annotated[ProductFilterDTO, Depends()]
StageCreateBody = Annotated[StageCreateDTO, Body(openapi_examples=STAGE_CREATE_EXAMPLES)]
FieldCreateBody = Annotated[FieldCreateDTO, Body(openapi_examples=FIELD_CREATE_EXAMPLES)]
FieldUpdateBody = Annotated[FieldUpdateDTO, Body(openapi_examples=FIELD_UPDATE_EXAMPLES)]
OptionCreateBody = Annotated[OptionCreateDTO, Body(openapi_examples=OPTION_CREATE_EXAMPLES)]

create_dep = Depends(require_permission(Module.PRODUCTS, Action.CREATE))
read_dep = Depends(require_permission(Module.PRODUCTS, Action.READ))
update_dep = Depends(require_permission(Module.PRODUCTS, Action.UPDATE))
delete_dep = Depends(require_permission(Module.PRODUCTS, Action.DELETE))
approve_dep = Depends(require_permission(Module.PRODUCTS, Action.APPROVE))

DRAFT_EXAMPLE = {**PRODUCT_DETAIL_EXAMPLE, "status": "DRAFT"}
NOT_FOUND = {404: error_examples(ProductNotFoundException)}
STAGE_NOT_FOUND = {404: error_examples(ProductNotFoundException, ProductStageNotFoundException)}
FIELD_NOT_FOUND = {404: error_examples(ProductNotFoundException, ProductFieldNotFoundException)}
OPTION_NOT_FOUND = {
    404: error_examples(ProductNotFoundException, ProductFieldOptionNotFoundException)
}
LOCKED = {409: error_examples(ProductLockedException)}
CONDITION = {400: error_examples(FieldConditionException)}
IN_USE = {409: error_examples(ProductLockedException, FieldInUseByConditionException)}

STRUCTURE_NOTE = (
    "Возвращает продукт целиком. Если по продукту уже есть заявки, этапы и поля менять нельзя "
    "(`product_locked`): скопируйте продукт (`POST /fund/products/{id}/copy`)."
)
CONDITION_NOTE = (
    "`visible_when` — условие показа: поле SELECT / RADIO / CHECKBOX, расположенное раньше в "
    "анкете, и его варианты; иначе 400 `field_condition`. `null` — показывать всегда."
)


@router.get(
    "",
    summary="Все продукты (фильтр по статусу и категории, поиск по названию)",
    description="Без авторизации.",
    responses={200: paginated_example(PRODUCT_EXAMPLE, "Products retrieved."), **PUBLIC_ERRORS},
)
async def get_products(db: DBDep, pagination: PaginationDep, filters: FilterDep):
    data = await ProductService(db).get_page(filters, pagination.page, pagination.per_page)
    return ResponseBuilder.success(data=data, message="Products retrieved.")


@router.post(
    "",
    status_code=201,
    summary="Создать продукт (черновик): категория, названия, описания, типы субъекта, сроки, банки",
    description="`category_id` обязателен: активная категория из `GET /fund/product-categories`.",
    dependencies=[create_dep],
    responses={
        201: success_example({**DRAFT_EXAMPLE, "stages": []}, "Product created."),
        **COMMON_ERRORS,
        400: error_examples(ProductCategoryInactiveException),
        404: error_examples(ProductCategoryNotFoundException, BankNotFoundException),
    },
)
async def create_product(data: ProductCreateDTO, db: DBDep, user: CurrentUserDep):
    product = await ProductService(db).create(user, data)
    return ResponseBuilder.success(data=product, message="Product created.", status_code=201)


@router.get(
    "/{product_id}",
    summary="Продукт с банками, этапами и полями",
    description="Без авторизации.",
    responses={
        200: success_example(PRODUCT_DETAIL_EXAMPLE, "Product found."),
        **PUBLIC_ERRORS,
        **NOT_FOUND,
    },
)
async def get_product(product_id: int, db: DBDep):
    product = await ProductService(db).get_detail(product_id)
    return ResponseBuilder.success(data=product, message="Product found.")


@router.patch(
    "/{product_id}",
    summary="Изменить категорию, названия, описания, типы субъекта, сроки приёма или банки",
    description=(
        "Передаются только изменяемые поля. `bank_ids` заменяет список банков целиком. "
        "Разрешено и при наличии заявок."
    ),
    dependencies=[update_dep],
    responses={
        200: success_example(PRODUCT_DETAIL_EXAMPLE, "Product updated."),
        **COMMON_ERRORS,
        400: error_examples(ProductStatusException, ProductCategoryInactiveException),
        404: error_examples(
            ProductNotFoundException, ProductCategoryNotFoundException, BankNotFoundException
        ),
    },
)
async def update_product(product_id: int, data: ProductUpdateDTO, db: DBDep, user: CurrentUserDep):
    product = await ProductService(db).update(user, product_id, data)
    return ResponseBuilder.success(data=product, message="Product updated.")


@router.delete(
    "/{product_id}",
    summary="Удалить продукт без заявок",
    description="Продукт с заявками удалить нельзя — снимите его с публикации (`archive`).",
    dependencies=[delete_dep],
    responses={
        200: success_example(None, "Product deleted."),
        **COMMON_ERRORS,
        **NOT_FOUND,
        409: error_examples(ProductInUseException),
    },
)
async def delete_product(product_id: int, db: DBDep, user: CurrentUserDep):
    await ProductService(db).delete(user, product_id)
    return ResponseBuilder.success(message="Product deleted.")


@router.post(
    "/{product_id}/publish",
    summary="Опубликовать продукт (DRAFT / ARCHIVED → PUBLISHED)",
    description=(
        "Нужны хотя бы один этап, хотя бы одно поле в каждом этапе и не меньше двух вариантов "
        "у каждого поля SELECT / RADIO / CHECKBOX; если банки указаны — хотя бы один активный. "
        "Продукт без банков: заявитель банк не выбирает, утверждение Советом завершает заявку. "
        "Заявители видят продукт в сроках приёма."
    ),
    dependencies=[approve_dep],
    responses={
        200: success_example(PRODUCT_DETAIL_EXAMPLE, "Product published."),
        **COMMON_ERRORS,
        400: error_examples(ProductNotReadyException, ProductStatusException),
        **NOT_FOUND,
    },
)
async def publish_product(product_id: int, db: DBDep, user: CurrentUserDep):
    product = await ProductService(db).publish(user, product_id)
    return ResponseBuilder.success(data=product, message="Product published.")


@router.post(
    "/{product_id}/archive",
    summary="Снять продукт с публикации (PUBLISHED → ARCHIVED)",
    description="Новые заявки не принимаются, черновики по продукту отправить нельзя.",
    dependencies=[approve_dep],
    responses={
        200: success_example({**PRODUCT_DETAIL_EXAMPLE, "status": "ARCHIVED"}, "Product archived."),
        **COMMON_ERRORS,
        400: error_examples(ProductStatusException),
        **NOT_FOUND,
    },
)
async def archive_product(product_id: int, db: DBDep, user: CurrentUserDep):
    product = await ProductService(db).archive(user, product_id)
    return ResponseBuilder.success(data=product, message="Product archived.")


@router.post(
    "/{product_id}/copy",
    status_code=201,
    summary="Скопировать продукт в новый черновик (с банками, этапами, полями, вариантами и условиями)",
    dependencies=[create_dep],
    responses={
        201: success_example({**DRAFT_EXAMPLE, "copied_from_id": 3, "id": 4}, "Product copied."),
        **COMMON_ERRORS,
        **NOT_FOUND,
    },
)
async def copy_product(product_id: int, db: DBDep, user: CurrentUserDep):
    product = await ProductService(db).copy(user, product_id)
    return ResponseBuilder.success(data=product, message="Product copied.", status_code=201)


# ---------- этапы ----------


@router.post(
    "/{product_id}/stages",
    status_code=201,
    summary="Добавить этап: номер, название на трёх языках, условие показа",
    description=STRUCTURE_NOTE + " " + CONDITION_NOTE,
    dependencies=[update_dep],
    responses={
        201: success_example(DRAFT_EXAMPLE, "Stage added."),
        **COMMON_ERRORS,
        **CONDITION,
        **NOT_FOUND,
        409: error_examples(ProductLockedException, StageNumberTakenException),
    },
)
async def add_stage(product_id: int, data: StageCreateBody, db: DBDep, user: CurrentUserDep):
    product = await ProductService(db).add_stage(user, product_id, data)
    return ResponseBuilder.success(data=product, message="Stage added.", status_code=201)


@router.patch(
    "/{product_id}/stages/{stage_id}",
    summary="Изменить номер, название или условие показа этапа",
    description=STRUCTURE_NOTE + " " + CONDITION_NOTE,
    dependencies=[update_dep],
    responses={
        200: success_example(DRAFT_EXAMPLE, "Stage updated."),
        **COMMON_ERRORS,
        **CONDITION,
        **STAGE_NOT_FOUND,
        409: error_examples(ProductLockedException, StageNumberTakenException),
    },
)
async def update_stage(
    product_id: int, stage_id: int, data: StageUpdateDTO, db: DBDep, user: CurrentUserDep
):
    product = await ProductService(db).update_stage(user, product_id, stage_id, data)
    return ResponseBuilder.success(data=product, message="Stage updated.")


@router.delete(
    "/{product_id}/stages/{stage_id}",
    summary="Удалить этап вместе с его полями",
    description=(
        STRUCTURE_NOTE + " Если поля этапа управляют показом других этапов или полей — "
        "409 `field_in_use_by_condition`: сначала снимите эти условия."
    ),
    dependencies=[update_dep],
    responses={
        200: success_example(DRAFT_EXAMPLE, "Stage deleted."),
        **COMMON_ERRORS,
        **STAGE_NOT_FOUND,
        **IN_USE,
    },
)
async def delete_stage(product_id: int, stage_id: int, db: DBDep, user: CurrentUserDep):
    product = await ProductService(db).delete_stage(user, product_id, stage_id)
    return ResponseBuilder.success(data=product, message="Stage deleted.")


# ---------- поля ----------


@router.post(
    "/{product_id}/stages/{stage_id}/fields",
    status_code=201,
    summary="Добавить поле в этап: тип, название на трёх языках, обязательность, варианты, условие",
    description=(
        "Типы: STRING (текст), NUMBER (число), DATE (дата), PHONE (+998XXXXXXXXX), EMAIL, "
        "PHOTO (JPG/PNG/WEBP), FILE (PDF/DOCX), SELECT / RADIO (один вариант из списка), "
        "CHECKBOX (несколько вариантов). `max_files` — только для PHOTO и FILE. "
        "`options` (2–50 вариантов с названиями на трёх языках) — только для SELECT / RADIO / "
        "CHECKBOX и обязательны для них. Справочник типов с их атрибутами (`has_options`, "
        "`multiple`, `min_options` / `max_options`) — `GET /products/field-types`. "
        "Готовые тела запросов для каждого типа — в списке примеров. "
        + CONDITION_NOTE
        + " "
        + STRUCTURE_NOTE
    ),
    dependencies=[update_dep],
    responses={
        201: success_example(DRAFT_EXAMPLE, "Field added."),
        **COMMON_ERRORS,
        **CONDITION,
        **STAGE_NOT_FOUND,
        **LOCKED,
    },
)
async def add_field(
    product_id: int, stage_id: int, data: FieldCreateBody, db: DBDep, user: CurrentUserDep
):
    product = await ProductService(db).add_field(user, product_id, stage_id, data)
    return ResponseBuilder.success(data=product, message="Field added.", status_code=201)


@router.patch(
    "/{product_id}/fields/{field_id}",
    summary="Изменить поле: тип, название, обязательность, лимит файлов, порядок, условие показа",
    description=(
        "Смена типа между SELECT / RADIO / CHECKBOX сохраняет варианты. Смена на тип без "
        "вариантов удаляет их; если поле управляет показом других полей или этапов — "
        "409 `field_in_use_by_condition`. " + CONDITION_NOTE + " " + STRUCTURE_NOTE
    ),
    dependencies=[update_dep],
    responses={
        200: success_example(DRAFT_EXAMPLE, "Field updated."),
        **COMMON_ERRORS,
        **CONDITION,
        **FIELD_NOT_FOUND,
        **IN_USE,
    },
)
async def update_field(
    product_id: int, field_id: int, data: FieldUpdateBody, db: DBDep, user: CurrentUserDep
):
    product = await ProductService(db).update_field(user, product_id, field_id, data)
    return ResponseBuilder.success(data=product, message="Field updated.")


@router.delete(
    "/{product_id}/fields/{field_id}",
    summary="Удалить поле",
    description=(
        STRUCTURE_NOTE + " Если поле управляет показом других полей или этапов — "
        "409 `field_in_use_by_condition`: сначала снимите эти условия."
    ),
    dependencies=[update_dep],
    responses={
        200: success_example(DRAFT_EXAMPLE, "Field deleted."),
        **COMMON_ERRORS,
        **FIELD_NOT_FOUND,
        **IN_USE,
    },
)
async def delete_field(product_id: int, field_id: int, db: DBDep, user: CurrentUserDep):
    product = await ProductService(db).delete_field(user, product_id, field_id)
    return ResponseBuilder.success(data=product, message="Field deleted.")


# ---------- варианты ответа ----------


@router.post(
    "/{product_id}/fields/{field_id}/options",
    status_code=201,
    summary="Добавить вариант ответа в поле SELECT / RADIO / CHECKBOX",
    description=(
        "Название на трёх языках и порядок. Для других типов полей — 400 `field_options`. "
        + STRUCTURE_NOTE
    ),
    dependencies=[update_dep],
    responses={
        201: success_example(DRAFT_EXAMPLE, "Option added."),
        **COMMON_ERRORS,
        400: error_examples(FieldOptionsException),
        **FIELD_NOT_FOUND,
        **LOCKED,
    },
)
async def add_option(
    product_id: int, field_id: int, data: OptionCreateBody, db: DBDep, user: CurrentUserDep
):
    product = await ProductService(db).add_option(user, product_id, field_id, data)
    return ResponseBuilder.success(data=product, message="Option added.", status_code=201)


@router.patch(
    "/{product_id}/options/{option_id}",
    summary="Изменить название или порядок варианта ответа",
    description=STRUCTURE_NOTE,
    dependencies=[update_dep],
    responses={
        200: success_example(DRAFT_EXAMPLE, "Option updated."),
        **COMMON_ERRORS,
        **OPTION_NOT_FOUND,
        **LOCKED,
    },
)
async def update_option(
    product_id: int, option_id: int, data: OptionUpdateDTO, db: DBDep, user: CurrentUserDep
):
    product = await ProductService(db).update_option(user, product_id, option_id, data)
    return ResponseBuilder.success(data=product, message="Option updated.")


@router.delete(
    "/{product_id}/options/{option_id}",
    summary="Удалить вариант ответа",
    description=(
        STRUCTURE_NOTE + " Если вариант используется в условии показа — "
        "409 `field_in_use_by_condition`: сначала снимите это условие."
    ),
    dependencies=[update_dep],
    responses={
        200: success_example(DRAFT_EXAMPLE, "Option deleted."),
        **COMMON_ERRORS,
        **OPTION_NOT_FOUND,
        **IN_USE,
    },
)
async def delete_option(product_id: int, option_id: int, db: DBDep, user: CurrentUserDep):
    product = await ProductService(db).delete_option(user, product_id, option_id)
    return ResponseBuilder.success(data=product, message="Option deleted.")
