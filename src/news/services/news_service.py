from datetime import UTC, datetime
from pathlib import Path

from fastapi import UploadFile

from src.account.schemas.user_schema import CurrentUserDTO
from src.bulletin.enums import TASHKENT_TZ
from src.common.responses.exceptions import (
    NewsNotFoundException,
    NewsPhotoNotFoundException,
    NewsScheduleException,
)
from src.news.enums import NewsState, NewsStatus
from src.news.mappers import NewsDataMapper, news_state
from src.news.models.news_model import NewsORM, NewsTranslationORM
from src.news.schemas.news_schema import (
    NewsCreateForm,
    NewsDTO,
    NewsFilterDTO,
    NewsPublicDTO,
    NewsUpdateDTO,
)
from src.news.storage import NewsPhotoStorage
from src.product.services.product_service import apply_translations
from src.utils.base_service import BaseService


def utcnow() -> datetime:
    return datetime.now(UTC)


class NewsService(BaseService):
    storage = NewsPhotoStorage()

    # ---------- сайт ----------

    async def get_public_page(self, page: int | None, per_page: int | None) -> dict:
        return await self.db.news.get_public_page(utcnow(), page, per_page)

    async def get_public_detail(self, news_id: int) -> NewsPublicDTO:
        news = await self.db.news.get_visible(news_id, utcnow())
        if news is None:
            raise NewsNotFoundException()
        return NewsDataMapper.map_to_public(news)

    async def public_photo(self, news_id: int) -> tuple[Path, str, str]:
        news = await self.db.news.get_visible(news_id, utcnow())
        if news is None:
            raise NewsNotFoundException()
        return self._photo_file(news)

    # ---------- маркетинг ----------

    async def get_page(
        self, filters: NewsFilterDTO, page: int | None, per_page: int | None
    ) -> dict:
        return await self.db.news.get_page(filters, utcnow(), page, per_page)

    async def get_detail(self, news_id: int) -> NewsDTO:
        return NewsDataMapper.map_to_domain_entity(await self._get(news_id))

    async def photo(self, news_id: int) -> tuple[Path, str, str]:
        return self._photo_file(await self._get(news_id))

    async def create(self, user: CurrentUserDTO, form: NewsCreateForm) -> NewsDTO:
        now = utcnow()
        status, publish_at = self._schedule(form.status, form.publish_at, now)
        news = NewsORM(
            status=status,
            publish_at=publish_at,
            news_date=form.date or (publish_at or now).astimezone(TASHKENT_TZ).date(),
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        apply_translations(news.translations, form.translations(), NewsTranslationORM)
        self.db.session.add(news)
        await self.db.flush()
        try:
            if form.photo is not None:
                await self._store_photo(news, form.photo)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            await self.storage.delete_news_dir(news.id)
            raise
        return await self.get_detail(news.id)

    async def update(self, user: CurrentUserDTO, news_id: int, data: NewsUpdateDTO) -> NewsDTO:
        news = await self._get(news_id)
        now = utcnow()
        fields = data.model_fields_set

        if "status" in fields and data.status is not None:
            if data.status == NewsState.PUBLISHED and news_state(news, now) == NewsState.PUBLISHED:
                pass  # уже на сайте — дату публикации не сдвигаем
            else:
                news.status, news.publish_at = self._schedule(data.status, data.publish_at, now)
        elif "publish_at" in fields:
            if news_state(news, now) != NewsState.SCHEDULED:
                raise NewsScheduleException(
                    "publish_at can be changed only for a scheduled news item; "
                    "send status=SCHEDULED to schedule it",
                    field="publish_at",
                )
            news.status, news.publish_at = self._schedule(NewsState.SCHEDULED, data.publish_at, now)

        if data.translations is not None:
            apply_translations(news.translations, data.translations, NewsTranslationORM)
        if data.date is not None:
            news.news_date = data.date
        news.updated_by_id = user.id
        await self.db.commit()
        return await self.get_detail(news_id)

    async def set_photo(self, user: CurrentUserDTO, news_id: int, photo: UploadFile) -> NewsDTO:
        news = await self._get(news_id)
        old_path = news.photo_path
        await self._store_photo(news, photo)
        news.updated_by_id = user.id
        try:
            await self.db.commit()
        except Exception:
            await self.storage.delete(news.photo_path)
            raise
        if old_path:
            await self.storage.delete(old_path)
        return await self.get_detail(news_id)

    async def delete_photo(self, user: CurrentUserDTO, news_id: int) -> NewsDTO:
        news = await self._get(news_id)
        if not news.photo_path:
            raise NewsPhotoNotFoundException()
        old_path = news.photo_path
        news.photo_path = news.photo_name = news.photo_content_type = None
        news.photo_size = None
        news.updated_by_id = user.id
        await self.db.commit()
        await self.storage.delete(old_path)
        return await self.get_detail(news_id)

    async def delete(self, news_id: int) -> None:
        news = await self._get(news_id)
        await self.db.session.delete(news)
        await self.db.commit()
        await self.storage.delete_news_dir(news_id)

    # ---------- внутреннее ----------

    @staticmethod
    def _schedule(
        state: NewsState, publish_at: datetime | None, now: datetime
    ) -> tuple[NewsStatus, datetime | None]:
        if state == NewsState.DRAFT:
            return NewsStatus.DRAFT, None
        if state == NewsState.PUBLISHED:
            return NewsStatus.PUBLISHED, now
        if publish_at is None:
            raise NewsScheduleException(
                "publish_at is required for a scheduled news item", field="publish_at"
            )
        if publish_at <= now:
            raise NewsScheduleException(
                "publish_at must be in the future; use status PUBLISHED to publish now",
                field="publish_at",
            )
        return NewsStatus.PUBLISHED, publish_at

    async def _get(self, news_id: int) -> NewsORM:
        news = await self.db.news.get_orm(news_id)
        if news is None:
            raise NewsNotFoundException()
        return news

    async def _store_photo(self, news: NewsORM, photo: UploadFile) -> None:
        path, size, content_type = await self.storage.save(news.id, photo)
        news.photo_path = path
        news.photo_name = (Path(photo.filename or "").name or Path(path).name)[:255]
        news.photo_content_type = content_type
        news.photo_size = size

    def _photo_file(self, news: NewsORM) -> tuple[Path, str, str]:
        if not news.photo_path:
            raise NewsPhotoNotFoundException()
        path = self.storage.absolute_path(news.photo_path)
        if not path.is_file():
            raise NewsPhotoNotFoundException()
        return path, news.photo_content_type or "image/jpeg", news.photo_name or path.name
