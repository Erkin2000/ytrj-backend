from enum import StrEnum


class NewsStatus(StrEnum):
    """Хранимый статус. Отложенная новость — PUBLISHED с `publish_at` в будущем:
    на сайте она появляется сама, когда наступает время публикации."""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class NewsState(StrEnum):
    """Что видит маркетинг: черновик, ждёт публикации или уже на сайте."""

    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
