"""Операции заявителя: черновик, форма, место деятельности, фото, отправка,
прогресс и история."""

from pathlib import Path

from fastapi import UploadFile

from src.account.models.user_model import UserORM
from src.account.profile import missing_profile_fields
from src.account.schemas.user_schema import CurrentUserDTO
from src.application.enums import (
    SUBJECT_TYPES_WITH_COMPANY,
    SUBJECT_TYPES_WITH_FOUNDERS,
    SUBJECT_TYPES_WITH_LEGAL_NAME,
    ApplicationStatus,
    SubjectType,
)
from src.application.mappers import (
    ApplicationDataMapper,
    FounderDataMapper,
    PhotoDataMapper,
    company_dto,
    location_dto,
    project_dto,
)
from src.application.models.application_model import ApplicationORM
from src.application.schemas.application_schema import (
    ApplicationAddDTO,
    ApplicationBankDTO,
    ApplicationCreateDTO,
    ApplicationDetailDTO,
    ApplicationFilterDTO,
    ApplicationProgressDTO,
    ApplicationUpdateDTO,
    CompanyDTO,
    DocumentAddDTO,
    DocumentDTO,
    FounderAddDTO,
    FounderCreateDTO,
    FounderDTO,
    FounderUpdateDTO,
    LocationDTO,
    LocationResponseDTO,
    PhotoAddDTO,
    PhotoDTO,
    ProjectDTO,
    ProjectResponseDTO,
    StatusHistoryDTO,
    SubmissionCheckDTO,
)
from src.application.schemas.bank_schema import BankDTO
from src.application.services.base import ApplicationBaseService, now
from src.application.services.photo_storage import DocumentStorage, PhotoStorage
from src.application.services.scoring_service import ScoringService
from src.application.workflow import build_progress
from src.common.responses.exceptions import (
    ApplicantProfileIncompleteException,
    ApplicationNotEditableException,
    ApplicationValidationException,
    BankNotFoundException,
    BankSubjectTypeMismatchException,
    CompanyNotAllowedException,
    DocumentLimitExceededException,
    DocumentNotFoundException,
    FounderLimitExceededException,
    FounderNotFoundException,
    FoundersNotAllowedException,
    PhotoLimitExceededException,
    PhotoNotFoundException,
    UserNotFoundException,
)
from src.config import settings


