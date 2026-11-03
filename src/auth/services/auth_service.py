import asyncio
import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from src.account.mappers import UserDataMapper
from src.account.models.user_model import UserORM, UserStatus
from src.account.schemas.user_schema import (
    CurrentUserDTO,
    UserAddDTO,
    UserProfileDTO,
    UserProfileUpdateDTO,
)
from src.auth.schemas.auth_schema import (
    ChangePasswordDTO,
    LoginDTO,
    LoginRedirectDTO,
    LoginResultDTO,
    LoginTokensDTO,
    RefreshTokenCreateDTO,
    SSOAuthorizeDTO,
    SSOCallbackDTO,
    SSOMockLoginDTO,
    SSOProfileDTO,
    SSOSite,
    TicketExchangeDTO,
    TokenPairDTO,
)
from src.auth.services.password_service import hash_password, verify_password
from src.auth.services.sso_service import YiaSSOService
from src.auth.services.token_service import TokenService
from src.common.responses.exceptions import (
    ApplicantLoginViaSSOException,
    ExpiredRefreshTokenException,
    InvalidCredentialsException,
    InvalidCurrentPasswordException,
    InvalidLoginTicketException,
    PasswordLoginNotAllowedException,
    RefreshTokenNotFoundException,
    RefreshTokenRevokedException,
    SamePasswordException,
    SSOException,
    UserBlockedException,
    UserNotFoundException,
)
from src.common.urls import append_query, origin_of
from src.config import settings
from src.rbac.permissions import RoleCode
from src.utils.base_service import BaseService

logger = logging.getLogger(__name__)


