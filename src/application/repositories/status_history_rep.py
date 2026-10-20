from sqlalchemy import select

from src.application.mappers import StatusHistoryDataMapper
from src.application.models.status_history_model import StatusHistoryORM
from src.application.schemas.application_schema import StatusHistoryDTO
from src.utils.base_rep.base_rep import BaseRepository


class StatusHistoryRepository(BaseRepository):
    model = StatusHistoryORM
    mapper = StatusHistoryDataMapper

    async def get_for_application(self, application_id: int) -> list[StatusHistoryDTO]:
        stmt = (
            select(self.model)
            .where(self.model.application_id == application_id)
            .order_by(self.model.id)
        )
        result = await self.session.scalars(stmt)
        return [self.mapper.map_to_domain_entity(m) for m in result.all()]
