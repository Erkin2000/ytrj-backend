from datetime import datetime
from math import ceil

from sqlalchemy import Select, and_, func, or_, select

from src.bulletin.enums import SENT_STATUSES, SIGNING_STATUSES, BulletinStatus, CouncilBulletinTab
from src.bulletin.models.bulletin_model import BulletinORM, BulletinSignatureORM
from src.bulletin.schemas.bulletin_schema import BulletinFilterDTO
from src.utils.base_rep.base_rep import BaseRepository


class BulletinRepository(BaseRepository):
    model = BulletinORM

    async def get_orm(self, bulletin_id: int, *, for_update: bool = False) -> BulletinORM | None:
        stmt = (
            select(self.model)
            .where(self.model.id == bulletin_id)
            .execution_options(populate_existing=True)
        )
        if for_update:
            stmt = stmt.with_for_update(of=self.model)
        return await self.session.scalar(stmt)

    async def get_orm_by_public_id(self, public_id: str) -> BulletinORM | None:
        return await self.session.scalar(
            select(self.model).where(self.model.public_id == public_id)
        )

    async def add_orm(self, bulletin: BulletinORM) -> BulletinORM:
        self.session.add(bulletin)
        await self.session.flush()
        return bulletin

    async def delete_orm(self, bulletin: BulletinORM) -> None:
        await self.session.delete(bulletin)
        await self.session.flush()

    def fund_stmt(self, filters: BulletinFilterDTO) -> Select:
        stmt = select(self.model)
        if filters.status:
            stmt = stmt.where(self.model.status == filters.status)
        if filters.application_id:
            stmt = stmt.where(self.model.application_id == filters.application_id)
        if filters.search:
            pattern = f"%{filters.search.strip()}%"
            stmt = stmt.where(or_(self.model.number.ilike(pattern), self.model.name.ilike(pattern)))
        return stmt.order_by(self.model.id.desc())

    async def get_all_fund(
        self, filters: BulletinFilterDTO, page: int | None, per_page: int | None, mapper
    ) -> dict:
        return await self.paginate(self.fund_stmt(filters), page, per_page, mapper=mapper)

    async def count_by_status(self) -> dict[BulletinStatus, int]:
        rows = await self.session.execute(
            select(self.model.status, func.count()).group_by(self.model.status)
        )
        return {status: count for status, count in rows.all()}

    async def count_overdue(self, now: datetime) -> int:
        return (
            await self.session.scalar(
                select(func.count()).where(
                    self.model.status.in_(SIGNING_STATUSES), self.model.deadline_at < now
                )
            )
            or 0
        )

    async def ids_due_for_publication(self, now: datetime, limit: int = 50) -> list[int]:
        """Отложенные бюллетени, чья дата отправки наступила. Строки блокируются
        (SKIP LOCKED), чтобы несколько процессов не отправили один бюллетень дважды."""
        stmt = (
            select(self.model.id)
            .where(self.model.status == BulletinStatus.PENDING, self.model.send_at <= now)
            .order_by(self.model.send_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self.session.scalars(stmt)).all())

    async def ids_due_for_expiry(self, now: datetime, limit: int = 50) -> list[int]:
        """Разосланные бюллетени, у которых прошёл срок подписания (SKIP LOCKED)."""
        stmt = (
            select(self.model.id)
            .where(self.model.status.in_(SIGNING_STATUSES), self.model.deadline_at < now)
            .order_by(self.model.deadline_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self.session.scalars(stmt)).all())

    async def open_unsigned_signatures(self) -> list[BulletinSignatureORM]:
        """Неподписанные строки бюллетеней, которые ещё ждут подписей."""
        stmt = (
            select(BulletinSignatureORM)
            .join(BulletinORM, BulletinORM.id == BulletinSignatureORM.bulletin_id)
            .where(
                BulletinORM.status.in_(SIGNING_STATUSES),
                BulletinSignatureORM.signed_at.is_(None),
            )
        )
        return list((await self.session.scalars(stmt)).all())

    async def lock_skip_locked(self, bulletin_id: int) -> bool:
        """Блокирует бюллетень; False — если его сейчас держит другая транзакция."""
        stmt = (
            select(self.model.id)
            .where(self.model.id == bulletin_id)
            .with_for_update(skip_locked=True)
        )
        return await self.session.scalar(stmt) is not None

    async def get_in_range(
        self, start: datetime, end: datetime, statuses: set[BulletinStatus] | None = None
    ) -> list[BulletinORM]:
        """Бюллетени, у которых дата отправки или срок подписания попадает в [start, end)."""
        stmt = select(self.model).where(
            or_(
                and_(self.model.send_at >= start, self.model.send_at < end),
                and_(self.model.deadline_at >= start, self.model.deadline_at < end),
            )
        )
        if statuses:
            stmt = stmt.where(self.model.status.in_(statuses))
        return list((await self.session.scalars(stmt.order_by(self.model.id))).all())

    # ---------- член Совета ----------

    def member_stmt(self, member_id: int) -> Select:
        """Строки получателя вместе с бюллетенем; отложенные бюллетени не видны."""
        return (
            select(BulletinSignatureORM, BulletinORM)
            .join(BulletinORM, BulletinORM.id == BulletinSignatureORM.bulletin_id)
            .where(
                BulletinSignatureORM.council_member_id == member_id,
                BulletinORM.status.in_(SENT_STATUSES),
            )
        )

    @staticmethod
    def tab_filter(stmt: Select, tab: CouncilBulletinTab, now: datetime) -> Select:
        open_for_signing = and_(
            BulletinORM.status.in_(SIGNING_STATUSES),
            BulletinORM.deadline_at >= now,
            BulletinSignatureORM.signed_at.is_(None),
        )
        if tab == CouncilBulletinTab.NEW:
            return stmt.where(open_for_signing, BulletinSignatureORM.viewed_at.is_(None))
        if tab == CouncilBulletinTab.TO_SIGN:
            return stmt.where(open_for_signing)
        if tab == CouncilBulletinTab.SIGNED:
            return stmt.where(BulletinSignatureORM.signed_at.is_not(None))
        if tab == CouncilBulletinTab.OVERDUE:
            return stmt.where(
                or_(
                    and_(BulletinORM.status.in_(SIGNING_STATUSES), BulletinORM.deadline_at < now),
                    BulletinORM.status == BulletinStatus.EXPIRED,
                ),
                BulletinSignatureORM.signed_at.is_(None),
            )
        return stmt

    async def get_member_page(
        self,
        member_id: int,
        tab: CouncilBulletinTab,
        now: datetime,
        page: int | None,
        per_page: int | None,
        mapper,
    ) -> dict:
        stmt = self.tab_filter(self.member_stmt(member_id), tab, now)
        # Сначала ближайший срок подписания среди неподписанных, затем свежие.
        stmt = stmt.order_by(
            BulletinSignatureORM.signed_at.is_not(None),
            BulletinORM.deadline_at,
            BulletinORM.id.desc(),
        )
        return await self._paginate_rows(stmt, page, per_page, mapper)

    async def _paginate_rows(self, stmt: Select, page, per_page, mapper) -> dict:
        total = (
            await self.session.scalar(
                select(func.count()).select_from(stmt.order_by(None).subquery())
            )
            or 0
        )
        if page and per_page:
            stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        rows = (await self.session.execute(stmt)).all()
        return {
            "items": [mapper(bulletin, signature) for signature, bulletin in rows],
            "pagination": {
                "page": page or 1,
                "per_page": per_page or total,
                "total": total,
                "pages": ceil(total / per_page) if per_page else 1,
            },
        }

    async def count_member_tabs(self, member_id: int, now: datetime) -> dict[str, int]:
        counts = {}
        for tab in (
            CouncilBulletinTab.NEW,
            CouncilBulletinTab.TO_SIGN,
            CouncilBulletinTab.SIGNED,
            CouncilBulletinTab.OVERDUE,
        ):
            stmt = self.tab_filter(self.member_stmt(member_id), tab, now)
            counts[tab.value] = (
                await self.session.scalar(
                    select(func.count()).select_from(stmt.order_by(None).subquery())
                )
                or 0
            )
        return counts

    async def get_member_signature(
        self, bulletin_id: int, member_id: int
    ) -> tuple[BulletinSignatureORM, BulletinORM] | None:
        row = (
            await self.session.execute(
                self.member_stmt(member_id).where(BulletinORM.id == bulletin_id)
            )
        ).first()
        return (row[0], row[1]) if row else None

    async def get_member_in_range(
        self, member_id: int, start: datetime, end: datetime
    ) -> list[tuple[BulletinSignatureORM, BulletinORM]]:
        stmt = self.member_stmt(member_id).where(
            or_(
                and_(BulletinORM.published_at >= start, BulletinORM.published_at < end),
                and_(BulletinORM.deadline_at >= start, BulletinORM.deadline_at < end),
            )
        )
        rows = (await self.session.execute(stmt.order_by(BulletinORM.id))).all()
        return [(row[0], row[1]) for row in rows]
