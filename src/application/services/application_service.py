"""Операции заявителя: заявка по продукту Фонда, ответы на поля этапов, файлы,
отправка, прогресс и история."""

from pathlib import Path

from fastapi import UploadFile

from src.account.models.user_model import UserORM
from src.account.profile import missing_profile_fields
from src.account.schemas.user_schema import CurrentUserDTO
from src.application.enums import ApplicationStatus, SubjectType
from src.application.field_values import normalize_value
from src.application.mappers import ApplicationDataMapper, build_form, field_file_dto
from src.application.models.answer_model import ApplicationFieldFileORM, ApplicationFieldValueORM
from src.application.models.application_model import ApplicationORM
from src.application.schemas.application_schema import (
    ApplicationAddDTO,
    ApplicationBankDTO,
    ApplicationCreateDTO,
    ApplicationDetailDTO,
    ApplicationFilterDTO,
    ApplicationProgressDTO,
    ApplicationUpdateDTO,
    FieldFileDTO,
    FormStageDTO,
    StageValuesDTO,
    StatusHistoryDTO,
    SubmissionCheckDTO,
)
from src.application.schemas.bank_schema import BankDTO
from src.application.services.base import ApplicationBaseService, now
from src.application.services.photo_storage import FieldDocumentStorage, FieldPhotoStorage
from src.application.services.scoring_service import ScoringService
from src.application.workflow import build_progress
from src.common.responses.exceptions import (
    ApplicantProfileIncompleteException,
    ApplicationNotEditableException,
    ApplicationValidationException,
    BankNotFoundException,
    BankNotInProductException,
    BankSubjectTypeMismatchException,
    FieldFileLimitExceededException,
    FieldFileNotFoundException,
    FieldValueInvalidException,
    FileFieldException,
    ProductFieldNotFoundException,
    ProductNotAvailableException,
    ProductStageNotFoundException,
    ProductWithoutBankException,
    UserNotFoundException,
)
from src.product.enums import FILE_FIELD_TYPES, FieldType
from src.product.mappers import product_brief
from src.product.models.product_model import ProductFieldORM, ProductORM, ru_name
from src.product.services.product_service import is_available


