from sqlalchemy import select

from src.application.mappers import ScoringAttemptDataMapper
from src.application.models.scoring_model import ScoringAttemptORM
from src.application.schemas.application_schema import ScoringAttemptDTO
from src.utils.base_rep.base_rep import BaseRepository


class ScoringAttemptRepository(BaseRepository):
    model = ScoringAttemptORM
    mapper = ScoringAttemptDataMapper

    async def get_for_application(self, application_id: int) -> list[ScoringAttemptDTO]:
        stmt = (
            select(self.model)
            .where(self.model.application_id == application_id)
            .order_by(self.model.id)
        )
        result = await self.session.scalars(stmt)
        return [self.mapper.map_to_domain_entity(m) for m in result.all()]
