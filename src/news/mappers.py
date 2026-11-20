from datetime import UTC, datetime

from src.application.mappers import actor
from src.news.enums import NewsState, NewsStatus
from src.news.models.news_model import NewsORM
from src.news.schemas.news_schema import (
    NewsDTO,
    NewsPhotoDTO,
    NewsPublicDTO,
    NewsTranslationOutDTO,
)
from src.utils.base_rep.mappers.base import DataMapper

PUBLIC_PREFIX = "/api/v1/news"
MARKETING_PREFIX = "/api/v1/marketing/news"


def news_state(model: NewsORM, now: datetime | None = None) -> NewsState:
    if model.status == NewsStatus.DRAFT or model.publish_at is None:
        return NewsState.DRAFT
    if model.publish_at > (now or datetime.now(UTC)):
        return NewsState.SCHEDULED
    return NewsState.PUBLISHED


def _translations(model: NewsORM) -> list[NewsTranslationOutDTO]:
    return [
        NewsTranslationOutDTO(language=t.language, title=t.title, text=t.text)
        for t in model.translations
    ]


def _photo(model: NewsORM, prefix: str) -> NewsPhotoDTO | None:
    if not model.photo_path:
        return None
    return NewsPhotoDTO(
        url=f"{prefix}/{model.id}/photo",
        name=model.photo_name,
        content_type=model.photo_content_type or "image/jpeg",
        size=model.photo_size or 0,
    )


class NewsDataMapper(DataMapper):
    db_model = NewsORM
    schema = NewsDTO

    @classmethod
    def map_to_domain_entity(cls, data: NewsORM) -> NewsDTO:
        return NewsDTO(
            id=data.id,
            translations=_translations(data),
            date=data.news_date,
            state=news_state(data),
            publish_at=data.publish_at,
            photo=_photo(data, MARKETING_PREFIX),
            source=data.source,
            telegram_url=data.telegram_url,
            created_by=actor(data.created_by),
            updated_by=actor(data.updated_by),
            created_at=data.created_at,
            updated_at=data.updated_at,
        )

    @staticmethod
    def map_to_public(data: NewsORM) -> NewsPublicDTO:
        return NewsPublicDTO(
            id=data.id,
            translations=_translations(data),
            date=data.news_date,
            published_at=data.publish_at,
            photo=_photo(data, PUBLIC_PREFIX),
        )
