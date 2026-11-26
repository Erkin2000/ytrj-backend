"""Договоры исполнителей: ведёт Фонд (права contracts.*), исполнитель видит свои."""

from sqlalchemy import select

from src.account.models.user_model import UserORM, UserStatus
from src.account.schemas.user_schema import CurrentUserDTO
from src.act.enums import ActStatus, ContractStatus
from src.act.mappers import map_contract
from src.act.models.act_model import ActORM, ContractORM
from src.act.schemas.act_schema import (
    ContractCreateDTO,
    ContractDTO,
    ContractFilterDTO,
    ContractUpdateDTO,
    PersonDTO,
)
from src.act.text import display_name
from src.common.responses.exceptions import (
    ContractApproverException,
    ContractContractorException,
    ContractDatesException,
    ContractInUseException,
    ContractNotFoundException,
    ContractNumberTakenException,
)
from src.rbac.models.role_model import RoleORM
from src.rbac.permissions import RoleCode
from src.utils.base_service import BaseService

SIGNING_PERMISSION = "act_signing.approve"
# Поля, которые входят в подписанное содержимое акта: после отправки акта их не меняют.
LOCKED_FIELDS = {
    "number",
    "signed_on",
    "contractor_id",
    "contractor_name",
    "approver_name",
    "approver_title",
}
LOCKING_STATUSES = (ActStatus.SUBMITTED, ActStatus.ACCEPTED, ActStatus.SIGNED)


