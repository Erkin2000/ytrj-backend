from sqlalchemy import select

from src.application.mappers import CouncilAssignmentDataMapper
from src.application.models.council_assignment_model import CouncilAssignmentORM
from src.utils.base_rep.base_rep import BaseRepository


class CouncilAssignmentRepository(BaseRepository):
    model = CouncilAssignmentORM
    mapper = CouncilAssignmentDataMapper

    async def get_orm_for_member(
        self,
        application_id: int,
        council_member_id: int,
    ) -> CouncilAssignmentORM | None:
        return await self.session.scalar(
            select(self.model).where(
                self.model.application_id == application_id,
                self.model.council_member_id == council_member_id,
            )
        )

    async def get_orm_for_application(self, application_id: int) -> list[CouncilAssignmentORM]:
        result = await self.session.scalars(
            select(self.model)
            .where(self.model.application_id == application_id)
            .order_by(self.model.id)
        )
        return list(result.all())
