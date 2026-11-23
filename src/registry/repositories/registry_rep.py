from datetime import date
from decimal import Decimal

from sqlalchemy import Select, and_, case, delete, extract, func, or_, select

from src.registry.dictionaries import district_key, district_name
from src.registry.enums import GroupBy, ProjectStatus, Source
from src.registry.models.registry_model import RegistryProgramORM, RegistryProjectORM
from src.registry.schemas.registry_schema import ProjectFilterDTO
from src.utils.base_rep.base_rep import BaseRepository

P = RegistryProjectORM
# Дата отчёта: решение Совета, а если его нет — заявка.
REPORT_DATE = func.coalesce(P.council_date, P.application_date)
ZERO = Decimal(0)
# Ключ «не указано» в счётчиках итогов (пол, тип субъекта, статус).
NOT_SPECIFIED = "NOT_SPECIFIED"


def _totals_columns():
    allocated = and_(P.allocated_amount.is_not(None), P.allocated_amount > 0)
    credit = and_(P.credit_amount.is_not(None), P.credit_amount > 0)
    returned = P.status == ProjectStatus.RETURNED
    return [
        func.count(P.id).label("projects"),
        func.coalesce(func.sum(P.requested_amount), 0).label("requested_amount"),
        func.count(P.id).filter(allocated).label("allocated_count"),
        func.coalesce(func.sum(P.allocated_amount), 0).label("allocated_amount"),
        func.count(P.id).filter(credit).label("credit_count"),
        func.coalesce(func.sum(P.credit_amount), 0).label("credit_amount"),
        func.count(P.id).filter(returned).label("returned_count"),
        func.coalesce(func.sum(case((returned, P.requested_amount), else_=0)), 0).label(
            "returned_amount"
        ),
        func.coalesce(func.sum(P.jobs), 0).label("jobs"),
    ]


GROUP_COLUMNS = {
    GroupBy.PROGRAM: P.program_id,
    GroupBy.KIND: RegistryProgramORM.kind,
    GroupBy.REGION: P.region,
    GroupBy.DISTRICT: P.district_key,
    GroupBy.BANK: P.bank,
    GroupBy.SECTOR: P.sector,
    GroupBy.DIRECTION: P.direction,
    GroupBy.GENDER: P.gender,
    GroupBy.SUBJECT_TYPE: P.subject_type,
    GroupBy.STATUS: P.status,
    GroupBy.YEAR: extract("year", REPORT_DATE),
    GroupBy.MONTH: func.to_char(REPORT_DATE, "YYYY-MM"),
}


