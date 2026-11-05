"""Рабочее окно члена Совета: только направленные ему заявки и решение
«Согласен» / «Отклоняю»."""

from src.account.schemas.user_schema import CurrentUserDTO
from src.application.enums import ApplicationStatus, CouncilDecision
from src.application.mappers import ApplicationDataMapper
from src.application.models.application_model import ApplicationORM
from src.application.schemas.application_schema import (
    ApplicationDetailDTO,
    ApplicationFilterDTO,
    CouncilDecisionDTO,
)
from src.application.services.base import ApplicationBaseService, now
from src.common.responses.exceptions import (
    CouncilAssignmentNotFoundException,
    CouncilDecisionAlreadyMadeException,
    InvalidStatusTransitionException,
    RejectReasonRequiredException,
)


class CouncilService(ApplicationBaseService):
    async def get_assigned_applications(
        self,
        user: CurrentUserDTO,
        filters: ApplicationFilterDTO,
        page: int | None,
        per_page: int | None,
        pending_only: bool = False,
    ) -> dict:
        if pending_only:
            filters = filters.model_copy(update={"status": ApplicationStatus.COUNCIL_REVIEW})

        return await self.db.application.get_all(
            filters,
            page=page,
            per_page=per_page,
            council_member_id=None if self.has_global_scope(user) else user.id,
        )

    async def get_counters(self, user: CurrentUserDTO) -> dict[str, int]:
        by_status = await self.db.application.count_by_status(
            council_member_id=None if self.has_global_scope(user) else user.id,
        )
        return {
            "pending": by_status[ApplicationStatus.COUNCIL_REVIEW.value],
            # утверждённые Советом — в том числе ушедшие дальше в банк
            "approved": sum(
                by_status[s.value]
                for s in (
                    ApplicationStatus.COUNCIL_APPROVED,
                    ApplicationStatus.SENT_TO_BANK,
                    ApplicationStatus.BANK_REVIEW,
                    ApplicationStatus.BANK_APPROVED,
                    ApplicationStatus.BANK_REJECTED,
                    ApplicationStatus.COMPLETED,
                )
            ),
            "rejected": by_status[ApplicationStatus.COUNCIL_REJECTED.value],
        }

    async def decide(
        self,
        application_id: int,
        user: CurrentUserDTO,
        data: CouncilDecisionDTO,
    ) -> ApplicationDetailDTO:
        application = await self.get_for_user(application_id, user)

        if application.status != ApplicationStatus.COUNCIL_REVIEW:
            raise InvalidStatusTransitionException("Application is not under council review")

        assignment = await self.db.council_assignment.get_orm_for_member(application.id, user.id)
        if assignment is None:
            raise CouncilAssignmentNotFoundException()
        if assignment.decision is not None:
            raise CouncilDecisionAlreadyMadeException()
        if data.decision == CouncilDecision.REJECTED and not data.reason:
            raise RejectReasonRequiredException()

        assignment.decision = data.decision
        assignment.reason = data.reason
        assignment.decided_at = now()
        await self.db.flush()

        await self.add_history(
            application,
            to_status=application.status,
            event="council_vote",
            actor=user,
            comment=f"Решение члена Совета: {'Согласен' if data.decision == CouncilDecision.APPROVED else 'Отклоняю'}"
            + (f". Причина: {data.reason}" if data.reason else ""),
            from_status=application.status,
        )

        await self._finalize_if_ready(application, user, data)

        await self.db.commit()
        return ApplicationDataMapper.map_to_detail(await self.reload(application_id))

    async def _finalize_if_ready(
        self,
        application: ApplicationORM,
        user: CurrentUserDTO,
        data: CouncilDecisionDTO,
    ) -> None:
        """Правило итога (кворум/большинство ещё не согласованы — см. архитектуру):
        «Отклоняю» любого члена завершает заявку как COUNCIL_REJECTED;
        «Согласен» всех назначенных — COUNCIL_APPROVED и отправка в банк заявителя."""
        if data.decision == CouncilDecision.REJECTED:
            application.council_decided_at = now()
            application.council_reject_reason = data.reason
            await self.transition(
                application,
                ApplicationStatus.COUNCIL_REJECTED,
                event="council_rejected",
                actor=user,
                comment=data.reason,
            )
            return

        assignments = await self.db.council_assignment.get_orm_for_application(application.id)
        if any(a.decision != CouncilDecision.APPROVED for a in assignments):
            return

        application.council_decided_at = now()
        await self.transition(
            application,
            ApplicationStatus.COUNCIL_APPROVED,
            event="council_approved",
            actor=user,
            comment="Совет: «Согласен»",
        )

        # Утверждённая Советом заявка уходит в банк, выбранный заявителем.
        await self.route_to_chosen_bank(application)
