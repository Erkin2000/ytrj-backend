from datetime import date

from sqlalchemy import func, select

from src.utils.base_rep.base_rep import BaseRepository
from src.website.enums import PersonKind
from src.website.mappers import WebsiteDataMapper, event_public
from src.website.models.website_model import AboutSectionORM, EventORM, PersonORM
from src.website.schemas.website_schema import EventFilterDTO


class WebsiteRepository(BaseRepository):
    model = EventORM
    mapper = WebsiteDataMapper

    async def _get(self, orm, object_id: int):
        stmt = select(orm).where(orm.id == object_id).execution_options(populate_existing=True)
        return await self.session.scalar(stmt)

    # ---------- события ----------

    async def get_event(self, event_id: int) -> EventORM | None:
        return await self._get(EventORM, event_id)

    async def get_events_page(
        self,
        filters: EventFilterDTO,
        page: int | None,
        per_page: int | None,
        only_active: bool,
    ) -> dict:
        stmt = select(EventORM)
        if only_active:
            stmt = stmt.where(EventORM.is_active.is_(True))
        if filters.date:
            stmt = stmt.where(EventORM.event_date == filters.date)
        if filters.date_from:
            stmt = stmt.where(EventORM.event_date >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(EventORM.event_date <= filters.date_to)
        stmt = stmt.order_by(EventORM.event_date.desc(), EventORM.id.desc())
        mapper = event_public if only_active else None
        return await self.paginate(stmt, page, per_page, mapper=mapper)

    async def get_event_days(
        self, date_from: date, date_to: date, only_active: bool
    ) -> list[tuple[date, int]]:
        stmt = (
            select(EventORM.event_date, func.count())
            .where(EventORM.event_date >= date_from, EventORM.event_date <= date_to)
            .group_by(EventORM.event_date)
            .order_by(EventORM.event_date)
        )
        if only_active:
            stmt = stmt.where(EventORM.is_active.is_(True))
        return [(day, count) for day, count in (await self.session.execute(stmt)).all()]

    # ---------- «О нас» ----------

    async def get_about(self, section_id: int) -> AboutSectionORM | None:
        return await self._get(AboutSectionORM, section_id)

    async def get_about_list(self, only_active: bool) -> list[AboutSectionORM]:
        stmt = select(AboutSectionORM).order_by(AboutSectionORM.sort_order, AboutSectionORM.id)
        if only_active:
            stmt = stmt.where(AboutSectionORM.is_active.is_(True))
        return list((await self.session.scalars(stmt)).all())

    # ---------- люди ----------

    async def get_person(self, kind: PersonKind, person_id: int) -> PersonORM | None:
        person = await self._get(PersonORM, person_id)
        return person if person is not None and person.kind == kind else None

    async def get_people(
        self, kind: PersonKind, only_active: bool = False, for_update: bool = False
    ) -> list[PersonORM]:
        stmt = (
            select(PersonORM)
            .where(PersonORM.kind == kind)
            .order_by(PersonORM.queue_number, PersonORM.id)
        )
        if only_active:
            stmt = stmt.where(PersonORM.is_active.is_(True))
        if for_update:
            stmt = stmt.with_for_update()
        return list((await self.session.scalars(stmt)).all())
