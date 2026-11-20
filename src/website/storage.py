"""Фото контента сайта на диске: MEDIA_PATH/site/<folder>/<id>/."""

import shutil
from pathlib import Path

import anyio

from src.application.services.photo_storage import PhotoStorage


class SitePhotoStorage(PhotoStorage):
    subdir = ""
    folder: str

    def _application_dir(self, object_id: int) -> Path:
        return self.root / "site" / self.folder / str(object_id)

    async def delete_dir(self, object_id: int) -> None:
        directory = self._application_dir(object_id)
        await anyio.to_thread.run_sync(lambda: shutil.rmtree(directory, ignore_errors=True))


class PersonPhotoStorage(SitePhotoStorage):
    folder = "people"


class EventPhotoStorage(SitePhotoStorage):
    folder = "events"