class ApplicationService(ApplicationBaseService):
    storage = PhotoStorage()
    document_storage = DocumentStorage()

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

        # YIA SSO даёт только Ф.И.О. и ПИНФЛ; телефон, паспорт, ИНН, email, пол и дату
        # рождения заявитель дополняет через PATCH /auth/me до создания заявки.
        missing = missing_profile_fields(applicant)
        if missing:
            raise ApplicantProfileIncompleteException(missing=missing)

        self._assert_company_allowed(data.subject_type, data.company)
        self._assert_founders_allowed(data.subject_type, data.founders)

        number = await self.db.application.next_number()

        created = await self.db.application.add(
            ApplicationAddDTO(
                number=number,
                applicant_id=applicant.id,
                # Снимок данных заявителя; в заявке они не редактируются.
                **self._applicant_snapshot(applicant),
                subject_type=data.subject_type,
                legal_name=self._legal_name_for(data.subject_type, data.legal_name),
                **self._company_columns(data.company),
            )
        )

        for founder in data.founders or []:
            await self.db.application_founder.add(
                FounderAddDTO(application_id=created.id, **founder.model_dump())
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

        if data.company is not None:
            self._assert_company_allowed(subject_type, data.company)

        if (
            subject_type != application.subject_type
            and application.bank is not None
            and subject_type not in application.bank.allowed_subject_types
        ):
            # Выбранный ранее банк не работает с новым типом субъекта — выбор сбрасывается,
            # заявитель выбирает банк заново (PUT /applications/{id}/bank).
            application.bank_id = None

        application.subject_type = subject_type
        application.legal_name = self._legal_name_for(
            subject_type,
            changes.get("legal_name", application.legal_name),
        )

        if data.company is not None:
            # Частичное обновление: меняются только переданные поля руководителя.
            for column, value in self._company_columns(data.company, partial=True).items():
                setattr(application, column, value)

        if subject_type not in SUBJECT_TYPES_WITH_COMPANY:
            # ИП / самозанятый: реквизиты предприятия не используются.
            for column in self._company_columns(None):
                setattr(application, column, None)

        if subject_type not in SUBJECT_TYPES_WITH_FOUNDERS and application.founders:
            # ИП / самозанятый: список учредителей не используется.
            await self.db.application_founder.delete(application_id=application.id)

        await self.db.commit()
        return ApplicationDataMapper.map_to_detail(await self.reload(application_id))

    # ---------- банк ----------

    async def set_bank(
        self, application_id: int, user: CurrentUserDTO, data: ApplicationBankDTO
    ) -> BankDTO:
        """Заявитель выбирает банк из каталога (GET /banks?subject_type=...).
        Банк должен быть активен и работать с типом субъекта заявки."""
        application = await self._get_editable(application_id, user)

        bank = await self._validate_bank(application.subject_type, data.bank_id)
        application.bank_id = bank.id

        await self.db.commit()
        return bank

    async def _validate_bank(self, subject_type: SubjectType | None, bank_id: int) -> BankDTO:
        bank = await self.db.bank.get_one_or_none(id=bank_id)
        if bank is None or not bank.is_active:
            raise BankNotFoundException()
        if subject_type is not None and subject_type not in bank.allowed_subject_types:
            raise BankSubjectTypeMismatchException()
        return bank

    # ---------- учредители ----------

    async def add_founder(
        self, application_id: int, user: CurrentUserDTO, data: FounderCreateDTO
    ) -> FounderDTO:
        application = await self._get_editable(application_id, user)
        self._assert_founders_allowed(application.subject_type, [data])

        count = await self.db.application_founder.count_for_application(application.id)
        if count >= settings.MAX_APPLICATION_FOUNDERS:
            raise FounderLimitExceededException(
                f"Maximum number of founders reached ({settings.MAX_APPLICATION_FOUNDERS})"
            )

        founder = await self.db.application_founder.add(
            FounderAddDTO(application_id=application.id, **data.model_dump())
        )
        await self.db.commit()
        return founder

    async def update_founder(
        self,
        application_id: int,
        user: CurrentUserDTO,
        founder_id: int,
        data: FounderUpdateDTO,
    ) -> FounderDTO:
        application = await self._get_editable(application_id, user)

        founder = await self.db.application_founder.get_orm(application.id, founder_id)
        if founder is None:
            raise FounderNotFoundException()

        for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
            setattr(founder, field, value)

        await self.db.commit()
        return FounderDataMapper.map_to_domain_entity(founder)

    async def delete_founder(
        self, application_id: int, user: CurrentUserDTO, founder_id: int
    ) -> None:
        application = await self._get_editable(application_id, user)

        founder = await self.db.application_founder.get_orm(application.id, founder_id)
        if founder is None:
            raise FounderNotFoundException()

        await self.db.application_founder.delete(id=founder.id)
        await self.db.commit()

    async def set_project(
        self,
        application_id: int,
        user: CurrentUserDTO,
        data: ProjectDTO,
    ) -> ProjectResponseDTO:
        """Информация о проекте: сумма, срок, стоимость, рабочие места, описание.
        Заполняется целиком (PUT), доступна только в черновике."""
        application = await self._get_editable(application_id, user)

        application.project_requested_amount = data.requested_amount
        application.project_loan_term_months = data.loan_term_months
        application.project_total_cost = data.total_cost
        application.project_jobs_count = data.jobs_count
        application.project_description = data.description

        await self.db.commit()
        return project_dto(application)

    async def set_location(
        self,
        application_id: int,
        user: CurrentUserDTO,
        data: LocationDTO,
    ) -> LocationResponseDTO:
        application = await self._get_editable(application_id, user)

        application.location_lat = data.lat
        application.location_lng = data.lng
        application.location_region = data.region
        application.location_district = data.district
        application.location_makhalla = data.makhalla
        application.location_address = data.address
        application.location_confirmed = data.confirmed

        await self.db.commit()
        return location_dto(application)

    async def delete_draft(self, application_id: int, user: CurrentUserDTO) -> None:
        application = await self._get_editable(application_id, user)

        # Файлы черновика (фото и документы) удаляются вместе с каталогом заявки.
        await self.storage.delete_application_dir(application.id)

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

    # ---------- документы (PDF / DOCX) ----------

    async def add_document(
        self, application_id: int, user: CurrentUserDTO, upload: UploadFile
    ) -> DocumentDTO:
        application = await self._get_editable(application_id, user)

        count = await self.db.application_document.count_for_application(application.id)
        if count >= settings.MAX_APPLICATION_DOCUMENTS:
            raise DocumentLimitExceededException(
                f"Maximum number of documents reached ({settings.MAX_APPLICATION_DOCUMENTS})"
            )

        storage_path, size, content_type = await self.document_storage.save(application.id, upload)

        document = await self.db.application_document.add(
            DocumentAddDTO(
                application_id=application.id,
                file_name=upload.filename or Path(storage_path).name,
                storage_path=storage_path,
                content_type=content_type,
                size=size,
            )
        )
        await self.db.commit()
        return document

    async def delete_document(
        self, application_id: int, user: CurrentUserDTO, document_id: int
    ) -> None:
        application = await self._get_editable(application_id, user)

        document = await self.db.application_document.get_orm(application.id, document_id)
        if document is None:
            raise DocumentNotFoundException()

        await self.document_storage.delete(document.storage_path)
        await self.db.application_document.delete(id=document.id)
        await self.db.commit()

    async def get_document_path(
        self, application_id: int, user: CurrentUserDTO, document_id: int
    ) -> tuple[Path, str, str]:
        """Файл открывается только тем, кто имеет доступ к заявке."""
        application = await self.get_for_user(application_id, user)

        document = await self.db.application_document.get_orm(application.id, document_id)
        if document is None:
            raise DocumentNotFoundException()

        return (
            self.document_storage.absolute_path(document.storage_path),
            document.content_type,
            document.file_name,
        )

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
            company=company_dto(application),
            founders_count=len(application.founders),
            project=project_dto(application),
            bank=BankDTO.model_validate(application.bank, from_attributes=True)
            if application.bank
            else None,
            location=location_dto(application),
            photos_count=len(application.photos),
            max_photos=settings.MAX_APPLICATION_PHOTOS,
            documents_count=len(application.documents),
            max_documents=settings.MAX_APPLICATION_DOCUMENTS,
        )

    async def submit(self, application_id: int, user: CurrentUserDTO) -> ApplicationDetailDTO:
        application = await self._get_editable(application_id, user)

        missing = await self._collect_missing(application)
        if missing:
            raise ApplicationValidationException(missing=missing)

        # Заявитель мог дополнить профиль после создания черновика —
        # в снимок попадают актуальные данные на момент отправки.
        for field, value in self._applicant_snapshot(application.applicant).items():
            setattr(application, field, value)

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
    def _applicant_snapshot(applicant: UserORM) -> dict:
        return {
            "applicant_full_name": applicant.full_name,
            "applicant_phone": applicant.phone,
            "applicant_passport": applicant.passport_number,
            "applicant_pinfl": applicant.pinfl,
            "applicant_inn": applicant.inn,
            "applicant_email": applicant.email,
            "applicant_gender": applicant.gender,
            "applicant_date_of_birth": applicant.date_of_birth,
        }

    # Поле DTO проекта -> колонка заявки.
    PROJECT_COLUMNS = {
        "requested_amount": "project_requested_amount",
        "loan_term_months": "project_loan_term_months",
        "total_cost": "project_total_cost",
        "jobs_count": "project_jobs_count",
        "description": "project_description",
    }

    # Поле DTO -> колонка заявки.
    COMPANY_COLUMNS = {
        "inn": "company_inn",
        "director_full_name": "director_full_name",
        "director_passport": "director_passport",
        "director_phone": "director_phone",
        "director_date_of_birth": "director_date_of_birth",
    }

    @classmethod
    def _company_columns(cls, company: CompanyDTO | None, partial: bool = False) -> dict:
        if company is None:
            return dict.fromkeys(cls.COMPANY_COLUMNS.values())
        values = company.model_dump(exclude_unset=partial)
        return {cls.COMPANY_COLUMNS[field]: value for field, value in values.items()}

    @staticmethod
    def _assert_company_allowed(
        subject_type: SubjectType | None, company: CompanyDTO | None
    ) -> None:
        if company is None or not any(company.model_dump(exclude_none=True).values()):
            return
        if subject_type is not None and subject_type not in SUBJECT_TYPES_WITH_COMPANY:
            raise CompanyNotAllowedException()

    @staticmethod
    def _assert_founders_allowed(subject_type: SubjectType | None, founders: list | None) -> None:
        if not founders:
            return
        if subject_type not in SUBJECT_TYPES_WITH_FOUNDERS:
            raise FoundersNotAllowedException()
        if len(founders) > settings.MAX_APPLICATION_FOUNDERS:
            raise FounderLimitExceededException(
                f"Maximum number of founders reached ({settings.MAX_APPLICATION_FOUNDERS})"
            )

    @staticmethod
    def _legal_name_for(subject_type: SubjectType | None, legal_name: str | None) -> str | None:
        # Для самозанятого поле юридического наименования не используется.
        if subject_type is not None and subject_type not in SUBJECT_TYPES_WITH_LEGAL_NAME:
            return None
        return legal_name

    async def _collect_missing(self, application: ApplicationORM) -> list[str]:
        missing: list[str] = []

        if application.subject_type is None:
            missing.append("subject_type")
        elif (
            application.subject_type in SUBJECT_TYPES_WITH_LEGAL_NAME and not application.legal_name
        ):
            missing.append("legal_name")

        if application.bank is None or not application.bank.is_active:
            missing.append("bank_id")
        elif (
            application.subject_type is not None
            and application.subject_type not in application.bank.allowed_subject_types
        ):
            missing.append("bank_id")

        if application.subject_type in SUBJECT_TYPES_WITH_COMPANY:
            for field, column in self.COMPANY_COLUMNS.items():
                if not getattr(application, column):
                    missing.append(f"company.{field}")

        if application.subject_type in SUBJECT_TYPES_WITH_FOUNDERS and not application.founders:
            missing.append("founders")

        for field, column in self.PROJECT_COLUMNS.items():
            if getattr(application, column) is None:
                missing.append(f"project.{field}")

        if (
            application.location_lat is None
            or application.location_lng is None
            or not application.location_region
            or not application.location_district
            or not application.location_makhalla
        ):
            missing.append("location")
        elif not application.location_confirmed:
            missing.append("location.confirmed")

        if len(application.photos) > settings.MAX_APPLICATION_PHOTOS:
            missing.append("photos")
        if len(application.documents) > settings.MAX_APPLICATION_DOCUMENTS:
            missing.append("documents")

        # Проверяем живой профиль, а не снимок: заявитель дополняет данные
        # через PATCH /auth/me уже после создания черновика.
        missing.extend(
            f"applicant.{field}" for field in missing_profile_fields(application.applicant)
        )

        return missing

    @staticmethod
    def photo_to_dto(model) -> PhotoDTO:
        return PhotoDataMapper.map_to_domain_entity(model)
