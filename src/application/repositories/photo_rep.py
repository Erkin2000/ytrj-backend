from sqlalchemy import func, select

from src.application.mappers import PhotoDataMapper
from src.application.models.photo_model import ApplicationPhotoORM
from src.utils.base_rep.base_rep import BaseRepository


class ApplicationPhotoRepository(BaseRepository):
    model = ApplicationPhotoORM
    mapper = PhotoDataMapper

    async def count_for_application(self, application_id: int) -> int:
        return (
            await self.session.scalar(
                select(func.count())
                .select_from(self.model)
                .where(self.model.application_id == application_id)
            )
            or 0
        )

    async def get_orm(self, application_id: int, photo_id: int) -> ApplicationPhotoORM | None:
        return await self.session.scalar(
            select(self.model).where(
                self.model.id == photo_id,
                self.model.application_id == application_id,
            )
        )
