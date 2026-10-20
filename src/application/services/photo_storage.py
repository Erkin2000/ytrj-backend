"""Хранение фотографий заявки на диске (MEDIA_PATH).
Позже заменяется на закрытый S3-бакет с короткоживущими ссылками."""

import secrets
from pathlib import Path

import anyio
from fastapi import UploadFile

from src.common.responses.exceptions import InvalidPhotoException, PhotoTooLargeException
from src.config import settings

EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class PhotoStorage:
    @property
    def root(self) -> Path:
        return settings.media_dir

    def _application_dir(self, application_id: int) -> Path:
        return self.root / "applications" / str(application_id)

    async def save(self, application_id: int, upload: UploadFile) -> tuple[str, int, str]:
        """Проверяет формат и размер, сохраняет файл.
        Возвращает (относительный путь, размер, content_type)."""
        content_type = (upload.content_type or "").lower()

        if content_type not in settings.PHOTO_ALLOWED_TYPES or content_type not in EXTENSIONS:
            raise InvalidPhotoException()

        max_size = settings.PHOTO_MAX_SIZE_MB * 1024 * 1024
        content = await upload.read()

        if len(content) > max_size:
            raise PhotoTooLargeException(
                f"Photo is too large. Maximum size is {settings.PHOTO_MAX_SIZE_MB} MB"
            )
        if not content:
            raise InvalidPhotoException("Empty file")

        directory = self._application_dir(application_id)
        await anyio.to_thread.run_sync(lambda: directory.mkdir(parents=True, exist_ok=True))

        file_name = f"{secrets.token_hex(16)}{EXTENSIONS[content_type]}"
        path = directory / file_name
        await anyio.to_thread.run_sync(path.write_bytes, content)

        relative = path.relative_to(self.root).as_posix()
        return relative, len(content), content_type

    def absolute_path(self, storage_path: str) -> Path:
        return self.root / storage_path

    async def delete(self, storage_path: str) -> None:
        path = self.absolute_path(storage_path)
        await anyio.to_thread.run_sync(lambda: path.unlink(missing_ok=True))
