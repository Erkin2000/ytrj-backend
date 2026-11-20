from sqlalchemy import select

from src.faq.mappers import FaqDataMapper
from src.faq.models.faq_model import FaqORM
from src.utils.base_rep.base_rep import BaseRepository


class FaqRepository(BaseRepository):
    model = FaqORM
    mapper = FaqDataMapper

    async def get_orm(self, faq_id: int) -> FaqORM | None:
        stmt = select(FaqORM).where(FaqORM.id == faq_id).execution_options(populate_existing=True)
        return await self.session.scalar(stmt)

    async def get_list(self, only_active: bool = False) -> list[FaqORM]:
        stmt = select(FaqORM).order_by(FaqORM.sort_order, FaqORM.id)
        if only_active:
            stmt = stmt.where(FaqORM.is_active.is_(True))
        return list((await self.session.scalars(stmt)).all())
