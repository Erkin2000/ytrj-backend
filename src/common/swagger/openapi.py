"""Доработка сгенерированной OpenAPI-схемы."""

from typing import Any

from src.common.swagger.responses import NULL_MARKER


def restore_nulls(node: Any) -> Any:
    """Заменяет NULL_MARKER на None по всей схеме (на месте) — примеры ответов
    показывают null-поля так же, как реальный ответ."""
    if isinstance(node, dict):
        for key, value in node.items():
            node[key] = None if value == NULL_MARKER else restore_nulls(value)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            node[index] = None if value == NULL_MARKER else restore_nulls(value)
    return node
