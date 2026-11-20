"""Пост Telegram-канала → новость сайта.

- Берутся только каналы из TELEGRAM_CHANNELS; остальные — в лог с id и названием.
- Заголовок — первая строка поста (до 200 символов), текст — остальное; если пост
  из одной строки, текст повторяет её. Один текст записывается на ru, uz и en —
  переводы маркетинг правит в админке.
- Новость сразу публикуется (status PUBLISHED), дата — дата поста по Ташкенту.
- Фото — самое крупное из поста. Альбом: новость создаёт сообщение с подписью,
  фото других сообщений альбома добавляется, только если у новости фото ещё нет.
- Пост без текста (только фото, видео без подписи, опрос) пропускается.
- Повторно пришедший пост не создаёт дубль (уникальность чата + сообщения).
- Правка поста в канале обновляет текст, пока новость не меняли в админке.
- Удаление поста Telegram боту не сообщает — такую новость убирает маркетинг.
"""

import io
import logging
from datetime import UTC, datetime

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from starlette.datastructures import Headers

from src.bulletin.enums import TASHKENT_TZ
from src.common.responses.exceptions import ApiException
from src.config import settings
from src.news.enums import NewsSource, NewsStatus
from src.news.models.news_model import NewsORM, NewsTranslationORM
from src.news.storage import NewsPhotoStorage
from src.news.telegram.client import TelegramClient, TelegramError
from src.product.enums import Language
from src.utils.db_manager import DBManager

logger = logging.getLogger(__name__)

TITLE_LIMIT = 200
TEXT_LIMIT = 50000


def split_post(text: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.strip().splitlines()]
    lines = [line for line in lines if line] or [text.strip()]
    title = lines[0]
    if len(title) > TITLE_LIMIT:
        cut = title[:TITLE_LIMIT].rsplit(" ", 1)[0] or title[:TITLE_LIMIT]
        title = cut.rstrip(" ,.;:-—") + "…"
    body = "\n".join(text.strip().splitlines()[1:]).strip()
    return title, (body or text.strip())[:TEXT_LIMIT]


def is_allowed(chat: dict) -> bool:
    allowed = settings.telegram_channels
    username = (chat.get("username") or "").lower()
    return str(chat.get("id")) in allowed or (bool(username) and f"@{username}" in allowed)


def post_url(chat: dict, message_id: int) -> str | None:
    username = chat.get("username")
    return f"https://t.me/{username}/{message_id}" if username else None


def largest_photo(post: dict) -> dict | None:
    sizes = post.get("photo") or []
    return (
        max(sizes, key=lambda s: s.get("file_size") or s.get("width", 0) * s.get("height", 0))
        if sizes
        else None
    )


class TelegramNewsService:
    storage = NewsPhotoStorage()

    def __init__(self, db: DBManager, client: TelegramClient):
        self.db = db
        self.client = client

    async def handle_update(self, update: dict) -> NewsORM | None:
        """Обрабатывает одно обновление. Возвращает созданную или изменённую новость."""
        edited = "edited_channel_post" in update
        post = update.get("edited_channel_post") or update.get("channel_post")
        if not post:
            return None
        chat = post.get("chat") or {}
        if chat.get("type") != "channel":
            return None
        if not is_allowed(chat):
            logger.info(
                "Telegram post ignored: channel id=%s username=%s title=%r is not in TELEGRAM_CHANNELS",
                chat.get("id"),
                chat.get("username"),
                chat.get("title"),
            )
            return None

        chat_id, message_id = int(chat["id"]), int(post["message_id"])
        text = (post.get("text") or post.get("caption") or "").strip()
        photo = largest_photo(post)
        album = post.get("media_group_id")

        news = await self.db.news.get_by_telegram_message(chat_id, message_id)
        if edited:
            return await self._apply_edit(news, text)
        if news is not None:
            return None  # пост уже сохранён

        if not text:
            if album and photo:
                return await self._attach_album_photo(chat_id, album, photo)
            return None

        if album:
            existing = await self.db.news.get_by_telegram_album(chat_id, album)
            if existing is not None:
                return None

        return await self._create(post, chat, text, photo)

    async def _create(
        self, post: dict, chat: dict, text: str, photo: dict | None
    ) -> NewsORM | None:
        posted_at = (
            datetime.fromtimestamp(int(post.get("date") or 0), UTC)
            if post.get("date")
            else datetime.now(UTC)
        )
        now = datetime.now(UTC)
        title, body = split_post(text)
        news = NewsORM(
            status=NewsStatus.PUBLISHED,
            publish_at=min(posted_at, now),
            news_date=posted_at.astimezone(TASHKENT_TZ).date(),
            source=NewsSource.TELEGRAM,
            telegram_chat_id=int(chat["id"]),
            telegram_message_id=int(post["message_id"]),
            telegram_media_group_id=post.get("media_group_id"),
            telegram_url=post_url(chat, int(post["message_id"])),
        )
        for language in (Language.RU, Language.UZ, Language.EN):
            news.translations.append(NewsTranslationORM(language=language, title=title, text=body))
        self.db.session.add(news)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()  # тот же пост уже сохранил другой процесс
            return None
        if photo:
            await self._store_photo(news, photo)
        await self.db.commit()
        logger.info(
            "Telegram post %s/%s saved as news %s", chat.get("id"), post["message_id"], news.id
        )
        return news

    async def _apply_edit(self, news: NewsORM | None, text: str) -> NewsORM | None:
        if news is None or not text:
            return None
        if news.updated_by_id is not None:
            return None  # новость уже правили в админке — их правки важнее
        title, body = split_post(text)
        for translation in news.translations:
            translation.title, translation.text = title, body
        await self.db.commit()
        return news

    async def _attach_album_photo(self, chat_id: int, album: str, photo: dict) -> NewsORM | None:
        news = await self.db.news.get_by_telegram_album(chat_id, album)
        if news is None or news.photo_path:
            return None
        await self._store_photo(news, photo)
        await self.db.commit()
        return news

    async def _store_photo(self, news: NewsORM, photo: dict) -> None:
        """Фото не обязательно: если скачать или сохранить не вышло, новость остаётся без него."""
        try:
            content = await self.client.download_file(photo["file_id"])
            upload = UploadFile(
                file=io.BytesIO(content),
                filename="telegram.jpg",
                headers=Headers({"content-type": "image/jpeg"}),
            )
            path, size, content_type = await self.storage.save(news.id, upload)
        except (TelegramError, ApiException, OSError) as error:
            logger.warning("Telegram photo for news %s is skipped: %s", news.id, error)
            return
        news.photo_path = path
        news.photo_name = "telegram.jpg"
        news.photo_content_type = content_type
        news.photo_size = size
