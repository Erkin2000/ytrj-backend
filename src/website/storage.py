"""Фото карточек сайта на диске: MEDIA_PATH/site/people/<id>/."""

import shutil
from pathlib import Path

import anyio

from src.application.services.photo_storage import PhotoStorage


class PersonPhotoStorage(PhotoStorage):
    subdir = ""

    def _application_dir(self, person_id: int) -> Path:
        return self.root / "site" / "people" / str(person_id)

    async def delete_person_dir(self, person_id: int) -> None:
        directory = self._application_dir(person_id)
        await anyio.to_thread.run_sync(lambda: shutil.rmtree(directory, ignore_errors=True))
