"""Операции заявителя: черновик, форма, место деятельности, фото, отправка,
прогресс и история."""

from pathlib import Path

from fastapi import UploadFile

from src.account.schemas.user_schema import CurrentUserDTO
from src.application.enums import (
    SUBJECT_TYPES_WITH_LEGAL_NAME,
    ApplicationStatus,
    SubjectType,
)
from src.application.mappers import ApplicationDataMapper, PhotoDataMapper
from src.application.models.application_model import ApplicationORM
from src.application.schemas.application_schema import (
    ApplicationAddDTO,
    ApplicationCreateDTO,
    ApplicationDetailDTO,
    ApplicationFilterDTO,
    ApplicationProgressDTO,
    ApplicationUpdateDTO,
    LocationDTO,
    LocationResponseDTO,
    PhotoAddDTO,
    PhotoDTO,
    StatusHistoryDTO,
    SubmissionCheckDTO,
)
from src.application.schemas.bank_schema import BankDTO
from src.application.services.base import ApplicationBaseService, now
from src.application.services.photo_storage import PhotoStorage
from src.application.services.scoring_service import ScoringService
from src.application.workflow import build_progress
from src.common.responses.exceptions import (
    ApplicationNotEditableException,
    ApplicationValidationException,
    BankNotFoundException,
    BankSubjectTypeMismatchException,
    PhotoLimitExceededException,
    PhotoNotFoundException,
    UserNotFoundException,
)
from src.config import settings


