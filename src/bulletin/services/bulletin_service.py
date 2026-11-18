"""Бюллетени Совета: рабочее окно Фонда, отправка членам Совета, календарь,
фоновая отправка отложенных бюллетеней и публичная проверка по QR.

Жизненный цикл: PENDING (ждёт `send_at`) → PUBLISHED (разослан всем активным
членам Совета) → PARTIALLY_SIGNED → COMPLETED; CANCELLED — аннулирован Фондом.

Бюллетень, связанный с заявкой, переводит её FUND_REVIEW → COUNCIL_REVIEW при
создании; при отправке члены Совета назначаются на заявку, а их подписи
(«Согласен» / «Против») решают её — см. CouncilBulletinService.sign.
"""

import logging
import secrets
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from fastapi import UploadFile

from src.account.schemas.user_schema import CurrentUserDTO
from src.application.enums import ApplicationStatus
from src.application.services.base import ApplicationBaseService
from src.application.services.fund_service import FundService
from src.bulletin.enums import (
    SIGNING_STATUSES,
    TASHKENT_TZ,
    BulletinStatus,
    CalendarEventType,
)
from src.bulletin.mappers import BulletinDataMapper, verify_url
from src.bulletin.models.bulletin_model import BulletinORM, BulletinSignatureORM
from src.bulletin.qr import qr_svg
from src.bulletin.schemas.bulletin_schema import (
    BulletinCancelDTO,
    BulletinCreateForm,
    BulletinDetailDTO,
    BulletinFilterDTO,
    BulletinUpdateDTO,
    BulletinVerifyDTO,
    CalendarDayDTO,
    CalendarEventDTO,
)
from src.bulletin.storage import BulletinFileStorage
from src.common.responses.exceptions import (
    ApplicationNotFoundException,
    BulletinApplicationException,
    BulletinFileNotFoundException,
    BulletinNotEditableException,
    BulletinNotFoundException,
    BulletinScheduleException,
    BulletinStatusException,
    NoCouncilMembersException,
)
from src.utils.base_service import BaseService

logger = logging.getLogger(__name__)

# Календарь: не больше ~квартала за один запрос.
CALENDAR_MAX_DAYS = 93


def utcnow() -> datetime:
    return datetime.now(UTC)


def day_bounds(date_from: date | None, date_to: date | None) -> tuple[date, date]:
    """Диапазон календаря (включительно); по умолчанию — текущий месяц по Ташкенту."""
    today = utcnow().astimezone(TASHKENT_TZ).date()
    if date_from is None:
        date_from = today.replace(day=1)
    if date_to is None:
        next_month = (date_from.replace(day=28) + timedelta(days=4)).replace(day=1)
        date_to = next_month - timedelta(days=1)
    if date_to < date_from:
        raise BulletinScheduleException(
            "date_to must not be earlier than date_from", field="date_to"
        )
    if (date_to - date_from).days >= CALENDAR_MAX_DAYS:
        raise BulletinScheduleException(
            f"Calendar range must not exceed {CALENDAR_MAX_DAYS} days", field="date_to"
        )
    return date_from, date_to


def range_utc(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    start = datetime.combine(date_from, time.min, tzinfo=TASHKENT_TZ)
    end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=TASHKENT_TZ)
    return start, end


def group_events(
    events: list[CalendarEventDTO], date_from: date, date_to: date
) -> list[CalendarDayDTO]:
    days: dict[date, list[CalendarEventDTO]] = {}
    for event in events:
        day = event.at.astimezone(TASHKENT_TZ).date()
        if date_from <= day <= date_to:
            days.setdefault(day, []).append(event)
    return [
        CalendarDayDTO(date=day, events=sorted(items, key=lambda e: e.at))
        for day, items in sorted(days.items())
    ]


