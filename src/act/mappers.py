from src.act.models.act_model import ActORM, ContractORM
from src.act.schemas.act_schema import (
    ActActionsDTO,
    ActAttachmentDTO,
    ActDetailDTO,
    ActEventDTO,
    ActItemDTO,
    ActListItemDTO,
    ActSignatureDTO,
    ContractDTO,
    ContractShortDTO,
    PersonDTO,
)
from src.config import settings


def verify_url(act: ActORM) -> str:
    return f"{settings.ACT_VERIFY_BASE_URL.rstrip('/')}/{act.public_id}"


def person(user) -> PersonDTO | None:
    return PersonDTO(id=user.id, full_name=user.full_name) if user is not None else None


def map_contract(contract: ContractORM, acts_count: int = 0) -> ContractDTO:
    return ContractDTO(
        id=contract.id,
        number=contract.number,
        signed_on=contract.signed_on,
        contractor=person(contract.contractor),
        contractor_name=contract.contractor_name,
        position=contract.position,
        subject=contract.subject,
        start_date=contract.start_date,
        end_date=contract.end_date,
        amount=contract.amount,
        approver=person(contract.approver),
        approver_name=contract.approver_name,
        approver_title=contract.approver_title,
        status=contract.status,
        acts_count=acts_count,
        created_at=contract.created_at,
    )


def map_contract_short(contract: ContractORM) -> ContractShortDTO:
    return ContractShortDTO(
        id=contract.id,
        number=contract.number,
        signed_on=contract.signed_on,
        contractor_name=contract.contractor_name,
        position=contract.position,
        approver_name=contract.approver_name,
    )


def _list_fields(act: ActORM) -> dict:
    return {
        "id": act.id,
        "number": act.number,
        "status": act.status,
        "contract": map_contract_short(act.contract),
        "period_from": act.period_from,
        "period_to": act.period_to,
        "act_date": act.act_date,
        "items_count": len(act.items),
        "attachments_count": len(act.attachments),
        "submitted_at": act.submitted_at,
        "accepted_at": act.accepted_at,
        "signed_at": act.signed_at,
        "returned_at": act.returned_at,
        "updated_at": act.updated_at,
    }


def map_act_list_item(act: ActORM) -> ActListItemDTO:
    return ActListItemDTO(**_list_fields(act))


def map_act_detail(act: ActORM, actions: ActActionsDTO) -> ActDetailDTO:
    return ActDetailDTO(
        **_list_fields(act),
        intro=act.intro,
        appendix_title=act.appendix_title,
        return_comment=act.return_comment,
        cancel_reason=act.cancel_reason,
        cancelled_at=act.cancelled_at,
        content_hash=act.content_hash,
        final_pdf_sha256=act.final_pdf_sha256,
        items=[
            ActItemDTO(
                id=i.id,
                position=i.position,
                content=i.content,
                period_text=i.period_text,
                note=i.note,
            )
            for i in act.items
        ],
        attachments=[
            ActAttachmentDTO(
                id=a.id,
                position=a.position,
                caption=a.caption,
                url=a.url,
                file_name=a.file_name,
                content_type=a.content_type,
                size=a.file_size,
                sha256=a.sha256,
            )
            for a in act.attachments
        ],
        signatures=[
            ActSignatureDTO(
                role=s.role,
                signer=PersonDTO(id=s.signer_id, full_name=s.signer_full_name)
                if s.signer_id
                else None,
                signer_full_name=s.signer_full_name,
                signed_at=s.signed_at,
                cert_full_name=s.cert_full_name,
                cert_serial_number=s.cert_serial_number,
                cert_valid_to=s.cert_valid_to,
                document_hash=s.document_hash,
            )
            for s in act.signatures
        ],
        events=[
            ActEventDTO(
                event=e.event,
                from_status=e.from_status,
                to_status=e.to_status,
                actor=PersonDTO(id=e.actor_id, full_name=e.actor_name) if e.actor_id else None,
                actor_name=e.actor_name,
                comment=e.comment,
                created_at=e.created_at,
            )
            for e in act.events
        ],
        verify_url=verify_url(act),
        actions=actions,
    )
