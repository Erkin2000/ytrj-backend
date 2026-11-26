from datetime import date

from sqlalchemy import Select, func, or_, select

from src.act.enums import PERIOD_HOLDING_STATUSES, ActStatus, FundActTab
from src.act.models.act_model import ActAttachmentORM, ActORM, ContractORM
from src.act.schemas.act_schema import ContractFilterDTO, FundActFilterDTO, MyActFilterDTO
from src.utils.base_rep.base_rep import BaseRepository

TAB_STATUSES = {
    FundActTab.TO_REVIEW: [ActStatus.SUBMITTED],
    FundActTab.TO_SIGN: [ActStatus.ACCEPTED],
    FundActTab.SIGNED: [ActStatus.SIGNED],
    FundActTab.RETURNED: [ActStatus.RETURNED],
    FundActTab.CANCELLED: [ActStatus.CANCELLED],
}
# Черновики исполнителя Фонду не показываются: он видит акт с момента отправки.
FUND_VISIBLE = [s for s in ActStatus if s != ActStatus.DRAFT]


class ContractRepository(BaseRepository):
    model = ContractORM

    async def get_orm(self, contract_id: int) -> ContractORM | None:
        return await self.session.get(self.model, contract_id, populate_existing=True)

    async def number_taken(self, number: str, exclude_id: int | None = None) -> bool:
        stmt = select(func.count()).where(func.lower(self.model.number) == number.lower())
        if exclude_id is not None:
            stmt = stmt.where(self.model.id != exclude_id)
        return bool(await self.session.scalar(stmt))

    async def add_orm(self, contract: ContractORM) -> ContractORM:
        self.session.add(contract)
        await self.session.flush()
        return contract

    async def delete_orm(self, contract: ContractORM) -> None:
        await self.session.delete(contract)
        await self.session.flush()

    def list_stmt(self, filters: ContractFilterDTO, contractor_id: int | None = None) -> Select:
        stmt = select(self.model)
        if contractor_id is not None:
            stmt = stmt.where(self.model.contractor_id == contractor_id)
        if filters.status:
            stmt = stmt.where(self.model.status == filters.status)
        if filters.contractor_id:
            stmt = stmt.where(self.model.contractor_id == filters.contractor_id)
        if filters.search:
            pattern = f"%{filters.search.strip()}%"
            stmt = stmt.where(
                or_(self.model.number.ilike(pattern), self.model.contractor_name.ilike(pattern))
            )
        return stmt.order_by(self.model.id.desc())

    async def paginate_list(self, stmt: Select, page, per_page, mapper) -> dict:
        return await self.paginate(stmt, page, per_page, mapper=mapper)

    async def acts_counts(self, contract_ids: list[int]) -> dict[int, int]:
        if not contract_ids:
            return {}
        rows = await self.session.execute(
            select(ActORM.contract_id, func.count())
            .where(ActORM.contract_id.in_(contract_ids))
            .group_by(ActORM.contract_id)
        )
        return dict(rows.all())

    async def has_signed_acts(self, contract_id: int) -> bool:
        return bool(
            await self.session.scalar(
                select(func.count()).where(
                    ActORM.contract_id == contract_id, ActORM.status == ActStatus.SIGNED
                )
            )
        )


class ActRepository(BaseRepository):
    model = ActORM

    async def get_orm(self, act_id: int, *, for_update: bool = False) -> ActORM | None:
        stmt = (
            select(self.model)
            .where(self.model.id == act_id)
            .execution_options(populate_existing=True)
        )
        if for_update:
            stmt = stmt.with_for_update(of=self.model)
        return await self.session.scalar(stmt)

    async def get_orm_by_public_id(self, public_id: str) -> ActORM | None:
        return await self.session.scalar(
            select(self.model).where(self.model.public_id == public_id)
        )

    async def add_orm(self, act: ActORM) -> ActORM:
        self.session.add(act)
        await self.session.flush()
        return act

    async def delete_orm(self, act: ActORM) -> None:
        await self.session.delete(act)
        await self.session.flush()

    async def get_attachment(self, act_id: int, attachment_id: int) -> ActAttachmentORM | None:
        return await self.session.scalar(
            select(ActAttachmentORM).where(
                ActAttachmentORM.id == attachment_id, ActAttachmentORM.act_id == act_id
            )
        )

    async def count_for_contract(self, contract_id: int) -> int:
        return (
            await self.session.scalar(
                select(func.count()).where(self.model.contract_id == contract_id)
            )
            or 0
        )

    async def overlaps(
        self, contract_id: int, period_from: date, period_to: date, exclude_id: int | None
    ) -> bool:
        stmt = select(func.count()).where(
            self.model.contract_id == contract_id,
            self.model.status.in_(PERIOD_HOLDING_STATUSES),
            self.model.period_from <= period_to,
            self.model.period_to >= period_from,
        )
        if exclude_id is not None:
            stmt = stmt.where(self.model.id != exclude_id)
        return bool(await self.session.scalar(stmt))

    def my_stmt(self, contractor_id: int, filters: MyActFilterDTO) -> Select:
        stmt = (
            select(self.model)
            .join(ContractORM, ContractORM.id == self.model.contract_id)
            .where(ContractORM.contractor_id == contractor_id)
        )
        if filters.status:
            stmt = stmt.where(self.model.status == filters.status)
        if filters.contract_id:
            stmt = stmt.where(self.model.contract_id == filters.contract_id)
        return stmt.order_by(self.model.period_from.desc(), self.model.id.desc())

    def fund_stmt(self, filters: FundActFilterDTO, user_id: int) -> Select:
        stmt = select(self.model).join(ContractORM, ContractORM.id == self.model.contract_id)
        statuses = TAB_STATUSES.get(filters.tab, FUND_VISIBLE)
        stmt = stmt.where(self.model.status.in_(statuses))
        if filters.status:
            stmt = stmt.where(self.model.status == filters.status)
        if filters.contract_id:
            stmt = stmt.where(self.model.contract_id == filters.contract_id)
        if filters.contractor_id:
            stmt = stmt.where(ContractORM.contractor_id == filters.contractor_id)
        if filters.mine:
            stmt = stmt.where(ContractORM.approver_id == user_id)
        if filters.search:
            pattern = f"%{filters.search.strip()}%"
            stmt = stmt.where(
                or_(
                    self.model.number.ilike(pattern),
                    ContractORM.number.ilike(pattern),
                    ContractORM.contractor_name.ilike(pattern),
                )
            )
        return stmt.order_by(self.model.submitted_at.desc().nulls_last(), self.model.id.desc())

    async def paginate_list(self, stmt: Select, page, per_page, mapper) -> dict:
        return await self.paginate(stmt, page, per_page, mapper=mapper)

    async def count_by_status(self) -> dict[ActStatus, int]:
        rows = await self.session.execute(
            select(self.model.status, func.count()).group_by(self.model.status)
        )
        return dict(rows.all())

    async def count_to_sign_by(self, approver_id: int) -> int:
        return (
            await self.session.scalar(
                select(func.count())
                .select_from(self.model)
                .join(ContractORM, ContractORM.id == self.model.contract_id)
                .where(
                    self.model.status == ActStatus.ACCEPTED, ContractORM.approver_id == approver_id
                )
            )
            or 0
        )

    async def count_mine_by_status(self, contractor_id: int) -> dict[ActStatus, int]:
        rows = await self.session.execute(
            select(self.model.status, func.count())
            .join(ContractORM, ContractORM.id == self.model.contract_id)
            .where(ContractORM.contractor_id == contractor_id)
            .group_by(self.model.status)
        )
        return dict(rows.all())
