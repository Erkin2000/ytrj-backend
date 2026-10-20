import asyncio
from datetime import UTC, datetime

from src.account.mappers import UserDataMapper
from src.account.models.user_model import UserORM, UserStatus
from src.account.schemas.user_schema import CurrentUserDTO, UserAddDTO, UserProfileDTO
from src.auth.schemas.auth_schema import (
    ChangePasswordDTO,
    LoginDTO,
    OneIDAuthorizeDTO,
    OneIDMockLoginDTO,
    OneIDProfileDTO,
    RefreshTokenCreateDTO,
    TokenPairDTO,
)
from src.auth.services.oneid_service import OneIDService
from src.auth.services.password_service import hash_password, verify_password
from src.auth.services.token_service import TokenService
from src.common.responses.exceptions import (
    ApplicantLoginViaOneIDException,
    ExpiredRefreshTokenException,
    InvalidCredentialsException,
    InvalidCurrentPasswordException,
    OneIDException,
    OneIDNotForInternalUsersException,
    PasswordLoginNotAllowedException,
    RefreshTokenNotFoundException,
    RefreshTokenRevokedException,
    SamePasswordException,
    UserBlockedException,
    UserNotFoundException,
)
from src.config import settings
from src.rbac.permissions import RoleCode
from src.utils.base_service import BaseService