class BulletinService(BaseService):
    storage = BulletinFileStorage()

    @property
    def fund(self) -> FundService:
        return FundService(self.db)

    # ---------- загрузка ----------

    async def get_orm_or_404(self, bulletin_id: int, *, for_update: bool = False) -> BulletinORM:
        bulletin = await self.db.bulletin.get_orm(bulletin_id, for_update=for_update)
        if bulletin is None:
            raise BulletinNotFoundException()
        return bulletin

    async def reload(self, bulletin_id: int) -> BulletinORM:
        """Перечитать после commit, чтобы связи (подписи, заявка) были актуальны."""
        self.db.session.expire_all()
        return await self.get_orm_or_404(bulletin_id)

    async def detail(self, bulletin_id: int) -> BulletinDetailDTO:
        return BulletinDataMapper.map_to_detail(await self.reload(bulletin_id), utcnow())

    # ---------- рабочее окно Фонда ----------

    async def get_list(
        self,
        user: CurrentUserDTO,
        filters: BulletinFilterDTO,
        page: int | None,
        per_page: int | None,
    ) -> dict:
        ApplicationBaseService.assert_global_scope(user)
        await self.publish_due()
        now = utcnow()
        return await self.db.bulletin.get_all_fund(
            filters,
            page,
            per_page,
            mapper=lambda model: BulletinDataMapper.map_to_list_item(model, now),
        )

    async def get_counters(self, user: CurrentUserDTO) -> dict[str, int]:
        ApplicationBaseService.assert_global_scope(user)
        await self.publish_due()
        by_status = await self.db.bulletin.count_by_status()
        counters = {status.value.lower(): by_status.get(status, 0) for status in BulletinStatus}
        counters["overdue"] = await self.db.bulletin.count_overdue(utcnow())
        return counters

    async def get_detail(self, bulletin_id: int, user: CurrentUserDTO) -> BulletinDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        await self.get_orm_or_404(bulletin_id)
        return await self.detail(bulletin_id)

    async def create(
        self, user: CurrentUserDTO, form: BulletinCreateForm, file: UploadFile | None
    ) -> BulletinDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        now = utcnow()

        publish_now = form.status == BulletinStatus.PUBLISHED
        if publish_now:
            send_at = now
        else:
            if form.send_at is None:
                raise BulletinScheduleException(
                    "send_at is required for a pending bulletin", field="send_at"
                )
            send_at = form.send_at
            if send_at <= now:
                raise BulletinScheduleException(
                    "send_at must be in the future; use status PUBLISHED to send now",
                    field="send_at",
                )
        self._check_deadline(form.deadline_at, send_at, now)

        application = None
        if form.application_id is not None:
            application = await self._application_for_bulletin(form.application_id)
        if publish_now and not await self.fund.eligible_council_members():
            raise NoCouncilMembersException()

        bulletin = BulletinORM(
            public_id=secrets.token_urlsafe(24),
            name=form.name,
            description=form.description,
            application=application,
            status=BulletinStatus.PENDING,
            send_at=send_at,
            deadline_at=form.deadline_at,
            created_by_id=user.id,
            signatures=[],
        )
        await self.db.bulletin.add_orm(bulletin)
        bulletin.number = f"BYU-{now.astimezone(TASHKENT_TZ).year}-{bulletin.id:06d}"

        try:
            if file is not None:
                await self._store_file(bulletin, file)
            if application is not None:
                await self.fund.send_to_council(application, user, bulletin.number)
            if publish_now:
                await self._publish(bulletin, user.id)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            await self.storage.delete_bulletin_dir(bulletin.id)
            raise

        return await self.detail(bulletin.id)

    async def update(
        self, bulletin_id: int, user: CurrentUserDTO, data: BulletinUpdateDTO
    ) -> BulletinDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        bulletin = await self.get_orm_or_404(bulletin_id, for_update=True)
        values = data.model_dump(exclude_unset=True)
        now = utcnow()

        if bulletin.status == BulletinStatus.PENDING:
            for field in ("name", "description"):
                if values.get(field) is not None:
                    setattr(bulletin, field, values[field])
            if values.get("send_at") is not None:
                if values["send_at"] <= now:
                    raise BulletinScheduleException(
                        "send_at must be in the future; publish the bulletin to send it now",
                        field="send_at",
                    )
                bulletin.send_at = values["send_at"]
        elif bulletin.status in SIGNING_STATUSES:
            # После отправки текст и файл зафиксированы: продлевается только срок.
            if set(values) - {"deadline_at"}:
                raise BulletinNotEditableException()
        else:
            raise BulletinNotEditableException()

        if values.get("deadline_at") is not None:
            bulletin.deadline_at = values["deadline_at"]
        self._check_deadline(bulletin.deadline_at, bulletin.send_at, now)

        await self.db.commit()
        return await self.detail(bulletin_id)

    async def set_file(
        self, bulletin_id: int, user: CurrentUserDTO, file: UploadFile
    ) -> BulletinDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        bulletin = await self.get_orm_or_404(bulletin_id, for_update=True)
        self._assert_pending(bulletin)

        old_path = bulletin.file_path
        await self._store_file(bulletin, file)
        try:
            await self.db.commit()
        except Exception:
            await self.storage.delete(bulletin.file_path)
            raise
        if old_path:
            await self.storage.delete(old_path)
        return await self.detail(bulletin_id)

    async def delete_file(self, bulletin_id: int, user: CurrentUserDTO) -> BulletinDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        bulletin = await self.get_orm_or_404(bulletin_id, for_update=True)
        self._assert_pending(bulletin)
        if not bulletin.file_path:
            raise BulletinFileNotFoundException()

        old_path = bulletin.file_path
        for field in ("file_path", "file_name", "file_content_type", "file_size", "file_sha256"):
            setattr(bulletin, field, None)
        await self.db.commit()
        await self.storage.delete(old_path)
        return await self.detail(bulletin_id)

    async def publish(self, bulletin_id: int, user: CurrentUserDTO) -> BulletinDetailDTO:
        """Отправить отложенный бюллетень сейчас, не дожидаясь `send_at`."""
        ApplicationBaseService.assert_global_scope(user)
        bulletin = await self.get_orm_or_404(bulletin_id, for_update=True)
        if bulletin.status != BulletinStatus.PENDING:
            raise BulletinStatusException("Only a pending bulletin can be sent")
        if utcnow() >= bulletin.deadline_at:
            raise BulletinScheduleException(
                "The signing deadline has already passed: extend deadline_at first"
            )
        await self._publish(bulletin, user.id)
        await self.db.commit()
        return await self.detail(bulletin_id)

    async def cancel(
        self, bulletin_id: int, user: CurrentUserDTO, data: BulletinCancelDTO
    ) -> BulletinDetailDTO:
        """Аннулировать бюллетень. Подписи сохраняются, страница QR показывает
        «Аннулирован». Заявка, которую Совет ещё не решил, возвращается Фонду."""
        ApplicationBaseService.assert_global_scope(user)
        bulletin = await self.get_orm_or_404(bulletin_id, for_update=True)
        if bulletin.status == BulletinStatus.CANCELLED:
            raise BulletinStatusException("Bulletin is already cancelled")

        bulletin.status = BulletinStatus.CANCELLED
        bulletin.cancelled_at = utcnow()
        bulletin.cancelled_by_id = user.id
        bulletin.cancel_reason = data.reason

        application = await self._linked_application(bulletin)
        if application is not None:
            await self.fund.return_from_council(
                application, user, f"Бюллетень {bulletin.number} аннулирован: {data.reason}"
            )

        await self.db.commit()
        return await self.detail(bulletin_id)

    async def delete(self, bulletin_id: int, user: CurrentUserDTO) -> None:
        """Удалить можно только неотправленный бюллетень; отправленный — аннулировать."""
        ApplicationBaseService.assert_global_scope(user)
        bulletin = await self.get_orm_or_404(bulletin_id, for_update=True)
        if bulletin.status != BulletinStatus.PENDING:
            raise BulletinStatusException(
                "Only a pending bulletin can be deleted; cancel a sent bulletin instead"
            )

        application = await self._linked_application(bulletin)
        if application is not None:
            await self.fund.return_from_council(
                application, user, f"Бюллетень {bulletin.number} удалён до отправки"
            )
        await self.db.bulletin.delete_orm(bulletin)
        await self.db.commit()
        await self.storage.delete_bulletin_dir(bulletin_id)

    async def purge(self, bulletin_id: int, user: CurrentUserDTO) -> None:
        """Super Admin (админ-панель): удалить бюллетень в любом статусе вместе с
        подписями и файлом. Заявка, которую Совет ещё не решил, возвращается Фонду."""
        if not user.is_superuser:
            raise BulletinStatusException("Only the Super Admin can delete a sent bulletin")
        bulletin = await self.get_orm_or_404(bulletin_id, for_update=True)
        application = await self._linked_application(bulletin)
        if application is not None:
            await self.fund.return_from_council(
                application, user, f"Бюллетень {bulletin.number} удалён Super Admin"
            )
        await self.db.bulletin.delete_orm(bulletin)
        await self.db.commit()
        await self.storage.delete_bulletin_dir(bulletin_id)

    async def get_file_path(self, bulletin_id: int, user: CurrentUserDTO) -> tuple[Path, str, str]:
        ApplicationBaseService.assert_global_scope(user)
        return self.file_path(await self.get_orm_or_404(bulletin_id))

    def file_path(self, bulletin: BulletinORM) -> tuple[Path, str, str]:
        if not bulletin.file_path:
            raise BulletinFileNotFoundException()
        path = self.storage.absolute_path(bulletin.file_path)
        if not path.is_file():
            raise BulletinFileNotFoundException("Bulletin file is missing on the server")
        return path, bulletin.file_content_type, bulletin.file_name

    async def get_qr(self, bulletin_id: int, user: CurrentUserDTO) -> bytes:
        ApplicationBaseService.assert_global_scope(user)
        return qr_svg(verify_url(await self.get_orm_or_404(bulletin_id)))

    async def get_calendar(
        self, user: CurrentUserDTO, date_from: date | None, date_to: date | None
    ) -> list[CalendarDayDTO]:
        """Календарь Фонда: даты отправки (в том числе плановые) и сроки подписания."""
        ApplicationBaseService.assert_global_scope(user)
        await self.publish_due()
        date_from, date_to = day_bounds(date_from, date_to)
        start, end = range_utc(date_from, date_to)

        events = []
        for bulletin in await self.db.bulletin.get_in_range(start, end):
            for event_type, at in (
                (CalendarEventType.SEND, bulletin.send_at),
                (CalendarEventType.DEADLINE, bulletin.deadline_at),
            ):
                events.append(
                    CalendarEventDTO(
                        type=event_type,
                        at=at,
                        bulletin_id=bulletin.id,
                        number=bulletin.number,
                        name=bulletin.name,
                        status=bulletin.status,
                    )
                )
        return group_events(events, date_from, date_to)

    # ---------- отправка ----------

    async def _publish(self, bulletin: BulletinORM, actor_id: int | None) -> None:
        """Рассылка всем активным членам Совета: строка подписи на каждого,
        назначения на связанную заявку. Коммит делает вызывающий."""
        members = await self.fund.eligible_council_members()
        if not members:
            raise NoCouncilMembersException()

        now = utcnow()
        for member in members:
            bulletin.signatures.append(
                BulletinSignatureORM(
                    council_member_id=member.id,
                    member_full_name=member.full_name or member.username,
                )
            )

        application = await self._linked_application(bulletin)
        if application is not None and application.status == ApplicationStatus.COUNCIL_REVIEW:
            await self.fund.assign_council(application, members, actor_id or bulletin.created_by_id)

        bulletin.status = BulletinStatus.PUBLISHED
        bulletin.published_at = now
        bulletin.published_by_id = actor_id
        # Отправлен раньше плановой даты — в календаре фактическая дата отправки.
        if bulletin.send_at > now:
            bulletin.send_at = now
        await self.db.flush()

    async def publish_due(self) -> int:
        """Отправляет отложенные бюллетени, у которых наступила дата отправки.
        Вызывается фоновой задачей и перед выдачей списков (на случай, если задача
        не запущена). Возвращает число отправленных."""
        ids = await self.db.bulletin.ids_due_for_publication(utcnow())
        if not ids:
            return 0
        if not await self.fund.eligible_council_members():
            logger.warning(
                "Bulletins %s are due but there are no council members to send them to", ids
            )
            await self.db.rollback()
            return 0

        for bulletin_id in ids:
            bulletin = await self.get_orm_or_404(bulletin_id)
            await self._publish(bulletin, None)
            logger.info("Bulletin %s sent to council members on schedule", bulletin.number)
        await self.db.commit()
        return len(ids)

    # ---------- проверка по QR (публично) ----------

    async def verify(self, public_id: str) -> BulletinVerifyDTO:
        bulletin = await self.db.bulletin.get_orm_by_public_id(public_id)
        if bulletin is None:
            raise BulletinNotFoundException("Document not found: it cannot be verified")
        return BulletinDataMapper.map_to_verify(bulletin)

    # ---------- вспомогательное ----------

    @staticmethod
    def _assert_pending(bulletin: BulletinORM) -> None:
        if bulletin.status != BulletinStatus.PENDING:
            raise BulletinNotEditableException()

    @staticmethod
    def _check_deadline(deadline_at: datetime, send_at: datetime, now: datetime) -> None:
        if deadline_at <= max(send_at, now):
            raise BulletinScheduleException(
                "deadline_at must be later than the send date and the current time",
                field="deadline_at",
            )

    async def _application_for_bulletin(self, application_id: int):
        application = await self.db.application.get_orm(application_id)
        if application is None:
            raise ApplicationNotFoundException(field="application_id")
        if application.status != ApplicationStatus.FUND_REVIEW:
            raise BulletinApplicationException(
                f"Only an application under Fund review can be attached to a bulletin "
                f"(current status: {application.status})"
            )
        return application

    async def _linked_application(self, bulletin: BulletinORM):
        if bulletin.application_id is None:
            return None
        return await self.db.application.get_orm(bulletin.application_id)

    async def _store_file(self, bulletin: BulletinORM, file: UploadFile) -> None:
        path, size, content_type = await self.storage.save(bulletin.id, file)
        bulletin.file_path = path
        bulletin.file_name = (Path(file.filename or "").name or f"bulletin{Path(path).suffix}")[
            :255
        ]
        bulletin.file_content_type = content_type
        bulletin.file_size = size
        bulletin.file_sha256 = await self.storage.sha256(path)
