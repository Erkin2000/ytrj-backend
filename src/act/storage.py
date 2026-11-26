"""Файлы актов на диске: MEDIA_PATH/acts/<id>/ — скриншоты приложения (JPEG / PNG,
те же проверки, что у фото заявки) и итоговый PDF подписанного акта."""

import hashlib
import secrets
import shutil
from pathlib import Path

import anyio

from src.application.services.photo_storage import PhotoStorage
from src.common.responses.exceptions import InvalidPhotoException

# PDF собирается fpdf2: WEBP он не встраивает, поэтому только JPEG и PNG.
ACT_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png"}
IMAGE_SIGNATURES = {"image/jpeg": b"\xff\xd8\xff", "image/png": b"\x89PNG\r\n\x1a\n"}


class ActFileStorage(PhotoStorage):
    subdir = "attachments"
    extensions = ACT_IMAGE_TYPES
    signatures = IMAGE_SIGNATURES
    invalid_exception = InvalidPhotoException

    @property
    def allowed_types(self) -> list[str]:
        return list(ACT_IMAGE_TYPES)

    def _act_dir(self, act_id: int) -> Path:
        return self.root / "acts" / str(act_id)

    def _application_dir(self, act_id: int) -> Path:
        return self._act_dir(act_id) / self.subdir

    @staticmethod
    def sha256_bytes(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    async def sha256(self, storage_path: str) -> str:
        content = await anyio.to_thread.run_sync(self.absolute_path(storage_path).read_bytes)
        return self.sha256_bytes(content)

    async def save_pdf(self, act_id: int, content: bytes) -> str:
        directory = self._act_dir(act_id)
        await anyio.to_thread.run_sync(lambda: directory.mkdir(parents=True, exist_ok=True))
        path = directory / f"dalolatnoma-{secrets.token_hex(8)}.pdf"
        await anyio.to_thread.run_sync(path.write_bytes, content)
        return path.relative_to(self.root).as_posix()

    async def read(self, storage_path: str) -> bytes:
        return await anyio.to_thread.run_sync(self.absolute_path(storage_path).read_bytes)

    async def delete_act_dir(self, act_id: int) -> None:
        directory = self._act_dir(act_id)
        await anyio.to_thread.run_sync(lambda: shutil.rmtree(directory, ignore_errors=True))
