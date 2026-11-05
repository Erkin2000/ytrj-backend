"""Рабочее окно Фонда: поиск заявок, скоринг, отказ или направление в Совет.
В банк заявка уходит автоматически после утверждения Советом."""

from src.account.schemas.user_schema import CurrentUserDTO
from src.application.enums import ApplicationStatus
from src.application.mappers import ApplicationDataMapper
from src.application.schemas.application_schema import (
    ApplicationDetailDTO,
    ApplicationFilterDTO,
    CouncilAssignmentAddDTO,
    FundRejectDTO,
    ScoringAttemptDTO,
    SendToCouncilDTO,
)
from src.application.services.base import ApplicationBaseService, now
from src.application.services.scoring_service import ScoringService
from src.common.responses.exceptions import (
    NoCouncilMembersException,
    UserNotFoundException,
)
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

    # ---------- Совет ----------

    async def send_to_council(
        self,
        application_id: int,
        user: CurrentUserDTO,
        data: SendToCouncilDTO,
    ) -> ApplicationDetailDTO:
        application = await self.get_for_user(application_id, user)

        if data.council_member_ids:
            members = []
            for member_id in dict.fromkeys(data.council_member_ids):
                member = await self.db.user.get_orm_by_id(member_id)
                if (
                    member is None
                    or member.role is None
                    or member.role.code != RoleCode.COUNCIL_MEMBER
                    or COUNCIL_VOTE not in effective_permissions(member)
                ):
                    raise UserNotFoundException(f"Council member not found: {member_id}")
                members.append(member)
        else:
            # Голосуют только члены Совета с правом решения (права выдаются поштучно).
            members = [
                member
                for member in await self.db.user.get_active_by_role_code(RoleCode.COUNCIL_MEMBER)
                if COUNCIL_VOTE in effective_permissions(member)
            ]

        if not members:
            raise NoCouncilMembersException()

        application.fund_decided_by_id = user.id
        application.fund_decided_at = now()
        application.sent_to_council_at = now()
        application.sent_to_council_by_id = user.id
        await self.transition(
            application,
            ApplicationStatus.COUNCIL_REVIEW,
            event="sent_to_council",
            actor=user,
            comment=data.comment or f"Направлена в Совет ({len(members)} чл.)",
        )

        for member in members:
            await self.db.council_assignment.add(
                CouncilAssignmentAddDTO(
                    application_id=application.id,
                    council_member_id=member.id,
                    assigned_by_id=user.id,
                )
            )

        await self.db.commit()
        return ApplicationDataMapper.map_to_detail(await self.reload(application_id))