class AuthService(BaseService):
    token_service = TokenService()
    oneid_service = OneIDService()

    # ---------- токены ----------

    async def _issue_tokens(
        self,
        user_id: int,
        user_agent: str | None = None,
        ip_address: str | None = None,
        *,
        touch_login: bool = False,
    ) -> TokenPairDTO:
        access_token = self.token_service.create_access_token(user_id)
        refresh_token = self.token_service.create_refresh_token(user_id)

        await self.db.refresh_token.add(
            RefreshTokenCreateDTO(
                user_id=user_id,
                refresh_token=refresh_token,
                expires_at=datetime.now(UTC) + self.token_service.refresh_expire,
                user_agent=user_agent[:512] if user_agent else None,
                ip_address=ip_address,
            )
        )

        if touch_login:
            await self.db.user.touch_last_login(user_id)

        await self.db.commit()

        return TokenPairDTO(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(self.token_service.access_expire.total_seconds()),
        )

    async def login(
        self,
        data: LoginDTO,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPairDTO:
        user = await self.db.user.get_orm_by_username(data.username)

        is_valid = await asyncio.to_thread(
            verify_password,
            data.password,
            user.hashed_password if user else None,
        )

        if user is None or not is_valid:
            raise InvalidCredentialsException()

        # Заявители входят только через OneID; пароль — для внутренних ролей.
        if self._is_applicant(user):
            raise ApplicantLoginViaOneIDException()

        if user.status != UserStatus.ACTIVE:
            raise UserBlockedException()

        return await self._issue_tokens(user.id, user_agent, ip_address, touch_login=True)

    @staticmethod
    def _is_applicant(user: UserORM) -> bool:
        return user.role is not None and user.role.code == RoleCode.APPLICANT

    async def refresh_tokens(
        self,
        refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPairDTO:
        payload = self.token_service.decode_refresh_token(refresh_token)
        user_id = int(payload["sub"])

        token_db = await self.db.refresh_token.get_one_or_none(refresh_token=refresh_token)

        if token_db is None or token_db.user_id != user_id:
            raise RefreshTokenNotFoundException()
        if token_db.is_revoked:
            raise RefreshTokenRevokedException()
        if token_db.expires_at < datetime.now(UTC):
            raise ExpiredRefreshTokenException()

        user = await self.db.user.get_orm_by_id(user_id)
        if user is None:
            raise UserNotFoundException()
        if user.status != UserStatus.ACTIVE:
            raise UserBlockedException()

        await self.db.refresh_token.delete(id=token_db.id)
        return await self._issue_tokens(user_id, user_agent, ip_address)

    async def logout(self, refresh_token: str) -> None:
        token = await self.db.refresh_token.get_one_or_none(refresh_token=refresh_token)
        if token is None:
            raise RefreshTokenNotFoundException()

        await self.db.refresh_token.delete(id=token.id)
        await self.db.commit()

    async def logout_everywhere(self, user_id: int) -> None:
        await self.db.refresh_token.delete(user_id=user_id)
        await self.db.commit()



    async def change_password(self, user_id: int, data: ChangePasswordDTO) -> TokenPairDTO:
        user = await self.db.user.get_orm_by_id(user_id)
        if user is None:
            raise UserNotFoundException()
        if self._is_applicant(user) or user.hashed_password is None:
            raise PasswordLoginNotAllowedException()

        is_valid = await asyncio.to_thread(
            verify_password,
            data.current_password,
            user.hashed_password,
        )
        if not is_valid:
            raise InvalidCurrentPasswordException()
        if data.current_password == data.new_password:
            raise SamePasswordException()

        user.hashed_password = await asyncio.to_thread(hash_password, data.new_password)

        # Прежние сессии закрываем и сразу выдаём новую пару токенов.
        await self.db.refresh_token.delete(user_id=user_id)
        return await self._issue_tokens(user_id)

    # ---------- профиль ----------

    async def get_profile(self, current: CurrentUserDTO) -> UserProfileDTO:
        user = await self.db.user.get_orm_by_id(current.id)
        if user is None:
            raise UserNotFoundException()

        # Суперпользователь имеет все права без явного назначения —
        # фронтенду отдаём полный список кодов.
        if current.is_superuser:
            permissions = [p.code for p in await self.db.permission.get_all()]
        else:
            permissions = sorted(current.permissions)

        return UserDataMapper.map_to_profile(user, permissions)

    # ---------- OneID ----------

    def oneid_authorize(self) -> OneIDAuthorizeDTO:
        return self.oneid_service.build_authorize_url()

    async def oneid_callback(
        self,
        code: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPairDTO:
        profile = await self.oneid_service.exchange_code(code)
        return await self._login_with_oneid_profile(profile, user_agent, ip_address)

    async def oneid_mock_login(
        self,
        data: OneIDMockLoginDTO,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPairDTO:
        if not settings.ONEID_MOCK:
            raise OneIDException("Mock OneID login is disabled")

        profile = OneIDProfileDTO(sub=f"mock-{data.pinfl}", **data.model_dump())
        return await self._login_with_oneid_profile(profile, user_agent, ip_address)

    async def _login_with_oneid_profile(
        self,
        profile: OneIDProfileDTO,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenPairDTO:
        user = await self._find_or_create_oneid_user(profile)

        # Через OneID входят только заявители. Сотрудник Фонда, банка или
        # Совета с таким же ПИНФЛ входит по логину и паролю.
        if not self._is_applicant(user):
            raise OneIDNotForInternalUsersException()

        if user.status != UserStatus.ACTIVE:
            raise UserBlockedException()

        return await self._issue_tokens(user.id, user_agent, ip_address, touch_login=True)

    async def _find_or_create_oneid_user(self, profile: OneIDProfileDTO) -> UserORM:
        """Определяет существующий профиль по sub или ПИНФЛ, иначе создаёт
        заявителя. Идентификационные данные всегда обновляются из источника."""
        user = await self.db.user.get_orm_by_oneid_sub(profile.sub)

        if user is None:
            user = await self.db.user.get_orm_by_pinfl(profile.pinfl)

        if user is None:
            applicant_role = await self.db.role.get_by_code(RoleCode.APPLICANT)
            username = profile.pinfl
            if await self.db.user.get_orm_by_username(username):
                username = f"oneid_{profile.sub}"

            await self.db.user.add(
                UserAddDTO(
                    username=username,
                    role_id=applicant_role.id if applicant_role else None,
                    oneid_sub=profile.sub,
                    full_name=profile.full_name,
                    phone=profile.phone,
                    passport_number=profile.passport_number,
                    pinfl=profile.pinfl,
                    inn=profile.inn,
                    email=profile.email,
                )
            )
            await self.db.flush()
            user = await self.db.user.get_orm_by_oneid_sub(profile.sub)
            return user

        if not self._is_applicant(user):
            raise OneIDNotForInternalUsersException()

        user.oneid_sub = profile.sub
        user.full_name = profile.full_name
        user.pinfl = profile.pinfl
        if profile.phone:
            user.phone = profile.phone
        if profile.passport_number:
            user.passport_number = profile.passport_number
        if profile.inn:
            user.inn = profile.inn
        if profile.email:
            user.email = profile.email

        await self.db.flush()
        return user
