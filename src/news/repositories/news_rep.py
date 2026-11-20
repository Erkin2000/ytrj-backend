from datetime import datetime

from sqlalchemy import Select, exists, select

from src.news.enums import NewsState, NewsStatus
from src.news.mappers import NewsDataMapper
from src.news.models.news_model import NewsORM, NewsTranslationORM
from src.news.schemas.news_schema import NewsFilterDTO
from src.utils.base_rep.base_rep import BaseRepository


def visible(now: datetime):
    return (NewsORM.status == NewsStatus.PUBLISHED) & (NewsORM.publish_at <= now)


class NewsRepository(BaseRepository):
    model = NewsORM
    mapper = NewsDataMapper

    async def get_orm(self, news_id: int) -> NewsORM | None:
        stmt = (
            select(NewsORM).where(NewsORM.id == news_id).execution_options(populate_existing=True)
        )
        return await self.session.scalar(stmt)

    async def get_visible(self, news_id: int, now: datetime) -> NewsORM | None:
        return await self.session.scalar(select(NewsORM).where(NewsORM.id == news_id, visible(now)))

    async def get_public_page(self, now: datetime, page: int | None, per_page: int | None) -> dict:
        stmt = (
            select(NewsORM)
            .where(visible(now))
            .order_by(NewsORM.publish_at.desc(), NewsORM.id.desc())
        )
        return await self.paginate(stmt, page, per_page, mapper=NewsDataMapper.map_to_public)

    async def get_page(
        self, filters: NewsFilterDTO, now: datetime, page: int | None, per_page: int | None
    ) -> dict:
        stmt: Select = select(NewsORM)
        if filters.state == NewsState.DRAFT:
            stmt = stmt.where(NewsORM.status == NewsStatus.DRAFT)
        elif filters.state == NewsState.SCHEDULED:
            stmt = stmt.where(NewsORM.status == NewsStatus.PUBLISHED, NewsORM.publish_at > now)
        elif filters.state == NewsState.PUBLISHED:
            stmt = stmt.where(visible(now))
        if filters.search:
            stmt = stmt.where(
                exists().where(
                    NewsTranslationORM.news_id == NewsORM.id,
                    NewsTranslationORM.title.ilike(f"%{filters.search}%"),
                )
            )
        stmt = stmt.order_by(
            NewsORM.publish_at.desc().nulls_first(), NewsORM.created_at.desc(), NewsORM.id.desc()
        )
        return await self.paginate(stmt, page, per_page)