class AuthService(BaseService):
    token_service = TokenService()
    sso_service = YiaSSOService()

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
        page_origin: str | None = None,
        base_url: str | None = None,
    ) -> LoginResultDTO:
        user = await self.db.user.get_orm_by_username(data.username)

        is_valid = await asyncio.to_thread(
            verify_password,
            data.password,
            user.hashed_password if user else None,
        )

        if user is None or not is_valid:
            raise InvalidCredentialsException()

        # Заявители входят только через YIA SSO; пароль — для внутренних ролей.
        if self._is_applicant(user):
            raise ApplicantLoginViaSSOException()

        if user.status != UserStatus.ACTIVE:
            raise UserBlockedException()

        return await self._complete_login(user, user_agent, ip_address, page_origin, base_url)

    # ---------- кабинет роли и билет входа ----------

    @staticmethod
    def home_url(role_code: str | None) -> str:
        """Адрес кабинета роли из ROLE_HOME_URLS (иначе ROLE_HOME_URL_DEFAULT)."""
        return settings.ROLE_HOME_URLS.get(role_code or "", settings.ROLE_HOME_URL_DEFAULT)

    @staticmethod
    def _hash_ticket(ticket: str) -> str:
        return hashlib.sha256(ticket.encode()).hexdigest()

    async def _issue_ticket_url(self, user: UserORM) -> str:
        """Создаёт одноразовый билет и возвращает адрес кабинета роли с ним."""
        ticket = secrets.token_urlsafe(32)
        await self.db.login_ticket.purge_stale()
        await self.db.login_ticket.add(
            ticket_hash=self._hash_ticket(ticket),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(seconds=settings.LOGIN_TICKET_TTL_SECONDS),
        )
        role_code = user.role.code if user.role else None
        return append_query(self.home_url(role_code), [("ticket", ticket)])

    async def _complete_login(
        self,
        user: UserORM,
        user_agent: str | None,
        ip_address: str | None,
        page_origin: str | None = None,
        base_url: str | None = None,
    ) -> LoginResultDTO:
        """Общий финал входа.

        page_origin — сайт страницы, с которой выполнен вход (заголовок Origin
        или SSO_FRONTEND_REDIRECT_URL); base_url — адрес бэкенда для относительных
        ROLE_HOME_URLS. Кабинет на том же сайте — только токены (LoginTokensDTO);
        на другом поддомене — только role и redirect_url с билетом (LoginRedirectDTO),
        localStorage у поддоменов свой."""
        role_code = user.role.code if user.role else None
        home = self.home_url(role_code)

        if page_origin and origin_of(home, base_url or "") == page_origin:
            tokens = await self._issue_tokens(user.id, user_agent, ip_address, touch_login=True)
            return LoginTokensDTO(
                access_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
                expires_in=tokens.expires_in,
            )

        redirect_url = await self._issue_ticket_url(user)
        await self.db.user.touch_last_login(user.id)
        await self.db.commit()
        return LoginRedirectDTO(role=role_code, redirect_url=redirect_url)

    async def exchange_ticket(
        self,
        data: TicketExchangeDTO,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPairDTO:
        user_id = await self.db.login_ticket.consume(self._hash_ticket(data.ticket))
        if user_id is None:
            raise InvalidLoginTicketException()

        user = await self.db.user.get_orm_by_id(user_id)
        if user is None:
            raise InvalidLoginTicketException()
        if user.status != UserStatus.ACTIVE:
            raise UserBlockedException()

        # _issue_tokens делает commit — билет гасится в той же транзакции.
        return await self._issue_tokens(user.id, user_agent, ip_address)

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

    async def update_profile(
        self, current: CurrentUserDTO, data: UserProfileUpdateDTO
    ) -> UserProfileDTO:
        """Пользователь дополняет собственный профиль: телефон, паспорт, ИНН,
        email, пол, дата рождения. Ф.И.О. и ПИНФЛ приходят из YIA SSO и в DTO
        отсутствуют (extra=forbid), поэтому изменить их этим методом нельзя."""
        user = await self.db.user.get_orm_by_id(current.id)
        if user is None:
            raise UserNotFoundException()

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)

        await self.db.commit()
        return await self.get_profile(current)

    # ---------- YIA SSO ----------

    def sso_authorize(self, site: SSOSite = SSOSite.MAIN) -> SSOAuthorizeDTO:
        return self.sso_service.build_authorize_url(site)

    async def sso_callback(
        self,
        data: SSOCallbackDTO,
        user_agent: str | None = None,
        ip_address: str | None = None,
        page_origin: str | None = None,
        base_url: str | None = None,
    ) -> LoginResultDTO:
        # Порядок как в sso_integration.md: сверяем state, смотрим error,
        # затем сразу меняем code (живёт 60 секунд) на профиль.
        site = self.sso_service.verify_state(data.state)
        self.sso_service.check_callback_error(data.error)
        if not data.code:
            raise SSOException("SSO code is missing")

        profile = await self.sso_service.exchange_code(data.code, site)
        return await self._login_with_sso_profile(
            profile, user_agent, ip_address, page_origin, base_url
        )

    async def sso_mock_login(
        self,
        data: SSOMockLoginDTO,
        user_agent: str | None = None,
        ip_address: str | None = None,
        page_origin: str | None = None,
        base_url: str | None = None,
    ) -> LoginResultDTO:
        if not settings.SSO_MOCK:
            raise SSOException("Mock SSO login is disabled")

        profile = SSOProfileDTO(
            sub=data.sub or f"mock-{data.pinfl}",
            full_name=data.full_name,
            pinfl=data.pinfl,
        )
        return await self._login_with_sso_profile(
            profile, user_agent, ip_address, page_origin, base_url
        )

    async def _login_with_sso_profile(
        self,
        profile: SSOProfileDTO,
        user_agent: str | None,
        ip_address: str | None,
        page_origin: str | None = None,
        base_url: str | None = None,
    ) -> LoginResultDTO:
        # Через YIA Portal входят все роли: заявитель создаётся автоматически,
        # сотрудник (Фонд, банк, Совет) заранее заведён Super Admin по ПИНФЛ.
        user = await self._find_or_create_sso_user(profile)

        if user.status != UserStatus.ACTIVE:
            raise UserBlockedException()

        return await self._complete_login(user, user_agent, ip_address, page_origin, base_url)

    async def _find_or_create_sso_user(self, profile: SSOProfileDTO) -> UserORM:
        """Определяет существующий профиль по sub портала, затем по ПИНФЛ
        (пользователь, заведённый до перехода на YIA SSO), иначе создаёт
        заявителя. Сотрудники находятся по ПИНФЛ, который указал Super Admin.
        Ф.И.О. и ПИНФЛ всегда обновляются из источника."""
        user = await self.db.user.get_orm_by_sso_sub(profile.sub)

        if user is None and profile.pinfl:
            user = await self.db.user.get_orm_by_pinfl(profile.pinfl)

        if user is None:
            return await self._create_applicant(profile)

        if user.sso_sub and user.sso_sub != profile.sub:
            # Профиль с этим ПИНФЛ был привязан к другой учётке портала.
            logger.warning(
                "YIA SSO sub changed for user %s (pinfl match): %s -> %s",
                user.id,
                user.sso_sub,
                profile.sub,
            )
        user.sso_sub = profile.sub
        user.full_name = profile.full_name
        if profile.pinfl and profile.pinfl != user.pinfl:
            if user.pinfl is None:
                user.pinfl = profile.pinfl
            else:
                # ПИНФЛ в профиле уже есть и отличается от переданного порталом —
                # не перезаписываем молча, это повод для ручной проверки.
                logger.warning(
                    "YIA SSO pinfl mismatch for user %s: stored=%s, portal=%s",
                    user.id,
                    user.pinfl,
                    profile.pinfl,
                )

        await self.db.flush()
        return user

    async def _create_applicant(self, profile: SSOProfileDTO) -> UserORM:
        applicant_role = await self.db.role.get_by_code(RoleCode.APPLICANT)

        username = profile.pinfl or f"sso_{profile.sub}"
        if await self.db.user.get_orm_by_username(username):
            username = f"sso_{profile.sub}"

        await self.db.user.add(
            UserAddDTO(
                username=username,
                role_id=applicant_role.id if applicant_role else None,
                sso_sub=profile.sub,
                full_name=profile.full_name,
                pinfl=profile.pinfl,
                region=profile.region,
            )
        )
        await self.db.flush()
        user = await self.db.user.get_orm_by_sso_sub(profile.sub)
        if user is None:
            raise UserNotFoundException()
        return user
