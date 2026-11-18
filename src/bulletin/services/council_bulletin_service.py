"""Рабочее окно члена Совета: свои бюллетени (новые, на подпись, подписанные,
просроченные), календарь, просмотр бюллетеня и файла, подпись ЭЦП.

Член Совета видит только собственный статус: чужие решения и подписи ему не
показываются. Подписать можно после просмотра бюллетеня и прикреплённого файла,
до срока подписания. Подпись — отдельный проход через мост E-IMZO: ПИНФЛ
сертификата должен совпасть с ПИНФЛ члена Совета.
"""

import hashlib
import json
from datetime import date
from pathlib import Path

from src.account.schemas.user_schema import CurrentUserDTO
from src.application.enums import CouncilDecision
from src.application.services.council_service import CouncilService
from src.auth.services.eimzo_service import EimzoService
from src.bulletin.enums import (
    SIGNING_STATUSES,
    BulletinDecision,
    BulletinStatus,
    CalendarEventType,
    CouncilBulletinTab,
)
from src.bulletin.mappers import BulletinDataMapper, member_status
from src.bulletin.models.bulletin_model import BulletinORM, BulletinSignatureORM
from src.bulletin.schemas.bulletin_schema import (
    BulletinSignDTO,
    CalendarDayDTO,
    CalendarEventDTO,
    CouncilBulletinDetailDTO,
)
from src.bulletin.services.bulletin_service import (
    BulletinService,
    day_bounds,
    group_events,
    range_utc,
    utcnow,
)
from src.common.responses.exceptions import (
    BulletinAlreadySignedException,
    BulletinDeadlinePassedException,
    BulletinFileNotViewedException,
    BulletinNotFoundException,
    BulletinNotOpenForSigningException,
    BulletinNotViewedException,
    EimzoSignerMismatchException,
    UserNotFoundException,
)
from src.utils.base_service import BaseService

DECISION_TO_COUNCIL = {
    BulletinDecision.AGREE: CouncilDecision.APPROVED,
    BulletinDecision.AGAINST: CouncilDecision.REJECTED,
}


