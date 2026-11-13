"""Условия показа этапов и полей анкеты продукта: проверка целостности.

Правило одно: этап или поле видны, если в управляющем поле (SELECT / RADIO /
CHECKBOX), расположенном раньше в анкете, выбран хотя бы один из указанных
вариантов. «Раньше» — более ранний этап (меньший `number`) либо, для поля,
то же самое поле выше по `(sort_order, id)` в том же этапе. Благодаря этому
циклов быть не может, а при заполнении управляющее поле уже отвечено.

Проверка запускается после каждого изменения структуры продукта, поэтому
перенумерация этапов или перестановка полей не могут сломать условия.
"""

from src.common.responses.exceptions import FieldConditionException
from src.product.enums import CHOICE_FIELD_TYPES
from src.product.models.product_model import ProductFieldORM, ProductORM, ProductStageORM


def field_position(stage: ProductStageORM, field: ProductFieldORM) -> tuple[int, int, int]:
    """Позиция поля в анкете: (номер этапа, порядок, id)."""
    return (stage.number, field.sort_order, field.id)


def controllers(product: ProductORM) -> dict[int, tuple[ProductStageORM, ProductFieldORM]]:
    """Поля с вариантами ответа продукта: id → (этап, поле)."""
    return {
        field.id: (stage, field)
        for stage in product.stages
        for field in stage.fields
        if field.field_type in CHOICE_FIELD_TYPES
    }


def dependents(product: ProductORM, field_id: int) -> list[str]:
    """Что зависит от поля: ключи `stages.<номер>` и `fields.<id>`."""
    found: list[str] = []
    for stage in product.stages:
        if stage.condition_field_id == field_id:
            found.append(f"stages.{stage.number}")
        found.extend(
            f"fields.{field.id}" for field in stage.fields if field.condition_field_id == field_id
        )
    return found


def option_dependents(product: ProductORM, option_id: int) -> list[str]:
    """Что зависит от варианта ответа: ключи `stages.<номер>` и `fields.<id>`."""
    found: list[str] = []
    for stage in product.stages:
        if option_id in (stage.condition_option_ids or []):
            found.append(f"stages.{stage.number}")
        found.extend(
            f"fields.{field.id}"
            for field in stage.fields
            if option_id in (field.condition_option_ids or [])
        )
    return found


def _check_rule(
    key: str,
    condition_field_id: int | None,
    condition_option_ids: list[int] | None,
    target_position: tuple[int, int, int] | None,
    target_stage_number: int,
    choice_fields: dict[int, tuple[ProductStageORM, ProductFieldORM]],
    errors: list[dict],
) -> None:
    if condition_field_id is None and not condition_option_ids:
        return
    if condition_field_id is None or not condition_option_ids:
        errors.append({"field": key, "message": "Both field_id and option_ids are required"})
        return
    controller = choice_fields.get(condition_field_id)
    if controller is None:
        errors.append(
            {
                "field": key,
                "message": "Controlling field must be a SELECT, RADIO or CHECKBOX field "
                "of this product",
            }
        )
        return
    controller_stage, controller_field = controller
    if target_position is None:
        earlier = controller_stage.number < target_stage_number
    else:
        earlier = field_position(controller_stage, controller_field) < target_position
    if not earlier:
        errors.append(
            {
                "field": key,
                "message": "Controlling field must be placed earlier in the form "
                "(an earlier stage, or the same stage above this field)",
            }
        )
        return
    known = {option.id for option in controller_field.options}
    unknown = sorted(set(condition_option_ids) - known)
    if unknown:
        errors.append(
            {
                "field": key,
                "message": "Options do not belong to the controlling field: "
                + ", ".join(map(str, unknown)),
            }
        )


def precheck_condition(product: ProductORM, visible_when, key: str) -> None:
    """Проверка ссылок условия до записи в БД (поле и варианты существуют в продукте);
    порядок расположения проверяет `validate_conditions` после сохранения."""
    if visible_when is None:
        return
    errors: list[dict] = []
    _check_rule(
        key,
        visible_when.field_id,
        list(visible_when.option_ids),
        None,
        10**9,  # порядок здесь не проверяется
        controllers(product),
        errors,
    )
    if errors:
        raise FieldConditionException(errors=errors)


def validate_conditions(product: ProductORM) -> None:
    """Проверяет все условия показа продукта; бросает `FieldConditionException`."""
    choice_fields = controllers(product)
    errors: list[dict] = []
    for stage in product.stages:
        _check_rule(
            f"stages.{stage.number}.visible_when",
            stage.condition_field_id,
            stage.condition_option_ids,
            None,
            stage.number,
            choice_fields,
            errors,
        )
        for field in stage.fields:
            _check_rule(
                f"fields.{field.id}.visible_when",
                field.condition_field_id,
                field.condition_option_ids,
                field_position(stage, field),
                stage.number,
                choice_fields,
                errors,
            )
    if errors:
        raise FieldConditionException(errors=errors)
