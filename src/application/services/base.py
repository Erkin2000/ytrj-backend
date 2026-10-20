from datetime import UTC, datetime

from src.account.schemas.user_schema import CurrentUserDTO
from src.application.enums import ApplicationStatus
from src.application.models.application_model import ApplicationORM
from src.application.schemas.application_schema import StatusHistoryAddDTO
from src.application.workflow import BANK_VISIBLE_STATUSES, assert_transition
from src.common.responses.exceptions import (
    ApplicationAccessDeniedException,
    ApplicationNotFoundException,
    PermissionDeniedException,
)
from src.rbac.permissions import RoleCode
from src.utils.base_service import BaseService

# Роли с ограниченным scope. Все остальные роли с правом applications.read
# (Super Admin, Фонд, кастомные роли) видят заявки глобально.
SCOPED_ROLES = {RoleCode.APPLICANT, RoleCode.BANK_EMPLOYEE, RoleCode.COUNCIL_MEMBER}


def now() -> datetime:
    return datetime.now(UTC)


class ApplicationBaseService(BaseService):
    """Общее для всех сервисов заявки: загрузка, проверка scope,
    смена статуса с записью в историю."""

    async def get_orm_or_404(self, application_id: int) -> ApplicationORM:
        application = await self.db.application.get_orm(application_id)
        if application is None:
            raise ApplicationNotFoundException()
        return application

    async def reload(self, application_id: int) -> ApplicationORM:
        """Перечитать заявку после commit: сбрасывает кэш identity map,
        чтобы связи (банк, фото, назначения) отражали изменения."""
        self.db.session.expire_all()
        return await self.get_orm_or_404(application_id)

    # ---------- scope ----------

    @staticmethod
    def has_global_scope(user: CurrentUserDTO) -> bool:
        return user.is_superuser or user.role_code not in SCOPED_ROLES

    @classmethod
    def assert_global_scope(cls, user: CurrentUserDTO) -> None:
        """Рабочее окно Фонда: роли с ограниченным scope (заявитель, банк,
        Совет) сюда не допускаются, даже если у них есть applications.read."""
        if not cls.has_global_scope(user):
            raise PermissionDeniedException()

    async def assert_can_view(self, application: ApplicationORM, user: CurrentUserDTO) -> None:
        """Проверка принадлежности объекта выполняется только здесь, на backend."""
        if self.has_global_scope(user):
            return

        if user.role_code == RoleCode.APPLICANT:
            if application.applicant_id == user.id:
                return

        elif user.role_code == RoleCode.BANK_EMPLOYEE:
            if (
                user.bank_id is not None
                and application.bank_id == user.bank_id
                and application.status in BANK_VISIBLE_STATUSES
            ):
                return

        elif user.role_code == RoleCode.COUNCIL_MEMBER:
            assignment = await self.db.council_assignment.get_orm_for_member(
                application.id, user.id
            )
            if assignment is not None:
                return

        raise ApplicationAccessDeniedException()

    async def get_for_user(self, application_id: int, user: CurrentUserDTO) -> ApplicationORM:
        application = await self.get_orm_or_404(application_id)
        await self.assert_can_view(application, user)
        return application

    # ---------- история и переходы ----------

    async def add_history(
        self,
        application: ApplicationORM,
        to_status: ApplicationStatus,
        event: str,
        actor: CurrentUserDTO | None = None,
        comment: str | None = None,
        from_status: ApplicationStatus | None = None,
    ) -> None:
        await self.db.status_history.add(
            StatusHistoryAddDTO(
                application_id=application.id,
                from_status=from_status,
                to_status=to_status,
                event=event,
                comment=comment,
                actor_id=actor.id if actor else None,
                actor_role=actor.role_code if actor else "SYSTEM",
            )
        )

    async def transition(
        self,
        application: ApplicationORM,
        to_status: ApplicationStatus,
        event: str,
        actor: CurrentUserDTO | None = None,
        comment: str | None = None,
    ) -> None:
        """Проверяет допустимость перехода, меняет статус и пишет историю.
        Коммит делает вызывающий сервис."""
        from_status = application.status
        assert_transition(from_status, to_status)

        application.status = to_status
        await self.db.flush()

        await self.add_history(
            application,
            to_status=to_status,
            event=event,
            actor=actor,
            comment=comment,
            from_status=from_status,
        )
