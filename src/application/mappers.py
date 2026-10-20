from src.account.models.user_model import UserORM
from src.application.enums import ApplicationStatus
from src.application.models.application_model import ApplicationORM
from src.application.models.bank_model import BankORM
from src.application.models.council_assignment_model import CouncilAssignmentORM
from src.application.models.demand_document_model import DemandDocumentORM
from src.application.models.photo_model import ApplicationPhotoORM
from src.application.models.resource_allocation_model import ResourceAllocationORM
from src.application.models.scoring_model import ScoringAttemptORM
from src.application.models.status_history_model import StatusHistoryORM
from src.application.schemas.application_schema import (
    ActorDTO,
    ApplicantSnapshotDTO,
    ApplicationDetailDTO,
    ApplicationListItemDTO,
    BankStageDTO,
    CouncilAssignmentDTO,
    DemandDocumentDTO,
    LocationResponseDTO,
    PhotoDTO,
    ResourceAllocationDTO,
    ScoringAttemptDTO,
    StatusHistoryDTO,
)
from src.application.schemas.bank_schema import BankDTO
from src.config import settings
from src.utils.base_rep.mappers.base import DataMapper


def actor(model: UserORM | None) -> ActorDTO | None:
    if model is None:
        return None
    return ActorDTO(id=model.id, full_name=model.full_name, username=model.username)


class BankDataMapper(DataMapper):
    db_model = BankORM
    schema = BankDTO


class PhotoDataMapper(DataMapper):
    db_model = ApplicationPhotoORM
    schema = PhotoDTO

    @staticmethod
    def map_to_domain_entity(model: ApplicationPhotoORM) -> PhotoDTO:
        return PhotoDTO(
            id=model.id,
            file_name=model.file_name,
            content_type=model.content_type,
            size=model.size,
            url=f"{settings.API_PREFIX}/applications/{model.application_id}/photos/{model.id}/file",
            created_at=model.created_at,
        )


class StatusHistoryDataMapper(DataMapper):
    db_model = StatusHistoryORM
    schema = StatusHistoryDTO

    @staticmethod
    def map_to_domain_entity(model: StatusHistoryORM) -> StatusHistoryDTO:
        return StatusHistoryDTO(
            id=model.id,
            from_status=model.from_status,
            to_status=model.to_status,
            event=model.event,
            comment=model.comment,
            actor=actor(model.actor),
            actor_role=model.actor_role,
            created_at=model.created_at,
        )


class ScoringAttemptDataMapper(DataMapper):
    db_model = ScoringAttemptORM
    schema = ScoringAttemptDTO

    @staticmethod
    def map_to_domain_entity(model: ScoringAttemptORM) -> ScoringAttemptDTO:
        return ScoringAttemptDTO(
            id=model.id,
            provider=model.provider,
            result=model.result,
            eligibility_passed=model.eligibility_passed,
            details=model.details,
            error_message=model.error_message,
            recorded_by=actor(model.recorded_by),
            created_at=model.created_at,
        )


class CouncilAssignmentDataMapper(DataMapper):
    db_model = CouncilAssignmentORM
    schema = CouncilAssignmentDTO

    @staticmethod
    def map_to_domain_entity(model: CouncilAssignmentORM) -> CouncilAssignmentDTO:
        return CouncilAssignmentDTO(
            id=model.id,
            council_member=actor(model.council_member),
            assigned_at=model.assigned_at,
            decision=model.decision,
            reason=model.reason,
            decided_at=model.decided_at,
        )


class DemandDocumentDataMapper(DataMapper):
    db_model = DemandDocumentORM
    schema = DemandDocumentDTO


class ResourceAllocationDataMapper(DataMapper):
    db_model = ResourceAllocationORM
    schema = ResourceAllocationDTO

    @staticmethod
    def map_to_domain_entity(model: ResourceAllocationORM) -> ResourceAllocationDTO:
        return ResourceAllocationDTO(
            id=model.id,
            amount=model.amount,
            currency=model.currency,
            reference_number=model.reference_number,
            details=model.details,
            allocated_by=actor(model.allocated_by),
            allocated_at=model.allocated_at,
        )


def _rejection_reason(model: ApplicationORM) -> str | None:
    if model.status == ApplicationStatus.BANK_REJECTED:
        return model.bank_decision_reason
    if model.status == ApplicationStatus.COUNCIL_REJECTED:
        return model.council_reject_reason
    if model.status == ApplicationStatus.SCORING_FAILED:
        return "Вы не прошли систему скоринга."
    if model.status == ApplicationStatus.ELIGIBILITY_FAILED:
        return "Заявка не соответствует требованиям Фонда."
    return None


class ApplicationDataMapper(DataMapper):
    db_model = ApplicationORM
    schema = ApplicationListItemDTO

    @staticmethod
    def _list_fields(model: ApplicationORM) -> dict:
        return {
            "id": model.id,
            "number": model.number,
            "status": model.status,
            "subject_type": model.subject_type,
            "legal_name": model.legal_name,
            "bank": BankDataMapper.map_to_domain_entity(model.bank) if model.bank else None,
            "applicant_full_name": model.applicant_full_name,
            "scoring_retry_required": model.scoring_retry_required,
            "submitted_at": model.submitted_at,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

    @staticmethod
    def map_to_domain_entity(model: ApplicationORM) -> ApplicationListItemDTO:
        return ApplicationListItemDTO(**ApplicationDataMapper._list_fields(model))

    @staticmethod
    def map_to_detail(model: ApplicationORM) -> ApplicationDetailDTO:
        return ApplicationDetailDTO(
            **ApplicationDataMapper._list_fields(model),
            applicant_id=model.applicant_id,
            applicant=ApplicantSnapshotDTO(
                full_name=model.applicant_full_name,
                phone=model.applicant_phone,
                passport_number=model.applicant_passport,
                pinfl=model.applicant_pinfl,
                inn=model.applicant_inn,
            ),
            location=LocationResponseDTO(
                lat=model.location_lat,
                lng=model.location_lng,
                address=model.location_address,
                confirmed=model.location_confirmed,
            ),
            photos=[PhotoDataMapper.map_to_domain_entity(p) for p in model.photos],
            bank_stage=BankStageDTO(
                sent_to_bank_at=model.sent_to_bank_at,
                accepted_by=actor(model.bank_accepted_by),
                accepted_at=model.bank_accepted_at,
                decision=model.bank_decision,
                decision_reason=model.bank_decision_reason,
                decided_by=actor(model.bank_decided_by),
                decided_at=model.bank_decided_at,
            ),
            council_assignments=[
                CouncilAssignmentDataMapper.map_to_domain_entity(a)
                for a in model.council_assignments
            ],
            council_decided_at=model.council_decided_at,
            council_reject_reason=model.council_reject_reason,
            demand_document=(
                DemandDocumentDataMapper.map_to_domain_entity(model.demand_document)
                if model.demand_document
                else None
            ),
            resource_allocation=(
                ResourceAllocationDataMapper.map_to_domain_entity(model.resource_allocation)
                if model.resource_allocation
                else None
            ),
            completed_at=model.completed_at,
            rejection_reason=_rejection_reason(model),
        )