class ApplicationService(ApplicationBaseService):
    photo_storage = FieldPhotoStorage()
    document_storage = FieldDocumentStorage()

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
            steps=build_progress(
                application.status,
                application.scoring_retry_required,
                uses_bank=application.product.uses_bank if application.product else True,
            ),
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

        product = await self._available_product(data.product_id, data.subject_type)
        if data.bank_id is not None:
            if not product.uses_bank:
                raise ProductWithoutBankException()
            await self._validate_bank(product, data.subject_type, data.bank_id)

        created_id = await self.db.application.add(
            ApplicationAddDTO(
                number=await self.db.application.next_number(),
                applicant_id=applicant.id,
                # Снимок данных заявителя; в заявке они не редактируются.
                **self._applicant_snapshot(applicant),
                product_id=product.id,
                subject_type=data.subject_type,
                bank_id=data.bank_id,
            )
        )

        application = await self.get_orm_or_404(created_id)
        await self.add_history(
            application,
            to_status=ApplicationStatus.DRAFT,
            event="created",
            actor=user,
            comment=f"Заявка создана по продукту «{ru_name(product.translations)}»",
        )
        await self.db.commit()

        return ApplicationDataMapper.map_to_detail(await self.reload(created_id))

    async def update(
        self,
        application_id: int,
        user: CurrentUserDTO,
        data: ApplicationUpdateDTO,
    ) -> ApplicationDetailDTO:
        """Смена продукта или типа субъекта в черновике."""
        application = await self._get_editable(application_id, user)
        subject_type = data.subject_type or application.subject_type
        product_id = data.product_id or application.product_id

        if product_id is None:
            raise ProductNotAvailableException()
        product = await self._available_product(product_id, subject_type)

        if product.id != application.product_id:
            # Другая анкета: ответы и банк прежнего продукта больше не подходят.
            await self._clear_answers(application)
            application.product_id = product.id
            application.bank_id = None

        application.subject_type = subject_type
        bank = application.bank
        if bank is not None and (
            subject_type not in bank.allowed_subject_types
            or bank.id not in {b.id for b in product.banks}
        ):
            application.bank_id = None

        await self.db.commit()
        return ApplicationDataMapper.map_to_detail(await self.reload(application_id))

    async def delete_draft(self, application_id: int, user: CurrentUserDTO) -> None:
        application = await self._get_editable(application_id, user)

        # Файлы черновика удаляются вместе с каталогом заявки.
        await self.photo_storage.delete_application_dir(application.id)

        await self.db.application.delete(id=application.id)
        await self.db.commit()

    # ---------- банк ----------

    async def set_bank(
        self, application_id: int, user: CurrentUserDTO, data: ApplicationBankDTO
    ) -> BankDTO:
        """Заявитель выбирает банк из банков продукта (`banks` в `GET /products/{id}`)."""
        application = await self._get_editable(application_id, user)
        if application.product is None:
            raise ProductNotAvailableException()
        if not application.product.uses_bank:
            raise ProductWithoutBankException()

        bank = await self._validate_bank(
            application.product, application.subject_type, data.bank_id
        )
        application.bank_id = bank.id

        await self.db.commit()
        return bank

    async def _validate_bank(
        self, product: ProductORM, subject_type: SubjectType | None, bank_id: int
    ) -> BankDTO:
        bank = await self.db.bank.get_one_or_none(id=bank_id)
        if bank is None or not bank.is_active:
            raise BankNotFoundException(f"Bank {bank_id} not found or inactive")
        if bank.id not in {b.id for b in product.banks}:
            raise BankNotInProductException()
        if subject_type is not None and subject_type not in bank.allowed_subject_types:
            raise BankSubjectTypeMismatchException(
                f"Bank '{bank.name}' does not work with subject type {subject_type.value}; "
                f"allowed: {', '.join(bank.allowed_subject_types)}"
            )
        return bank

    # ---------- ответы на поля этапов ----------

    async def save_stage(
        self,
        application_id: int,
        user: CurrentUserDTO,
        stage_id: int,
        data: StageValuesDTO,
    ) -> FormStageDTO:
        application = await self._get_editable(application_id, user)
        stage = next(
            (
                s
                for s in (application.product.stages if application.product else [])
                if s.id == stage_id
            ),
            None,
        )
        if stage is None:
            raise ProductStageNotFoundException()

        fields = {field.id: field for field in stage.fields}
        errors: list[dict] = []
        normalized: dict[int, str | None] = {}
        for field_id, raw in data.values.items():
            key = f"values.{field_id}"
            field = fields.get(field_id)
            if field is None:
                errors.append({"field": key, "message": "Field does not belong to this stage"})
                continue
            if field.field_type in FILE_FIELD_TYPES:
                errors.append({"field": key, "message": FileFieldException.message})
                continue
            if raw is None or not raw.strip():
                normalized[field_id] = None
                continue
            try:
                normalized[field_id] = normalize_value(field.field_type, raw)
            except ValueError as exc:
                errors.append({"field": key, "message": str(exc)})
        if errors:
            raise FieldValueInvalidException(errors=errors)

        existing = {value.field_id: value for value in application.field_values}
        for field_id, value in normalized.items():
            current = existing.get(field_id)
            if value is None:
                if current is not None:
                    application.field_values.remove(current)
            elif current is not None:
                current.value = value
            else:
                application.field_values.append(
                    ApplicationFieldValueORM(field_id=field_id, value=value)
                )

        await self.db.commit()
        application = await self.reload(application_id)
        return next(s for s in build_form(application) if s.id == stage_id)

    async def add_field_file(
        self, application_id: int, user: CurrentUserDTO, field_id: int, upload: UploadFile
    ) -> FieldFileDTO:
        application = await self._get_editable(application_id, user)
        field = self._find_field(application, field_id)
        if field.field_type not in FILE_FIELD_TYPES:
            raise FileFieldException()

        count = sum(1 for f in application.field_files if f.field_id == field.id)
        if count >= field.max_files:
            raise FieldFileLimitExceededException(
                f"Maximum number of files for this field reached: {count} of {field.max_files}. "
                "Delete a file before uploading a new one"
            )

        storage = (
            self.photo_storage if field.field_type == FieldType.PHOTO else self.document_storage
        )
        storage_path, size, content_type = await storage.save(application.id, upload)

        file = ApplicationFieldFileORM(
            field_id=field.id,
            file_name=upload.filename or Path(storage_path).name,
            storage_path=storage_path,
            content_type=content_type,
            size=size,
        )
        application.field_files.append(file)
        await self.db.flush()
        await self.db.session.refresh(file)
        await self.db.commit()
        return field_file_dto(file)

    async def delete_field_file(
        self, application_id: int, user: CurrentUserDTO, field_id: int, file_id: int
    ) -> None:
        application = await self._get_editable(application_id, user)
        file = self._find_file(application, field_id, file_id)

        await self.photo_storage.delete(file.storage_path)
        application.field_files.remove(file)
        await self.db.commit()

    async def get_field_file_path(
        self, application_id: int, user: CurrentUserDTO, field_id: int, file_id: int
    ) -> tuple[Path, str, str]:
        """Файл открывается только тем, кто имеет доступ к заявке."""
        application = await self.get_for_user(application_id, user)
        file = self._find_file(application, field_id, file_id)
        return (
            self.photo_storage.absolute_path(file.storage_path),
            file.content_type,
            file.file_name,
        )

    # ---------- отправка ----------

    async def check_submission(
        self, application_id: int, user: CurrentUserDTO
    ) -> SubmissionCheckDTO:
        application = await self.get_for_user(application_id, user)
        missing = self._collect_missing(application)
        product = application.product

        return SubmissionCheckDTO(
            is_ready=not missing,
            missing=missing,
            product=product_brief(product) if product else None,
            product_available=product is not None
            and is_available(product, application.subject_type),
            subject_type=application.subject_type,
            bank=BankDTO.model_validate(application.bank, from_attributes=True)
            if application.bank
            else None,
            stages=build_form(application),
        )

    async def submit(self, application_id: int, user: CurrentUserDTO) -> ApplicationDetailDTO:
        application = await self._get_editable(application_id, user)

        missing = self._collect_missing(application)
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
            raise ApplicationNotEditableException(current_status=application.status.value)
        return application

    async def _available_product(
        self, product_id: int, subject_type: SubjectType | None
    ) -> ProductORM:
        product = await self.db.product.get_orm(product_id)
        if product is None or not is_available(product, subject_type):
            raise ProductNotAvailableException()
        return product

    async def _clear_answers(self, application: ApplicationORM) -> None:
        for file in list(application.field_files):
            await self.photo_storage.delete(file.storage_path)
        application.field_files.clear()
        application.field_values.clear()

    @staticmethod
    def _find_field(application: ApplicationORM, field_id: int) -> ProductFieldORM:
        stages = application.product.stages if application.product else []
        for stage in stages:
            for field in stage.fields:
                if field.id == field_id:
                    return field
        raise ProductFieldNotFoundException()

    def _find_file(
        self, application: ApplicationORM, field_id: int, file_id: int
    ) -> ApplicationFieldFileORM:
        for file in application.field_files:
            if file.id == file_id and file.field_id == field_id:
                return file
        raise FieldFileNotFoundException()

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

    @staticmethod
    def _collect_missing(application: ApplicationORM) -> list[str]:
        missing: list[str] = []
        product = application.product

        if application.subject_type is None:
            missing.append("subject_type")

        if product is None or not is_available(product, application.subject_type):
            missing.append("product_id")

        # Продукт без банка: банк не выбирается, заявку решает Фонд.
        bank = application.bank
        if (product is None or product.uses_bank) and (
            bank is None
            or not bank.is_active
            or product is None
            or bank.id not in {b.id for b in product.banks}
            or (
                application.subject_type is not None
                and application.subject_type not in bank.allowed_subject_types
            )
        ):
            missing.append("bank_id")

        for stage in build_form(application):
            missing.extend(
                f"fields.{field.id}"
                for field in stage.fields
                if field.is_required and not field.value and not field.files
            )

        # Проверяем живой профиль, а не снимок: заявитель дополняет данные
        # через PATCH /auth/me уже после создания черновика.
        missing.extend(
            f"applicant.{field}" for field in missing_profile_fields(application.applicant)
        )

        return missing
