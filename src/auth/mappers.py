from src.auth.models.refresh_token_model import RefreshTokenORM
from src.auth.schemas.auth_schema import RefreshTokenDTO
from src.utils.base_rep.mappers.base import DataMapper


class RefreshTokenDataMapper(DataMapper):
    db_model = RefreshTokenORM
    schema = RefreshTokenDTO
