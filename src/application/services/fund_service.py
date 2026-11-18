"""Рабочее окно Фонда: поиск заявок, скоринг, отказ. В Совет заявка уходит через
бюллетень (src/bulletin), в банк — автоматически после утверждения Советом."""

from src.account.models.user_model import UserORM
from src.account.schemas.user_schema import CurrentUserDTO
from src.application.enums import ApplicationStatus
from src.application.mappers import ApplicationDataMapper
from src.application.models.application_model import ApplicationORM
from src.application.schemas.application_schema import (
    ApplicationDetailDTO,
    ApplicationFilterDTO,
    CouncilAssignmentAddDTO,
    FundRejectDTO,
    ScoringAttemptDTO,
)
from src.application.services.base import ApplicationBaseService, now
from src.application.services.scoring_service import ScoringService
from src.rbac.access import effective_permissions
from src.rbac.permissions import RoleCode

COUNCIL_VOTE = "council_review.approve"


class FundService(ApplicationBaseService):
    @property
    def scoring_service(self) -> ScoringService:
        return ScoringService(self.db)

    # ---------- чтение ----------

    async def get_applications(
        self,
        user: CurrentUserDTO,
        filters: ApplicationFilterDTO,
        page: int | None,
        per_page: int | None,
    ) -> dict:
        self.assert_global_scope(user)
        return await self.db.application.get_all(filters, page=page, per_page=per_page)

    async def get_counters(self, user: CurrentUserDTO) -> dict[str, int]:
        self.assert_global_scope(user)
        by_status = await self.db.application.count_by_status()
        s = ApplicationStatus
        return {
            "new": by_status[s.SUBMITTED.value] + by_status[s.SCORING_IN_PROGRESS.value],
            "to_review": by_status[s.FUND_REVIEW.value],
            "in_council": by_status[s.COUNCIL_REVIEW.value],
            "in_bank": by_status[s.SENT_TO_BANK.value] + by_status[s.BANK_REVIEW.value],
            "completed": by_status[s.COMPLETED.value],
            "rejected": sum(
                by_status[x.value]
                for x in (
                    s.SCORING_FAILED,
                    s.ELIGIBILITY_FAILED,
                    s.FUND_REJECTED,
                    s.COUNCIL_REJECTED,
                    s.BANK_REJECTED,
                )
            ),
            "by_status": by_status,
        }

    async def get_detail(self, application_id: int, user: CurrentUserDTO) -> ApplicationDetailDTO:
        application = await self.get_for_user(application_id, user)
        return ApplicationDataMapper.map_to_detail(application)

    # ---------- скоринг ----------

    async def get_scoring(
        self, application_id: int, user: CurrentUserDTO
    ) -> list[ScoringAttemptDTO]:
        await self.get_for_user(application_id, user)
        return await self.scoring_service.get_attempts(application_id)

    async def retry_scoring(
        self, application_id: int, user: CurrentUserDTO
    ) -> ApplicationDetailDTO:
        application = await self.get_for_user(application_id, user)
        await self.scoring_service.retry(application, actor=user)
        await self.db.commit()
        return ApplicationDataMapper.map_to_detail(await self.reload(application_id))

    # ---------- решение Фонда ----------

    async def reject(
        self,
        application_id: int,
        user: CurrentUserDTO,
        data: FundRejectDTO,
    ) -> ApplicationDetailDTO:
        """FUND_REVIEW → FUND_REJECTED: Фонд отклоняет заявку до Совета, причина обязательна."""
        application = await self.get_for_user(application_id, user)

        application.fund_decided_by_id = user.id
        application.fund_decided_at = now()
        application.fund_reject_reason = data.reason
        await self.transition(
            application,
            ApplicationStatus.FUND_REJECTED,
            event="fund_rejected",
            actor=user,
            comment=data.reason,
        )

        await self.db.commit()
        return ApplicationDataMapper.map_to_detail(await self.reload(application_id))

    # ---------- Совет: через бюллетень (src/bulletin) ----------

    async def eligible_council_members(self) -> list[UserORM]:
        """Кому уходит бюллетень: все активные члены Совета с правом решения
        (права выдаются поштучно) и с ПИНФЛ — без ПИНФЛ подписать ключом E-IMZO нельзя."""
        return [
            member
            for member in await self.db.user.get_active_by_role_code(RoleCode.COUNCIL_MEMBER)
            if member.pinfl and COUNCIL_VOTE in effective_permissions(member)
        ]

    async def send_to_council(
        self, application: ApplicationORM, user: CurrentUserDTO, bulletin_number: str
    ) -> None:
        """FUND_REVIEW → COUNCIL_REVIEW при создании бюллетеня, связанного с заявкой.
        Члены Совета назначаются при отправке бюллетеня (`assign_council`)."""
        application.fund_decided_by_id = user.id
        application.fund_decided_at = now()
        application.sent_to_council_at = now()
        application.sent_to_council_by_id = user.id
        await self.transition(
            application,
            ApplicationStatus.COUNCIL_REVIEW,
            event="sent_to_council",
            actor=user,
            comment=f"Направлена в Совет: бюллетень {bulletin_number}",
        )

    async def assign_council(
        self, application: ApplicationORM, members: list[UserORM], assigned_by_id: int | None
    ) -> None:
        """Назначения членов Совета по заявке — при отправке бюллетеня. Дают членам
        Совета доступ к заявке и хранят их голоса."""
        for member in members:
            if await self.db.council_assignment.get_orm_for_member(application.id, member.id):
                continue
            await self.db.council_assignment.add(
                CouncilAssignmentAddDTO(
                    application_id=application.id,
                    council_member_id=member.id,
                    assigned_by_id=assigned_by_id,
                )
            )

    async def return_from_council(
        self, application: ApplicationORM, user: CurrentUserDTO, comment: str
    ) -> None:
        """COUNCIL_REVIEW → FUND_REVIEW: бюллетень по заявке удалён или аннулирован до
        итогового решения. Назначения и голоса членов Совета снимаются (они остаются
        в бюллетене и в истории заявки)."""
        if application.status != ApplicationStatus.COUNCIL_REVIEW:
            return
        await self.db.council_assignment.delete(application_id=application.id)
        application.sent_to_council_at = None
        application.sent_to_council_by_id = None
        await self.transition(
            application,
            ApplicationStatus.FUND_REVIEW,
            event="returned_from_council",
            actor=user,
            comment=comment,
        )
