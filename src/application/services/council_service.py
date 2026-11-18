"""Рабочее окно члена Совета: только направленные ему заявки. Решение по заявке
член Совета выносит в бюллетене, связанном с ней (src/bulletin), — подписью ЭЦП."""

from src.account.schemas.user_schema import CurrentUserDTO
from src.application.enums import ApplicationStatus, CouncilDecision
from src.application.models.application_model import ApplicationORM
from src.application.schemas.application_schema import ApplicationFilterDTO
from src.application.services.base import ApplicationBaseService, now


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

    async def apply_vote(
        self,
        application: ApplicationORM,
        user: CurrentUserDTO,
        decision: CouncilDecision,
        reason: str | None,
        source: str,
    ) -> None:
        """Решение члена Совета по заявке — приходит из подписи бюллетеня, связанного
        с заявкой (`source` — номер бюллетеня для истории). Коммит делает вызывающий.

        Голос пишется в назначение члена Совета; если заявка ещё на рассмотрении
        Совета, применяется правило итога (см. `_finalize_if_ready`)."""
        assignment = await self.db.council_assignment.get_orm_for_member(application.id, user.id)
        if assignment is None or assignment.decision is not None:
            return

        assignment.decision = decision
        assignment.reason = reason
        assignment.decided_at = now()
        await self.db.flush()

        if application.status != ApplicationStatus.COUNCIL_REVIEW:
            return

        label = "Согласен" if decision == CouncilDecision.APPROVED else "Против"
        await self.add_history(
            application,
            to_status=application.status,
            event="council_vote",
            actor=user,
            comment=f"Решение члена Совета по бюллетеню {source}: «{label}»"
            + (f". Комментарий: {reason}" if reason else ""),
            from_status=application.status,
        )

        await self._finalize_if_ready(application, user, decision, reason, source)

    async def _finalize_if_ready(
        self,
        application: ApplicationORM,
        user: CurrentUserDTO,
        decision: CouncilDecision,
        reason: str | None,
        source: str,
    ) -> None:
        """Правило итога (кворум/большинство ещё не согласованы — см. архитектуру):
        «Против» любого члена завершает заявку как COUNCIL_REJECTED;
        «Согласен» всех назначенных — COUNCIL_APPROVED и отправка в банк заявителя."""
        if decision == CouncilDecision.REJECTED:
            application.council_decided_at = now()
            application.council_reject_reason = reason or f"Совет: «Против» (бюллетень {source})"
            await self.transition(
                application,
                ApplicationStatus.COUNCIL_REJECTED,
                event="council_rejected",
                actor=user,
                comment=application.council_reject_reason,
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
            comment=f"Совет: «Согласен» (бюллетень {source})",
        )

        # Утверждённая Советом заявка уходит в банк, выбранный заявителем.
        await self.route_to_chosen_bank(application)
