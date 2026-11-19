from datetime import datetime

from src.application.mappers import actor
from src.bulletin.enums import (
    SIGNING_STATUSES,
    TASHKENT_TZ,
    BulletinDecision,
    BulletinStatus,
    MemberBulletinStatus,
)
from src.bulletin.models.bulletin_model import BulletinORM, BulletinSignatureORM
from src.bulletin.schemas.bulletin_schema import (
    BulletinApplicationDTO,
    BulletinDetailDTO,
    BulletinFileDTO,
    BulletinListItemDTO,
    BulletinSignatureDTO,
    BulletinVerifyDTO,
    CertificateDTO,
    CouncilBulletinDetailDTO,
    CouncilBulletinItemDTO,
    MySignatureDTO,
    SignaturesSummaryDTO,
    VerifySignerDTO,
)
from src.config import settings

FUND_PREFIX = f"{settings.API_PREFIX}/fund/bulletins"
COUNCIL_PREFIX = f"{settings.API_PREFIX}/council/bulletins"


def verify_url(bulletin: BulletinORM) -> str:
    return f"{settings.BULLETIN_VERIFY_BASE_URL.rstrip('/')}/{bulletin.public_id}"


def is_overdue(bulletin: BulletinORM, now: datetime) -> bool:
    return bulletin.status in SIGNING_STATUSES and now > bulletin.deadline_at


def member_status(
    bulletin: BulletinORM, signature: BulletinSignatureORM, now: datetime
) -> MemberBulletinStatus:
    if signature.signed_at is not None:
        return MemberBulletinStatus.SIGNED
    if bulletin.status == BulletinStatus.CANCELLED:
        return MemberBulletinStatus.CANCELLED
    if now > bulletin.deadline_at:
        return MemberBulletinStatus.OVERDUE
    if signature.viewed_at is not None:
        return MemberBulletinStatus.VIEWED
    return MemberBulletinStatus.NEW


def sign_blockers(
    bulletin: BulletinORM, signature: BulletinSignatureORM, now: datetime
) -> list[str]:
    """Что мешает подписать (тот же порядок проверок, что в CouncilBulletinService.sign)."""
    if signature.signed_at is not None:
        return ["already_signed"]
    if bulletin.status not in SIGNING_STATUSES:
        return ["not_open_for_signing"]
    if now > bulletin.deadline_at:
        return ["deadline_passed"]
    blockers = []
    if signature.viewed_at is None:
        blockers.append("bulletin_not_viewed")
    if bulletin.file_path and signature.file_viewed_at is None:
        blockers.append("bulletin_file_not_viewed")
    return blockers


def file_dto(bulletin: BulletinORM, url: str | None) -> BulletinFileDTO | None:
    if not bulletin.file_path:
        return None
    return BulletinFileDTO(
        name=bulletin.file_name or "document",
        content_type=bulletin.file_content_type or "application/octet-stream",
        size=bulletin.file_size or 0,
        sha256=bulletin.file_sha256 or "",
        url=url,
    )


def application_dto(bulletin: BulletinORM, url_prefix: str) -> BulletinApplicationDTO | None:
    application = bulletin.application
    if application is None:
        return None
    return BulletinApplicationDTO(
        id=application.id,
        number=application.number,
        status=application.status,
        applicant_full_name=application.applicant_full_name,
        url=f"{settings.API_PREFIX}{url_prefix}/{application.id}",
    )


def certificate_dto(signature: BulletinSignatureORM) -> CertificateDTO | None:
    if signature.signed_at is None:
        return None
    return CertificateDTO(
        pinfl=signature.cert_pinfl,
        full_name=signature.cert_full_name,
        serial_number=signature.cert_serial_number,
        valid_from=signature.cert_valid_from,
        valid_to=signature.cert_valid_to,
    )


def summary(bulletin: BulletinORM) -> SignaturesSummaryDTO:
    signed = [s for s in bulletin.signatures if s.signed_at is not None]
    return SignaturesSummaryDTO(
        total=len(bulletin.signatures),
        signed=len(signed),
        pending=len(bulletin.signatures) - len(signed),
        agree=sum(1 for s in signed if s.decision == BulletinDecision.AGREE),
        against=sum(1 for s in signed if s.decision == BulletinDecision.AGAINST),
    )