class ContractService(BaseService):
    async def get_orm_or_404(self, contract_id: int) -> ContractORM:
        contract = await self.db.contract.get_orm(contract_id)
        if contract is None:
            raise ContractNotFoundException()
        return contract

    async def _dto(self, contract: ContractORM) -> ContractDTO:
        counts = await self.db.contract.acts_counts([contract.id])
        return map_contract(contract, counts.get(contract.id, 0))

    async def _page(self, stmt, page, per_page) -> dict:
        data = await self.db.contract.paginate_list(stmt, page, per_page, mapper=lambda c: c)
        counts = await self.db.contract.acts_counts([c.id for c in data["items"]])
        data["items"] = [map_contract(c, counts.get(c.id, 0)) for c in data["items"]]
        return data

    # ---------- Фонд ----------

    async def get_list(self, filters: ContractFilterDTO, page, per_page) -> dict:
        return await self._page(self.db.contract.list_stmt(filters), page, per_page)

    async def get_detail(self, contract_id: int) -> ContractDTO:
        return await self._dto(await self.get_orm_or_404(contract_id))

    async def people(self) -> dict[str, list[PersonDTO]]:
        """Кого можно выбрать в договоре: исполнители (роль CONTRACTOR с ПИНФЛ) и
        руководители (сотрудники с правом act_signing.approve и ПИНФЛ)."""
        contractors = await self.db.user.get_active_by_role_code(RoleCode.CONTRACTOR)
        stmt = (
            select(UserORM)
            .join(RoleORM, RoleORM.id == UserORM.role_id)
            .where(
                UserORM.status == UserStatus.ACTIVE,
                UserORM.pinfl.is_not(None),
                RoleORM.code.not_in([RoleCode.APPLICANT, RoleCode.CONTRACTOR]),
            )
            .order_by(UserORM.full_name)
        )
        approvers = []
        for user in (await self.db.session.scalars(stmt)).all():
            access = await self.db.user.get_access(user.id)
            if access and SIGNING_PERMISSION in access.permissions:
                approvers.append(PersonDTO(id=user.id, full_name=user.full_name))
        return {
            "contractors": [
                PersonDTO(id=u.id, full_name=u.full_name) for u in contractors if u.pinfl
            ],
            "approvers": approvers,
        }

    async def create(self, data: ContractCreateDTO, user: CurrentUserDTO) -> ContractDTO:
        if data.end_date < data.start_date:
            raise ContractDatesException()
        if await self.db.contract.number_taken(data.number):
            raise ContractNumberTakenException()
        contractor = await self._contractor(data.contractor_id)
        approver = await self._approver(data.approver_id)

        contract = ContractORM(
            number=data.number,
            signed_on=data.signed_on,
            contractor_id=contractor.id,
            contractor_name=data.contractor_name or display_name(contractor.full_name),
            position=data.position,
            subject=data.subject,
            start_date=data.start_date,
            end_date=data.end_date,
            amount=data.amount,
            approver_id=approver.id,
            approver_name=data.approver_name or display_name(approver.full_name),
            approver_title=data.approver_title,
            status=ContractStatus.ACTIVE,
            created_by_id=user.id,
        )
        await self.db.contract.add_orm(contract)
        await self.db.commit()
        return await self.get_detail(contract.id)

    async def update(self, contract_id: int, data: ContractUpdateDTO) -> ContractDTO:
        contract = await self.get_orm_or_404(contract_id)
        values = data.model_dump(exclude_unset=True)

        changed_locked = {
            k for k in values.keys() & LOCKED_FIELDS if values[k] != getattr(contract, k)
        }
        if changed_locked and await self._has_locking_acts(contract.id):
            raise ContractInUseException(
                "The contract has submitted or signed reports: its number, date, parties and "
                "names in the report cannot change",
                errors=[
                    {"field": f, "message": "Locked by submitted reports"}
                    for f in sorted(changed_locked)
                ],
            )
        if "number" in values and await self.db.contract.number_taken(
            values["number"], contract.id
        ):
            raise ContractNumberTakenException()
        if "contractor_id" in values:
            contractor = await self._contractor(values["contractor_id"])
            values.setdefault("contractor_name", display_name(contractor.full_name))
        if "approver_id" in values:
            approver = await self._approver(values["approver_id"])
            values.setdefault("approver_name", display_name(approver.full_name))

        for key, value in values.items():
            if value is None and key not in {"position", "amount"}:
                continue
            setattr(contract, key, value)
        if contract.end_date < contract.start_date:
            raise ContractDatesException()
        await self.db.flush()
        await self.db.commit()
        return await self.get_detail(contract.id)

    async def delete(self, contract_id: int) -> None:
        contract = await self.get_orm_or_404(contract_id)
        if await self.db.act.count_for_contract(contract.id):
            raise ContractInUseException()
        await self.db.contract.delete_orm(contract)
        await self.db.commit()

    # ---------- исполнитель ----------

    async def my_list(
        self, user: CurrentUserDTO, filters: ContractFilterDTO, page, per_page
    ) -> dict:
        return await self._page(
            self.db.contract.list_stmt(filters, contractor_id=user.id), page, per_page
        )

    # ---------- проверки ----------

    async def _has_locking_acts(self, contract_id: int) -> bool:
        stmt = select(ActORM.id).where(
            ActORM.contract_id == contract_id, ActORM.status.in_(LOCKING_STATUSES)
        )
        return (await self.db.session.scalar(stmt.limit(1))) is not None

    async def _contractor(self, user_id: int) -> UserORM:
        user = await self.db.user.get_orm_by_id(user_id)
        if (
            user is None
            or user.status != UserStatus.ACTIVE
            or not user.pinfl
            or user.role is None
            or user.role.code != RoleCode.CONTRACTOR
        ):
            raise ContractContractorException()
        return user

    async def _approver(self, user_id: int) -> UserORM:
        user = await self.db.user.get_orm_by_id(user_id)
        access = await self.db.user.get_access(user_id) if user else None
        if (
            user is None
            or access is None
            or not access.is_active
            or not user.pinfl
            or not access.has_permission(SIGNING_PERMISSION)
            or access.role_code in (RoleCode.APPLICANT, RoleCode.CONTRACTOR)
        ):
            raise ContractApproverException()
        return user
