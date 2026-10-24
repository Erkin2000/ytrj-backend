from sqlalchemy import func, select

from src.application.mappers import DocumentDataMapper
from src.application.models.document_model import ApplicationDocumentORM
from src.utils.base_rep.base_rep import BaseRepository


class ApplicationDocumentRepository(BaseRepository):
    model = ApplicationDocumentORM
    mapper = DocumentDataMapper

    async def count_for_application(self, application_id: int) -> int:
        return (
            await self.session.scalar(
                select(func.count())
                .select_from(self.model)
                .where(self.model.application_id == application_id)
            )
            or 0
        )

    async def get_orm(self, application_id: int, document_id: int) -> ApplicationDocumentORM | None:
        return await self.session.scalar(
            select(self.model).where(
                self.model.id == document_id,
                self.model.application_id == application_id,
            )
        )
