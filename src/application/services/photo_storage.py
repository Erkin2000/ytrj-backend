"""Хранение файлов заявки на диске (MEDIA_PATH): фотографии и документы.
Позже заменяется на закрытый S3-бакет с короткоживущими ссылками."""

import secrets
import shutil
from pathlib import Path

import anyio
from fastapi import UploadFile

from src.common.responses.exceptions import (
    ApiException,
    DocumentTooLargeException,
    InvalidDocumentException,
    InvalidPhotoException,
    PhotoTooLargeException,
)
from src.config import settings

PHOTO_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DOCUMENT_EXTENSIONS = {
    "application/pdf": ".pdf",
    DOCX_TYPE: ".docx",
}
# Сигнатуры файлов: PDF начинается с %PDF, DOCX — zip-архив (PK).
DOCUMENT_SIGNATURES = {
    "application/pdf": b"%PDF",
    DOCX_TYPE: b"PK\x03\x04",
}


class FileStorage:
    """Общая логика: проверка типа и размера, запись под случайным именем,
    удаление. Подкаталог и ограничения задаёт подкласс."""

    subdir: str
    extensions: dict[str, str]
    signatures: dict[str, bytes] = {}
    invalid_exception: type[ApiException]
    too_large_exception: type[ApiException]

    @property
    def allowed_types(self) -> list[str]:
        raise NotImplementedError

    @property
    def max_size_mb(self) -> int:
        raise NotImplementedError

    @property
    def root(self) -> Path:
        return settings.media_dir

    def _application_dir(self, application_id: int) -> Path:
        return self.root / "applications" / str(application_id) / self.subdir

    def _detect_type(self, upload: UploadFile) -> str | None:
        """Тип по content-type, а при общем application/octet-stream — по расширению имени."""
        content_type = (upload.content_type or "").lower().split(";")[0].strip()
        if content_type in self.extensions:
            return content_type
        suffix = Path(upload.filename or "").suffix.lower()
        for mime, ext in self.extensions.items():
            if ext == suffix:
                return mime
        return None

    async def save(self, application_id: int, upload: UploadFile) -> tuple[str, int, str]:
        """Проверяет формат и размер, сохраняет файл.
        Возвращает (относительный путь, размер, content_type)."""
        content_type = self._detect_type(upload)
        if content_type is None or content_type not in self.allowed_types:
            received = upload.content_type or Path(upload.filename or "").suffix or "unknown"
            raise self.invalid_exception(f"{self.invalid_exception.message}; received: {received}")

        max_size = self.max_size_mb * 1024 * 1024
        content = await upload.read()

        if len(content) > max_size:
            raise self.too_large_exception(
                f"File is too large: {len(content) / 1024 / 1024:.1f} MB. "
                f"Maximum size is {self.max_size_mb} MB"
            )
        if not content:
            raise self.invalid_exception("Empty file")

        signature = self.signatures.get(content_type)
        if signature and not content.startswith(signature):
            raise self.invalid_exception(f"File content does not match its type ({content_type})")

        directory = self._application_dir(application_id)
        await anyio.to_thread.run_sync(lambda: directory.mkdir(parents=True, exist_ok=True))

        file_name = f"{secrets.token_hex(16)}{self.extensions[content_type]}"
        path = directory / file_name
        await anyio.to_thread.run_sync(path.write_bytes, content)

        relative = path.relative_to(self.root).as_posix()
        return relative, len(content), content_type

    def absolute_path(self, storage_path: str) -> Path:
        return self.root / storage_path

    async def delete(self, storage_path: str) -> None:
        path = self.absolute_path(storage_path)
        await anyio.to_thread.run_sync(lambda: path.unlink(missing_ok=True))

    async def delete_application_dir(self, application_id: int) -> None:
        """Удаляет каталог заявки целиком (фото и документы) — при удалении черновика."""
        directory = self.root / "applications" / str(application_id)
        await anyio.to_thread.run_sync(lambda: shutil.rmtree(directory, ignore_errors=True))


class PhotoStorage(FileStorage):
    subdir = "photos"
    extensions = PHOTO_EXTENSIONS
    invalid_exception = InvalidPhotoException
    too_large_exception = PhotoTooLargeException

    @property
    def allowed_types(self) -> list[str]:
        return settings.PHOTO_ALLOWED_TYPES

    @property
    def max_size_mb(self) -> int:
        return settings.PHOTO_MAX_SIZE_MB

    def _application_dir(self, application_id: int) -> Path:
        # Фото исторически лежат прямо в каталоге заявки — путь не меняем.
        return self.root / "applications" / str(application_id)


class DocumentStorage(FileStorage):
    subdir = "documents"
    extensions = DOCUMENT_EXTENSIONS
    signatures = DOCUMENT_SIGNATURES
    invalid_exception = InvalidDocumentException
    too_large_exception = DocumentTooLargeException

    @property
    def allowed_types(self) -> list[str]:
        return settings.DOCUMENT_ALLOWED_TYPES

    @property
    def max_size_mb(self) -> int:
        return settings.DOCUMENT_MAX_SIZE_MB
