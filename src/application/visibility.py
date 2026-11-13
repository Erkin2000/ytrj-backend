"""Какие этапы и поля анкеты видны заявителю при текущих ответах.

Условие показа (`condition_field_id` + `condition_option_ids`) выполняется,
если управляющее поле само видно и среди выбранных в нём вариантов есть хотя
бы один из условия. Поле видно, если виден его этап и выполнено его условие;
этап — если выполнено условие этапа. Управляющее поле всегда расположено
раньше (это проверяет конструктор), поэтому обход анкеты по порядку решает
всё за один проход.
"""

from dataclasses import dataclass, field

from src.application.field_values import chosen_option_ids
from src.product.models.product_model import ProductFieldORM, ProductORM, ProductStageORM


@dataclass
class Visibility:
    stage_ids: set[int] = field(default_factory=set)
    field_ids: set[int] = field(default_factory=set)

    def stage(self, stage: ProductStageORM) -> bool:
        return stage.id in self.stage_ids

    def field(self, item: ProductFieldORM) -> bool:
        return item.id in self.field_ids


def _passes(
    condition_field_id: int | None,
    condition_option_ids: list[int] | None,
    chosen: dict[int, set[int]],
) -> bool:
    if condition_field_id is None or not condition_option_ids:
        return True
    selected = chosen.get(condition_field_id)
    return bool(selected) and bool(selected & set(condition_option_ids))


def visible(product: ProductORM | None, values: dict[int, str]) -> Visibility:
    """`values` — сохранённые значения: id поля → строка."""
    result = Visibility()
    if product is None:
        return result
    # Выбранные варианты только видимых управляющих полей.
    chosen: dict[int, set[int]] = {}
    for stage in sorted(product.stages, key=lambda s: s.number):
        if not _passes(stage.condition_field_id, stage.condition_option_ids, chosen):
            continue
        result.stage_ids.add(stage.id)
        for item in sorted(stage.fields, key=lambda f: (f.sort_order, f.id)):
            if not _passes(item.condition_field_id, item.condition_option_ids, chosen):
                continue
            result.field_ids.add(item.id)
            chosen[item.id] = chosen_option_ids(item, values.get(item.id))
    return result
