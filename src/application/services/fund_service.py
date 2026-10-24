"""Рабочее окно Фонда: поиск заявок, скоринг, направление в Совет,
выделение ресурсов и завершение."""

from src.account.schemas.user_schema import CurrentUserDTO
from src.application.enums import ApplicationStatus
from src.application.mappers import ApplicationDataMapper
from src.application.schemas.application_schema import (
    ApplicationDetailDTO,
    ApplicationFilterDTO,
    CompleteApplicationDTO,
    CouncilAssignmentAddDTO,
    ResourceAllocationAddDTO,
    ResourceAllocationCreateDTO,
    ScoringAttemptDTO,
    ScoringResultRecordDTO,
    SendToBankDTO,
    SendToCouncilDTO,
)
from src.application.services.base import ApplicationBaseService, now
from src.application.services.scoring_service import ScoringService
from src.common.responses.exceptions import (
    BankNotFoundException,
    BankSubjectTypeMismatchException,
    NoCouncilMembersException,
    ResourceAllocationNotAllowedException,
    UserNotFoundException,
)
from src.rbac.permissions import RoleCode


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
        return {
            "new": by_status[ApplicationStatus.SUBMITTED.value]
            + by_status[ApplicationStatus.SCORING_IN_PROGRESS.value],
            "to_bank": by_status[ApplicationStatus.READY_FOR_BANK.value],
            "to_council": by_status[ApplicationStatus.BANK_APPROVED.value],
            "in_council": by_status[ApplicationStatus.COUNCIL_REVIEW.value],
            "to_allocate": by_status[ApplicationStatus.DEMAND_DOCUMENT_CREATED.value],
            "in_allocation": by_status[ApplicationStatus.RESOURCE_ALLOCATION.value],
            "completed": by_status[ApplicationStatus.COMPLETED.value],
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

    async def record_scoring_result(
        self,
        application_id: int,
        user: CurrentUserDTO,
        data: ScoringResultRecordDTO,
    ) -> ApplicationDetailDTO:
        application = await self.get_for_user(application_id, user)
        await self.scoring_service.record_manual_result(application, data, actor=user)
        await self.db.commit()
        return ApplicationDataMapper.map_to_detail(await self.reload(application_id))

    # ---------- банк ----------

    async def send_to_bank(
        self,
        application_id: int,
        user: CurrentUserDTO,
        data: SendToBankDTO,
    ) -> ApplicationDetailDTO:
        """Фонд выбирает банк для заявки, прошедшей скоринг (READY_FOR_BANK → SENT_TO_BANK).
        Заявитель банк не выбирает."""
        application = await self.get_for_user(application_id, user)

        bank = await self.db.bank.get_one_or_none(id=data.bank_id)
        if bank is None or not bank.is_active:
            raise BankNotFoundException()
        if application.subject_type not in bank.allowed_subject_types:
            raise BankSubjectTypeMismatchException()

        application.bank_id = bank.id
        application.sent_to_bank_at = now()
        await self.transition(
            application,
            ApplicationStatus.SENT_TO_BANK,
            event="sent_to_bank",
            actor=user,
            comment=data.comment or f"Заявка направлена в банк: {bank.name}",
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
                ):
                    raise UserNotFoundException(f"Council member not found: {member_id}")
                members.append(member)
        else:
            members = await self.db.user.get_active_by_role_code(RoleCode.COUNCIL_MEMBER)

        if not members:
            raise NoCouncilMembersException()

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

    # ---------- выделение ресурсов ----------

    async def allocate_resources(
        self,
        application_id: int,
        user: CurrentUserDTO,
        data: ResourceAllocationCreateDTO,
    ) -> ApplicationDetailDTO:
        application = await self.get_for_user(application_id, user)

        # Этап выделения ресурсов начинается только после положительного
        # решения Совета и создания документа «Требование подтверждено».
        if application.status != ApplicationStatus.DEMAND_DOCUMENT_CREATED:
            raise ResourceAllocationNotAllowedException()

        await self.db.resource_allocation.add(
            ResourceAllocationAddDTO(
                application_id=application.id,
                allocated_by_id=user.id,
                **data.model_dump(),
            )
        )
        await self.transition(
            application,
            ApplicationStatus.RESOURCE_ALLOCATION,
            event="resources_allocated",
            actor=user,
            comment=data.details or "Зафиксировано выделение ресурсов",
        )

        await self.db.commit()
        return ApplicationDataMapper.map_to_detail(await self.reload(application_id))

    async def complete(
        self,
        application_id: int,
        user: CurrentUserDTO,
        data: CompleteApplicationDTO,
    ) -> ApplicationDetailDTO:
        application = await self.get_for_user(application_id, user)

        application.completed_at = now()
        await self.transition(
            application,
            ApplicationStatus.COMPLETED,
            event="completed",
            actor=user,
            comment=data.comment or "Процесс завершён",
        )

        await self.db.commit()
        return ApplicationDataMapper.map_to_detail(await self.reload(application_id))