def document_hash(bulletin: BulletinORM, signature: BulletinSignatureORM, pinfl: str) -> str:
    """SHA-256 того, что подписано: реквизиты бюллетеня, хэш файла и решение члена Совета."""
    payload = {
        "number": bulletin.number,
        "public_id": bulletin.public_id,
        "name": bulletin.name,
        "description": bulletin.description,
        "created_at": bulletin.created_at.isoformat(),
        "deadline_at": bulletin.deadline_at.isoformat(),
        "file_sha256": bulletin.file_sha256,
        "application": bulletin.application.number if bulletin.application else None,
        "signer_pinfl": pinfl,
        "decision": signature.decision.value if signature.decision else None,
        "comment": signature.comment,
        "signed_at": signature.signed_at.isoformat() if signature.signed_at else None,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class CouncilBulletinService(BaseService):
    eimzo = EimzoService()

    @property
    def bulletins(self) -> BulletinService:
        return BulletinService(self.db)

    async def _get_mine(
        self, bulletin_id: int, user: CurrentUserDTO
    ) -> tuple[BulletinSignatureORM, BulletinORM]:
        found = await self.db.bulletin.get_member_signature(bulletin_id, user.id)
        if found is None:
            # Не получатель или бюллетень ещё не отправлен — не раскрываем, что он есть.
            raise BulletinNotFoundException()
        return found

    async def detail(self, bulletin_id: int, user: CurrentUserDTO) -> CouncilBulletinDetailDTO:
        self.db.session.expire_all()
        signature, bulletin = await self._get_mine(bulletin_id, user)
        return BulletinDataMapper.map_to_council_detail(bulletin, signature, utcnow())

    # ---------- списки ----------

    async def get_list(
        self,
        user: CurrentUserDTO,
        tab: CouncilBulletinTab,
        page: int | None,
        per_page: int | None,
    ) -> dict:
        await self.bulletins.publish_due()
        now = utcnow()
        return await self.db.bulletin.get_member_page(
            user.id,
            tab,
            now,
            page,
            per_page,
            mapper=lambda bulletin, signature: BulletinDataMapper.map_to_council_item(
                bulletin, signature, now
            ),
        )

    async def get_counters(self, user: CurrentUserDTO) -> dict[str, int]:
        await self.bulletins.publish_due()
        return await self.db.bulletin.count_member_tabs(user.id, utcnow())

    async def get_calendar(
        self, user: CurrentUserDTO, date_from: date | None, date_to: date | None
    ) -> list[CalendarDayDTO]:
        """Мой календарь: в какой день бюллетень пришёл и до какого дня его подписать."""
        await self.bulletins.publish_due()
        date_from, date_to = day_bounds(date_from, date_to)
        start, end = range_utc(date_from, date_to)
        now = utcnow()

        events = []
        for signature, bulletin in await self.db.bulletin.get_member_in_range(user.id, start, end):
            my_status = member_status(bulletin, signature, now)
            for event_type, at in (
                (CalendarEventType.SEND, bulletin.published_at),
                (CalendarEventType.DEADLINE, bulletin.deadline_at),
            ):
                if at is None:
                    continue
                events.append(
                    CalendarEventDTO(
                        type=event_type,
                        at=at,
                        bulletin_id=bulletin.id,
                        number=bulletin.number,
                        name=bulletin.name,
                        status=bulletin.status,
                        my_status=my_status,
                    )
                )
        return group_events(events, date_from, date_to)

    # ---------- просмотр ----------

    async def open(self, bulletin_id: int, user: CurrentUserDTO) -> CouncilBulletinDetailDTO:
        """Открыть бюллетень: первый просмотр фиксируется (нужен для подписи)."""
        signature, _ = await self._get_mine(bulletin_id, user)
        if signature.viewed_at is None:
            signature.viewed_at = utcnow()
            await self.db.commit()
        return await self.detail(bulletin_id, user)

    async def open_file(self, bulletin_id: int, user: CurrentUserDTO) -> tuple[Path, str, str]:
        """Скачать / открыть файл бюллетеня: просмотр файла фиксируется."""
        signature, bulletin = await self._get_mine(bulletin_id, user)
        result = self.bulletins.file_path(bulletin)
        if signature.file_viewed_at is None:
            now = utcnow()
            signature.file_viewed_at = now
            signature.viewed_at = signature.viewed_at or now
            await self.db.commit()
        return result

    # ---------- подпись ----------

    async def sign(
        self, bulletin_id: int, user: CurrentUserDTO, data: BulletinSignDTO
    ) -> CouncilBulletinDetailDTO:
        # Блокируем бюллетень: одновременные подписи не должны потерять итоговый статус.
        await self.db.bulletin.get_orm(bulletin_id, for_update=True)
        signature, bulletin = await self._get_mine(bulletin_id, user)
        now = utcnow()

        if signature.signed_at is not None:
            raise BulletinAlreadySignedException()
        if bulletin.status not in SIGNING_STATUSES:
            raise BulletinNotOpenForSigningException()
        if now > bulletin.deadline_at:
            raise BulletinDeadlinePassedException()
        if signature.viewed_at is None:
            raise BulletinNotViewedException()
        if bulletin.file_path and signature.file_viewed_at is None:
            raise BulletinFileNotViewedException()

        member = await self.db.user.get_orm_by_id(user.id)
        if member is None:
            raise UserNotFoundException()
        certificate = await self.eimzo.verify_code(data.code)
        if not member.pinfl or certificate.pinfl != member.pinfl:
            raise EimzoSignerMismatchException()

        signature.decision = data.decision
        signature.comment = data.comment
        signature.signed_at = utcnow()
        signature.cert_pinfl = certificate.pinfl
        signature.cert_full_name = certificate.full_name
        signature.cert_serial_number = certificate.serial_number
        signature.cert_valid_from = certificate.valid_from
        signature.cert_valid_to = certificate.valid_to
        signature.cert_tin = certificate.individual_tin
        signature.eimzo_request_id = certificate.request_id
        signature.document_hash = document_hash(bulletin, signature, certificate.pinfl)

        if all(s.signed_at is not None for s in bulletin.signatures):
            bulletin.status = BulletinStatus.COMPLETED
            bulletin.completed_at = signature.signed_at
        else:
            bulletin.status = BulletinStatus.PARTIALLY_SIGNED
        await self.db.flush()

        # Бюллетень по заявке: подпись — решение члена Совета по ней.
        if bulletin.application_id is not None:
            application = await self.db.application.get_orm(bulletin.application_id)
            if application is not None:
                await CouncilService(self.db).apply_vote(
                    application,
                    user,
                    DECISION_TO_COUNCIL[data.decision],
                    data.comment,
                    bulletin.number,
                )

        await self.db.commit()
        return await self.detail(bulletin_id, user)
