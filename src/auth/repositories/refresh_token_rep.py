from sqlalchemy import select

from src.auth.mappers import RefreshTokenDataMapper
from src.auth.models.refresh_token_model import RefreshTokenORM
from src.auth.schemas.auth_schema import RefreshTokenDTO
from src.utils.base_rep.base_rep import BaseRepository


class RefreshTokenRepository(BaseRepository):
    model = RefreshTokenORM
    mapper = RefreshTokenDataMapper

    async def get_user_sessions(self, user_id: int) -> list[RefreshTokenDTO]:
        stmt = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .order_by(self.model.created_at.desc())
        )
        result = await self.session.scalars(stmt)
        return [self.mapper.map_to_domain_entity(m) for m in result.all()]