class ApplicationService(ApplicationBaseService):
    storage = PhotoStorage()

    # ---------- чтение ----------

    async def get_my_applications(
        self,
        user: CurrentUserDTO,
        filters: ApplicationFilterDTO,
        page: int | None,
        per_page: int | None,
    ) -> dict:
        return await self.db.application.get_all(
            filters,
            page=page,
            per_page=per_page,
            applicant_id=user.id,
        )

    async def get_detail(self, application_id: int, user: CurrentUserDTO) -> ApplicationDetailDTO:
        application = await self.get_for_user(application_id, user)
        return ApplicationDataMapper.map_to_detail(application)

    async def get_history(
        self, application_id: int, user: CurrentUserDTO
    ) -> list[StatusHistoryDTO]:
        await self.get_for_user(application_id, user)
        return await self.db.status_history.get_for_application(application_id)

    async def get_progress(
        self, application_id: int, user: CurrentUserDTO
    ) -> ApplicationProgressDTO:
        application = await self.get_for_user(application_id, user)
        detail = ApplicationDataMapper.map_to_detail(application)
        return ApplicationProgressDTO(
            application_id=application.id,
            number=application.number,
            status=application.status,
            is_rejected=detail.rejection_reason is not None,
            rejection_message=detail.rejection_reason,
            steps=build_progress(application.status, application.scoring_retry_required),
        )

    # ---------- черновик ----------

    async def create(
        self, user: CurrentUserDTO, data: ApplicationCreateDTO
    ) -> ApplicationDetailDTO:
        applicant = await self.db.user.get_orm_by_id(user.id)
        if applicant is None:
            raise UserNotFoundException()

        await self._validate_bank(data.subject_type, data.bank_id)

        number = await self.db.application.next_number()

        created = await self.db.application.add(
            ApplicationAddDTO(
                number=number,
                applicant_id=applicant.id,
                # Данные из OneID подставляются автоматически и не редактируются заявителем.
                applicant_full_name=applicant.full_name,
                applicant_phone=applicant.phone,
                applicant_passport=applicant.passport_number,
                applicant_pinfl=applicant.pinfl,
                applicant_inn=applicant.inn,
                subject_type=data.subject_type,
                legal_name=self._legal_name_for(data.subject_type, data.legal_name),
                bank_id=data.bank_id,
            )
        )

        application = await self.get_orm_or_404(created.id)
        await self.add_history(
            application,
            to_status=ApplicationStatus.DRAFT,
            event="created",
            actor=user,
            comment="Заявка создана",
        )
        await self.db.commit()

        return ApplicationDataMapper.map_to_detail(await self.reload(created.id))

    async def update(
        self,
        application_id: int,
        user: CurrentUserDTO,
        data: ApplicationUpdateDTO,
    ) -> ApplicationDetailDTO:
        application = await self._get_editable(application_id, user)
        changes = data.model_dump(exclude_unset=True)

        subject_type = changes.get("subject_type", application.subject_type)
        bank_id = changes.get("bank_id", application.bank_id)

        if "subject_type" in changes and subject_type != application.subject_type:
            # При смене типа субъекта банк, не подходящий новому типу, сбрасывается.
            if bank_id is not None and "bank_id" not in changes:
                bank = await self.db.bank.get_one_or_none(id=bank_id)
                if bank is None or subject_type not in bank.allowed_subject_types:
                    bank_id = None

        await self._validate_bank(subject_type, bank_id)

        application.subject_type = subject_type
        application.bank_id = bank_id
        application.legal_name = self._legal_name_for(
            subject_type,
            changes.get("legal_name", application.legal_name),
        )

        await self.db.commit()
        return ApplicationDataMapper.map_to_detail(await self.reload(application_id))

    async def set_location(
        self,
        application_id: int,
        user: CurrentUserDTO,
        data: LocationDTO,
    ) -> LocationResponseDTO:
        application = await self._get_editable(application_id, user)

        application.location_lat = data.lat
        application.location_lng = data.lng
        application.location_address = data.address
        application.location_confirmed = data.confirmed

        await self.db.commit()
        return LocationResponseDTO(
            lat=application.location_lat,
            lng=application.location_lng,
            address=application.location_address,
            confirmed=application.location_confirmed,
        )

    async def delete_draft(self, application_id: int, user: CurrentUserDTO) -> None:
        application = await self._get_editable(application_id, user)

        for photo in application.photos:
            await self.storage.delete(photo.storage_path)

        await self.db.application.delete(id=application.id)
        await self.db.commit()

    # ---------- фото ----------

    async def add_photo(
        self, application_id: int, user: CurrentUserDTO, upload: UploadFile
    ) -> PhotoDTO:
        application = await self._get_editable(application_id, user)

        count = await self.db.application_photo.count_for_application(application.id)
        if count >= settings.MAX_APPLICATION_PHOTOS:
            raise PhotoLimitExceededException(
                f"Maximum number of photos reached ({settings.MAX_APPLICATION_PHOTOS})"
            )

        storage_path, size, content_type = await self.storage.save(application.id, upload)

        photo = await self.db.application_photo.add(
            PhotoAddDTO(
                application_id=application.id,
                file_name=upload.filename or Path(storage_path).name,
                storage_path=storage_path,
                content_type=content_type,
                size=size,
            )
        )
        await self.db.commit()
        return photo

    async def delete_photo(self, application_id: int, user: CurrentUserDTO, photo_id: int) -> None:
        application = await self._get_editable(application_id, user)

        photo = await self.db.application_photo.get_orm(application.id, photo_id)
        if photo is None:
            raise PhotoNotFoundException()

        await self.storage.delete(photo.storage_path)
        await self.db.application_photo.delete(id=photo.id)
        await self.db.commit()

    async def get_photo_path(
        self, application_id: int, user: CurrentUserDTO, photo_id: int
    ) -> tuple[Path, str, str]:
        """Файл открывается только тем, кто имеет доступ к заявке."""
        application = await self.get_for_user(application_id, user)

        photo = await self.db.application_photo.get_orm(application.id, photo_id)
        if photo is None:
            raise PhotoNotFoundException()

        return self.storage.absolute_path(photo.storage_path), photo.content_type, photo.file_name

    # ---------- отправка ----------

    async def check_submission(
        self, application_id: int, user: CurrentUserDTO
    ) -> SubmissionCheckDTO:
        application = await self.get_for_user(application_id, user)
        missing = await self._collect_missing(application)

        return SubmissionCheckDTO(
            is_ready=not missing,
            missing=missing,
            subject_type=application.subject_type,
            legal_name=application.legal_name,
            bank=BankDTO.model_validate(application.bank, from_attributes=True)
            if application.bank
            else None,
            location=LocationResponseDTO(
                lat=application.location_lat,
                lng=application.location_lng,
                address=application.location_address,
                confirmed=application.location_confirmed,
            ),
            photos_count=len(application.photos),
            max_photos=settings.MAX_APPLICATION_PHOTOS,
        )

    async def submit(self, application_id: int, user: CurrentUserDTO) -> ApplicationDetailDTO:
        application = await self._get_editable(application_id, user)

        missing = await self._collect_missing(application)
        if missing:
            raise ApplicationValidationException(missing=missing)

        # Повторная проверка соответствия типа субъекта и банка на стороне сервера.
        await self._validate_bank(application.subject_type, application.bank_id)

        application.submitted_at = now()
        await self.transition(
            application,
            ApplicationStatus.SUBMITTED,
            event="submitted",
            actor=user,
            comment="Заявка отправлена заявителем",
        )

        # Заявка попадает в очередь на скоринг.
        await ScoringService(self.db).start(application, actor=None)

        await self.db.commit()
        return ApplicationDataMapper.map_to_detail(await self.reload(application_id))

    # ---------- вспомогательное ----------

    async def _get_editable(self, application_id: int, user: CurrentUserDTO) -> ApplicationORM:
        application = await self.get_for_user(application_id, user)
        if application.status != ApplicationStatus.DRAFT:
            raise ApplicationNotEditableException()
        return application

    @staticmethod
    def _legal_name_for(subject_type: SubjectType | None, legal_name: str | None) -> str | None:
        # Для самозанятого поле юридического наименования не используется.
        if subject_type is not None and subject_type not in SUBJECT_TYPES_WITH_LEGAL_NAME:
            return None
        return legal_name

    async def _validate_bank(self, subject_type: SubjectType | None, bank_id: int | None) -> None:
        if bank_id is None:
            return

        bank = await self.db.bank.get_one_or_none(id=bank_id)
        if bank is None or not bank.is_active:
            raise BankNotFoundException()

        if subject_type is not None and subject_type not in bank.allowed_subject_types:
            raise BankSubjectTypeMismatchException()

    async def _collect_missing(self, application: ApplicationORM) -> list[str]:
        missing: list[str] = []

        if application.subject_type is None:
            missing.append("subject_type")
        elif (
            application.subject_type in SUBJECT_TYPES_WITH_LEGAL_NAME and not application.legal_name
        ):
            missing.append("legal_name")

        if application.bank_id is None:
            missing.append("bank_id")
        elif application.subject_type is not None:
            bank = await self.db.bank.get_one_or_none(id=application.bank_id)
            if bank is None or application.subject_type not in bank.allowed_subject_types:
                missing.append("bank_id")

        if application.location_lat is None or application.location_lng is None:
            missing.append("location")
        elif not application.location_confirmed:
            missing.append("location.confirmed")

        if len(application.photos) > settings.MAX_APPLICATION_PHOTOS:
            missing.append("photos")

        if not application.applicant_full_name or not application.applicant_pinfl:
            missing.append("applicant")

        return missing

    @staticmethod
    def photo_to_dto(model) -> PhotoDTO:
        return PhotoDataMapper.map_to_domain_entity(model)
