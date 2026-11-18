"""Файл бюллетеня (PDF / DOCX) на диске: MEDIA_PATH/bulletins/<id>/.
Те же проверки формата, сигнатуры и размера, что у документов заявки."""

import hashlib
import shutil
from pathlib import Path

import anyio

from src.application.services.photo_storage import DocumentStorage


class BulletinFileStorage(DocumentStorage):
    subdir = ""

    def _application_dir(self, bulletin_id: int) -> Path:
        return self.root / "bulletins" / str(bulletin_id)

    async def sha256(self, storage_path: str) -> str:
        path = self.absolute_path(storage_path)
        content = await anyio.to_thread.run_sync(path.read_bytes)
        return hashlib.sha256(content).hexdigest()

    async def delete_bulletin_dir(self, bulletin_id: int) -> None:
        directory = self._application_dir(bulletin_id)
        await anyio.to_thread.run_sync(lambda: shutil.rmtree(directory, ignore_errors=True))
