"""Полное удаление заявки (только Super Admin): запись заявки и всё, что с ней связано.

В БД каскадом (ON DELETE CASCADE) удаляются: история статусов, попытки скоринга,
назначения и решения Совета, ответы и файлы анкеты, документ-требование,
выделение ресурсов, фото, документы и учредители старой анкеты.
С диска удаляется каталог MEDIA_PATH/applications/<id>/ (фото, документы, файлы
анкеты) и файл документа-требования, если он сформирован.
Запись о самом удалении нигде не сохраняется.
"""

from pathlib import Path

import anyio

from src.application.services.base import ApplicationBaseService
from src.application.services.photo_storage import FieldPhotoStorage
from src.config import settings


class ApplicationPurgeService(ApplicationBaseService):
    storage = FieldPhotoStorage()

    async def purge(self, application_id: int) -> None:
        application = await self.get_orm_or_404(application_id)
        extra_files = self._demand_document_files(application)

        await self.db.application.delete(id=application.id)
        await self.db.commit()

        # Файлы — после commit: если БД откатится, файлы заявки останутся целыми.
        await self.storage.delete_application_dir(application_id)
        for path in extra_files:
            await anyio.to_thread.run_sync(lambda p=path: p.unlink(missing_ok=True))

    @staticmethod
    def _demand_document_files(application) -> list[Path]:
        document = application.demand_document
        if document is None or not document.file_path:
            return []
        root = settings.media_dir.resolve()
        path = Path(document.file_path)
        path = (path if path.is_absolute() else root / path).resolve()
        # Удаляем только внутри MEDIA_PATH.
        return [path] if path.is_relative_to(root) else []
