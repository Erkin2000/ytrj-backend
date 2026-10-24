from sqlalchemy import func, select

from src.application.mappers import FounderDataMapper
from src.application.models.founder_model import ApplicationFounderORM
from src.utils.base_rep.base_rep import BaseRepository


class ApplicationFounderRepository(BaseRepository):
    model = ApplicationFounderORM
    mapper = FounderDataMapper

    async def count_for_application(self, application_id: int) -> int:
        return (
            await self.session.scalar(
                select(func.count())
                .select_from(self.model)
                .where(self.model.application_id == application_id)
            )
            or 0
        )

    async def get_orm(self, application_id: int, founder_id: int) -> ApplicationFounderORM | None:
        return await self.session.scalar(
            select(self.model).where(
                self.model.id == founder_id,
                self.model.application_id == application_id,
            )
        )
