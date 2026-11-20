"""Фото новости на диске: MEDIA_PATH/news/<id>/. Те же проверки, что у фото заявки."""

import shutil
from pathlib import Path

import anyio

from src.application.services.photo_storage import PhotoStorage


class NewsPhotoStorage(PhotoStorage):
    subdir = ""

    def _application_dir(self, news_id: int) -> Path:
        return self.root / "news" / str(news_id)

    async def delete_news_dir(self, news_id: int) -> None:
        directory = self._application_dir(news_id)
        await anyio.to_thread.run_sync(lambda: shutil.rmtree(directory, ignore_errors=True))
