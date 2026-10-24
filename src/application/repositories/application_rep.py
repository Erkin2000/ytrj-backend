from datetime import datetime, time, timedelta

from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.orm import selectinload

from src.application.enums import ApplicationStatus
from src.application.mappers import ApplicationDataMapper
from src.application.models.application_model import ApplicationORM
from src.application.models.council_assignment_model import CouncilAssignmentORM
from src.application.schemas.application_schema import ApplicationDetailDTO, ApplicationFilterDTO
from src.utils.base_rep.base_rep import BaseRepository


class ApplicationRepository(BaseRepository):
    model = ApplicationORM
    mapper = ApplicationDataMapper

    # ---------- номера ----------

    async def next_number(self) -> str:
        seq = await self.session.scalar(text("SELECT nextval('application_number_seq')"))
        return f"JG-{datetime.now().year}-{int(seq):06d}"

    async def next_demand_document_number(self) -> str:
        seq = await self.session.scalar(text("SELECT nextval('demand_document_number_seq')"))
        return f"TD-{datetime.now().year}-{int(seq):06d}"

    # ---------- выборки ----------

    def _detail_stmt(self) -> Select:
        return select(self.model).options(
            selectinload(self.model.photos),
            selectinload(self.model.documents),
            selectinload(self.model.founders),
            selectinload(self.model.council_assignments),
            selectinload(self.model.demand_document),
            selectinload(self.model.resource_allocation),
            selectinload(self.model.bank_accepted_by),
            selectinload(self.model.bank_decided_by),
            selectinload(self.model.sent_to_council_by),
        )

    async def get_orm(self, application_id: int) -> ApplicationORM | None:
        return await self.session.scalar(self._detail_stmt().where(self.model.id == application_id))

    async def get_detail(self, application_id: int) -> ApplicationDetailDTO | None:
        model = await self.get_orm(application_id)
        return self.mapper.map_to_detail(model) if model else None

    def _apply_filters(self, stmt: Select, filters: ApplicationFilterDTO) -> Select:
        if filters.status is not None:
            stmt = stmt.where(self.model.status == filters.status)
        if filters.statuses:
            stmt = stmt.where(self.model.status.in_(filters.statuses))
        if filters.bank_id is not None:
            stmt = stmt.where(self.model.bank_id == filters.bank_id)
        if filters.subject_type is not None:
            stmt = stmt.where(self.model.subject_type == filters.subject_type)
        if filters.date_from is not None:
            stmt = stmt.where(
                self.model.created_at >= datetime.combine(filters.date_from, time.min)
            )
        if filters.date_to is not None:
            stmt = stmt.where(
                self.model.created_at
                < datetime.combine(filters.date_to, time.min) + timedelta(days=1)
            )
        if filters.scoring_retry_required is not None:
            stmt = stmt.where(self.model.scoring_retry_required.is_(filters.scoring_retry_required))
        if filters.search:
            pattern = f"%{filters.search}%"
            stmt = stmt.where(
                or_(
                    self.model.number.ilike(pattern),
                    self.model.applicant_full_name.ilike(pattern),
                    self.model.legal_name.ilike(pattern),
                    self.model.applicant_pinfl.ilike(pattern),
                )
            )
        return stmt

    async def get_all(
        self,
        filters: ApplicationFilterDTO,
        page: int | None = None,
        per_page: int | None = None,
        applicant_id: int | None = None,
        bank_id: int | None = None,
        council_member_id: int | None = None,
    ) -> dict:
        """Список заявок с учётом scope:
        applicant_id — только свои; bank_id — только заявки банка;
        council_member_id — только направленные этому члену Совета."""
        stmt = select(self.model).order_by(self.model.updated_at.desc(), self.model.id.desc())

        if applicant_id is not None:
            stmt = stmt.where(self.model.applicant_id == applicant_id)
        if bank_id is not None:
            stmt = stmt.where(self.model.bank_id == bank_id)
        if council_member_id is not None:
            stmt = stmt.join(
                CouncilAssignmentORM,
                CouncilAssignmentORM.application_id == self.model.id,
            ).where(CouncilAssignmentORM.council_member_id == council_member_id)

        stmt = self._apply_filters(stmt, filters)
        return await self.paginate(stmt, page, per_page)

    async def count_by_status(
        self,
        applicant_id: int | None = None,
        bank_id: int | None = None,
        council_member_id: int | None = None,
    ) -> dict[str, int]:
        stmt = select(self.model.status, func.count()).group_by(self.model.status)

        if applicant_id is not None:
            stmt = stmt.where(self.model.applicant_id == applicant_id)
        if bank_id is not None:
            stmt = stmt.where(self.model.bank_id == bank_id)
        if council_member_id is not None:
            stmt = stmt.join(
                CouncilAssignmentORM,
                CouncilAssignmentORM.application_id == self.model.id,
            ).where(CouncilAssignmentORM.council_member_id == council_member_id)

        result = await self.session.execute(stmt)
        counters = {status.value: 0 for status in ApplicationStatus}
        for status, count in result.all():
            counters[status.value] = count
        return counters
