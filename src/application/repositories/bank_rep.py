from sqlalchemy import select

from src.application.mappers import BankDataMapper
from src.application.models.bank_model import BankORM
from src.application.schemas.bank_schema import BankDTO
from src.utils.base_rep.base_rep import BaseRepository


class BankRepository(BaseRepository):
    model = BankORM
    mapper = BankDataMapper

    async def get_all(
        self,
        subject_type: str | None = None,
        only_active: bool = True,
    ) -> list[BankDTO]:
        stmt = select(self.model).order_by(self.model.sort_order, self.model.id)

        if only_active:
            stmt = stmt.where(self.model.is_active.is_(True))
        if subject_type:
            stmt = stmt.where(self.model.allowed_subject_types.any(subject_type))

        result = await self.session.scalars(stmt)
        return [self.mapper.map_to_domain_entity(m) for m in result.all()]