class BulletinDataMapper:
    # ---------- Фонд ----------

    @staticmethod
    def _fund_fields(bulletin: BulletinORM, now: datetime) -> dict:
        return {
            "id": bulletin.id,
            "number": bulletin.number,
            "name": bulletin.name,
            "status": bulletin.status,
            "send_at": bulletin.send_at,
            "published_at": bulletin.published_at,
            "deadline_at": bulletin.deadline_at,
            "is_overdue": is_overdue(bulletin, now),
            "has_file": bool(bulletin.file_path),
            "application": application_dto(bulletin, "/fund/applications"),
            "signatures": summary(bulletin),
            "created_at": bulletin.created_at,
        }

    @classmethod
    def map_to_list_item(cls, bulletin: BulletinORM, now: datetime) -> BulletinListItemDTO:
        return BulletinListItemDTO(**cls._fund_fields(bulletin, now))

    @classmethod
    def map_to_detail(cls, bulletin: BulletinORM, now: datetime) -> BulletinDetailDTO:
        return BulletinDetailDTO(
            **cls._fund_fields(bulletin, now),
            public_id=bulletin.public_id,
            description=bulletin.description,
            file=file_dto(bulletin, f"{FUND_PREFIX}/{bulletin.id}/file"),
            signature_list=[
                BulletinSignatureDTO(
                    id=s.id,
                    member=actor(s.council_member),
                    member_full_name=s.member_full_name,
                    status=member_status(bulletin, s, now),
                    viewed_at=s.viewed_at,
                    file_viewed_at=s.file_viewed_at,
                    decision=s.decision,
                    comment=s.comment,
                    signed_at=s.signed_at,
                    certificate=certificate_dto(s),
                    document_hash=s.document_hash,
                )
                for s in bulletin.signatures
            ],
            created_by=actor(bulletin.created_by),
            completed_at=bulletin.completed_at,
            cancelled_at=bulletin.cancelled_at,
            cancelled_by=actor(bulletin.cancelled_by),
            cancel_reason=bulletin.cancel_reason,
            verify_url=verify_url(bulletin),
            qr_url=f"{FUND_PREFIX}/{bulletin.id}/qr",
        )

    # ---------- член Совета ----------

    @staticmethod
    def _council_fields(
        bulletin: BulletinORM, signature: BulletinSignatureORM, now: datetime
    ) -> dict:
        return {
            "id": bulletin.id,
            "number": bulletin.number,
            "name": bulletin.name,
            "status": bulletin.status,
            "published_at": bulletin.published_at,
            "deadline_at": bulletin.deadline_at,
            "has_file": bool(bulletin.file_path),
            "application": application_dto(bulletin, "/applications"),
            "my_status": member_status(bulletin, signature, now),
            "my_decision": signature.decision,
            "signed_at": signature.signed_at,
        }

    @classmethod
    def map_to_council_item(
        cls, bulletin: BulletinORM, signature: BulletinSignatureORM, now: datetime
    ) -> CouncilBulletinItemDTO:
        return CouncilBulletinItemDTO(**cls._council_fields(bulletin, signature, now))

    @classmethod
    def map_to_council_detail(
        cls, bulletin: BulletinORM, signature: BulletinSignatureORM, now: datetime
    ) -> CouncilBulletinDetailDTO:
        blockers = sign_blockers(bulletin, signature, now)
        return CouncilBulletinDetailDTO(
            **cls._council_fields(bulletin, signature, now),
            description=bulletin.description,
            file=file_dto(bulletin, f"{COUNCIL_PREFIX}/{bulletin.id}/file"),
            created_at=bulletin.created_at,
            my=MySignatureDTO(
                status=member_status(bulletin, signature, now),
                viewed_at=signature.viewed_at,
                file_viewed_at=signature.file_viewed_at,
                decision=signature.decision,
                comment=signature.comment,
                signed_at=signature.signed_at,
                certificate=certificate_dto(signature),
                can_sign=not blockers,
                sign_blockers=blockers,
            ),
            verify_url=verify_url(bulletin),
        )

    # ---------- проверка по QR ----------

    @staticmethod
    def map_to_verify(bulletin: BulletinORM) -> BulletinVerifyDTO:
        signers = [
            VerifySignerDTO(
                full_name=s.member_full_name
                or (s.council_member.full_name if s.council_member else None),
                signed=s.signed_at is not None,
                decision=s.decision if s.signed_at is not None else None,
                signed_at=s.signed_at,
            )
            for s in bulletin.signatures
        ]
        signed = [s for s in signers if s.signed]
        return BulletinVerifyDTO(
            number=bulletin.number,
            name=bulletin.name,
            description=bulletin.description,
            bulletin_date=bulletin.created_at.astimezone(TASHKENT_TZ).date(),
            status=bulletin.status,
            validity="CANCELLED" if bulletin.status == BulletinStatus.CANCELLED else "VALID",
            file=file_dto(bulletin, None),
            signers=signers,
            signed_count=len(signed),
            agree_count=sum(1 for s in signed if s.decision == BulletinDecision.AGREE),
            against_count=sum(1 for s in signed if s.decision == BulletinDecision.AGAINST),
            not_signed_count=len(signers) - len(signed),
            total_count=len(signers),
        )