class RegistryRepository(BaseRepository):
    model = RegistryProjectORM

    # ---------- программы ----------

    async def get_program(self, program_id: int) -> RegistryProgramORM | None:
        stmt = (
            select(RegistryProgramORM)
            .where(RegistryProgramORM.id == program_id)
            .execution_options(populate_existing=True)
        )
        return await self.session.scalar(stmt)

    async def get_program_by_code(self, code: str) -> RegistryProgramORM | None:
        return await self.session.scalar(
            select(RegistryProgramORM).where(RegistryProgramORM.code == code)
        )

    async def get_programs(self, only_active: bool = False) -> list[RegistryProgramORM]:
        stmt = select(RegistryProgramORM).order_by(
            RegistryProgramORM.sort_order, RegistryProgramORM.id
        )
        if only_active:
            stmt = stmt.where(RegistryProgramORM.is_active.is_(True))
        return list((await self.session.scalars(stmt)).all())

    async def projects_count_by_program(self) -> dict[int, int]:
        rows = await self.session.execute(select(P.program_id, func.count()).group_by(P.program_id))
        return dict(rows.all())

    # ---------- проекты ----------

    async def get_project(self, project_id: int) -> RegistryProjectORM | None:
        stmt = select(P).where(P.id == project_id).execution_options(populate_existing=True)
        return await self.session.scalar(stmt)

    @staticmethod
    def apply_filters(stmt: Select, f: ProjectFilterDTO) -> Select:
        if f.program_id is not None:
            stmt = stmt.where(P.program_id == f.program_id)
        if f.kind is not None:
            stmt = stmt.where(
                P.program_id.in_(
                    select(RegistryProgramORM.id).where(RegistryProgramORM.kind == f.kind)
                )
            )
        if f.region:
            stmt = stmt.where(P.region == f.region)
        if f.district:
            key = district_key(district_name(f.district)) or f.district
            stmt = stmt.where(or_(P.district_key == key, P.district_key == f.district))
        if f.bank:
            stmt = stmt.where(P.bank == f.bank)
        for column, value in (
            (P.sector, f.sector),
            (P.gender, f.gender),
            (P.subject_type, f.subject_type),
            (P.status, f.status),
            (P.source, f.source),
        ):
            if value is not None:
                stmt = stmt.where(column == value)
        if f.direction:
            stmt = stmt.where(func.lower(P.direction) == f.direction.strip().lower())
        if f.year is not None:
            stmt = stmt.where(extract("year", REPORT_DATE) == f.year)
        if f.date_from is not None:
            stmt = stmt.where(REPORT_DATE >= f.date_from)
        if f.date_to is not None:
            stmt = stmt.where(REPORT_DATE <= f.date_to)
        if f.search:
            like = f"%{f.search.strip()}%"
            stmt = stmt.where(
                or_(
                    P.applicant_name.ilike(like),
                    P.organization.ilike(like),
                    P.tin.ilike(like),
                    P.phone.ilike(like),
                )
            )
        return stmt

    async def get_projects_page(
        self, filters: ProjectFilterDTO, page: int | None, per_page: int | None, mapper
    ) -> dict:
        stmt = self.apply_filters(select(P), filters).order_by(
            REPORT_DATE.desc().nulls_last(), P.id.desc()
        )
        return await self.paginate(stmt, page, per_page, mapper=mapper)

    async def delete_imported(self, program_id: int) -> int:
        result = await self.session.execute(
            delete(P).where(P.program_id == program_id, P.source == Source.IMPORT)
        )
        return result.rowcount or 0

    # ---------- аналитика ----------

    async def totals(self, filters: ProjectFilterDTO) -> dict:
        stmt = self.apply_filters(select(*_totals_columns()), filters)
        return dict((await self.session.execute(stmt)).one()._mapping)

    async def counts_by(self, column, filters: ProjectFilterDTO) -> dict[str | None, int]:
        stmt = self.apply_filters(select(column, func.count(P.id)).group_by(column), filters)
        return {
            NOT_SPECIFIED if key is None else str(getattr(key, "value", key)): count
            for key, count in (await self.session.execute(stmt)).all()
        }

    async def date_range(self, filters: ProjectFilterDTO) -> tuple[date | None, date | None]:
        stmt = self.apply_filters(select(func.min(REPORT_DATE), func.max(REPORT_DATE)), filters)
        return tuple((await self.session.execute(stmt)).one())

    async def breakdown(self, group_by: GroupBy, filters: ProjectFilterDTO) -> list[dict]:
        column = GROUP_COLUMNS[group_by].label("key")
        stmt = select(column, *_totals_columns())
        if group_by == GroupBy.KIND:
            stmt = stmt.join(RegistryProgramORM, RegistryProgramORM.id == P.program_id)
        if group_by == GroupBy.DISTRICT:
            stmt = stmt.add_columns(
                func.min(P.district).label("label"), func.min(P.region).label("region")
            )
        stmt = self.apply_filters(stmt, filters).group_by(column)
        stmt = stmt.order_by(
            func.coalesce(func.sum(P.allocated_amount), 0).desc(), func.count(P.id).desc()
        )
        return [dict(row._mapping) for row in (await self.session.execute(stmt)).all()]
