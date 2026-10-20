"""Каталог банков (Super Admin) и этап банка (ответственный сотрудник банка)."""

from src.account.schemas.user_schema import CurrentUserDTO
from src.application.enums import ApplicationStatus, BankDecision, SubjectType
from src.application.mappers import ApplicationDataMapper
from src.application.schemas.application_schema import (
    ApplicationDetailDTO,
    ApplicationFilterDTO,
    BankDecisionDTO,
)
from src.application.schemas.bank_schema import (
    BankAddDTO,
    BankDTO,
    BankRequestAddDTO,
    BankRequestUpdateDTO,
    BankUpdateDTO,
)
from src.application.services.base import ApplicationBaseService, now
from src.application.workflow import BANK_BUCKETS
from src.common.responses.exceptions import (
    BankDecisionAlreadyMadeException,
    BankNotFoundException,
    BankScopeRequiredException,
    ConflictException,
    RejectReasonRequiredException,
)


class BankService(ApplicationBaseService):
    # ---------- каталог ----------

    async def get_banks(
        self, subject_type: SubjectType | None, only_active: bool = True
    ) -> list[BankDTO]:
        return await self.db.bank.get_all(subject_type=subject_type, only_active=only_active)

    async def get_bank(self, bank_id: int) -> BankDTO:
        bank = await self.db.bank.get_one_or_none(id=bank_id)
        if bank is None:
            raise BankNotFoundException()
        return bank

    async def add_bank(self, data: BankRequestAddDTO) -> BankDTO:
        if await self.db.bank.exists(code=data.code):
            raise ConflictException("Bank with this code already exists")

        bank = await self.db.bank.add(BankAddDTO(**data.model_dump()))
        await self.db.commit()
        return bank

    async def update_bank(self, bank_id: int, data: BankRequestUpdateDTO) -> BankDTO:
        await self.get_bank(bank_id)
        update_data = data.model_dump(exclude_unset=True)
        await self.db.bank.edit(BankUpdateDTO(**update_data), exclude_unset=True, id=bank_id)
        await self.db.commit()
        return await self.get_bank(bank_id)

    async def deactivate_bank(self, bank_id: int) -> None:
        await self.get_bank(bank_id)
        await self.db.bank.edit(BankUpdateDTO(is_active=False), exclude_unset=True, id=bank_id)
        await self.db.commit()

    # ---------- рабочее окно банка ----------

    @staticmethod
    def _bank_scope(user: CurrentUserDTO) -> int | None:
        """Сотрудник банка видит только свой банк. Фонд/Super Admin — все."""
        if ApplicationBaseService.has_global_scope(user):
            return None
        if user.bank_id is None:
            raise BankScopeRequiredException()
        return user.bank_id

    async def get_bank_applications(
        self,
        user: CurrentUserDTO,
        bucket: str | None,
        filters: ApplicationFilterDTO,
        page: int | None,
        per_page: int | None,
    ) -> dict:
        bank_id = self._bank_scope(user)

        statuses = (
            BANK_BUCKETS.get(bucket)
            if bucket
            else BANK_BUCKETS["new"] | BANK_BUCKETS["in_review"] | BANK_BUCKETS["completed"]
        )
        filters = filters.model_copy(update={"statuses": sorted(statuses)})

        return await self.db.application.get_all(
            filters,
            page=page,
            per_page=per_page,
            bank_id=bank_id if bank_id is not None else filters.bank_id,
        )

    async def get_counters(self, user: CurrentUserDTO) -> dict[str, int]:
        bank_id = self._bank_scope(user)
        by_status = await self.db.application.count_by_status(bank_id=bank_id)
        return {
            bucket: sum(by_status[s.value] for s in statuses)
            for bucket, statuses in BANK_BUCKETS.items()
        }

    async def accept(self, application_id: int, user: CurrentUserDTO) -> ApplicationDetailDTO:
        application = await self.get_for_user(application_id, user)

        application.bank_accepted_by_id = user.id
        application.bank_accepted_at = now()
        await self.transition(
            application,
            ApplicationStatus.BANK_REVIEW,
            event="bank_accepted",
            actor=user,
            comment="Банк принял заявку в рассмотрение",
        )
        await self.db.commit()
        return ApplicationDataMapper.map_to_detail(await self.reload(application_id))

    async def decide(
        self,
        application_id: int,
        user: CurrentUserDTO,
        data: BankDecisionDTO,
    ) -> ApplicationDetailDTO:
        application = await self.get_for_user(application_id, user)

        # После направления окончательного результата изменить его нельзя.
        if application.bank_decision is not None:
            raise BankDecisionAlreadyMadeException()

        if data.decision == BankDecision.REJECTED and not data.reason:
            raise RejectReasonRequiredException()

        application.bank_decision = data.decision
        application.bank_decision_reason = data.reason
        application.bank_decided_by_id = user.id
        application.bank_decided_at = now()

        if data.decision == BankDecision.APPROVED:
            await self.transition(
                application,
                ApplicationStatus.BANK_APPROVED,
                event="bank_approved",
                actor=user,
                comment=data.reason or "Банк: заявитель отвечает требованиям Фонда",
            )
        else:
            await self.transition(
                application,
                ApplicationStatus.BANK_REJECTED,
                event="bank_rejected",
                actor=user,
                comment=data.reason,
            )

        await self.db.commit()
        return ApplicationDataMapper.map_to_detail(await self.reload(application_id))
