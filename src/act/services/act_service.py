"""Акты выполненных работ (dalolatnoma): черновик исполнителя → подпись исполнителя и
отправка → проверка Фондом → подпись руководителя.

DRAFT ─submit(E-IMZO)→ SUBMITTED ─accept→ ACCEPTED ─sign(E-IMZO)→ SIGNED
  ▲          │withdraw        │send_back          │send_back
  └──────────┘                └──→ RETURNED ←─────┘  (исполнитель правит и снова подписывает)
Фонд может аннулировать акт до подписи руководителя (CANCELLED).

Править можно только DRAFT / RETURNED — в них подписей нет. Возврат снимает подписи.
Подписанный акт неизменяем: PDF формируется один раз и хранится вместе с SHA-256.
"""

import secrets
from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import UploadFile

from src.account.schemas.user_schema import CurrentUserDTO
from src.act.enums import (
    CANCELLABLE_STATUSES,
    EDITABLE_STATUSES,
    ActEventType,
    ActSignerRole,
    ActStatus,
    ContractStatus,
)
from src.act.hashing import content_hash, signature_hash
from src.act.mappers import map_act_detail, map_act_list_item
from src.act.models.act_model import (
    ActAttachmentORM,
    ActEventORM,
    ActItemORM,
    ActORM,
    ActSignatureORM,
    ContractORM,
)
from src.act.pdf import render_act_pdf
from src.act.schemas.act_schema import (
    DEFAULT_APPENDIX_TITLE,
    ActActionsDTO,
    ActAttachmentForm,
    ActAttachmentOrderDTO,
    ActAttachmentUpdateDTO,
    ActCreateDTO,
    ActDetailDTO,
    ActItemsDTO,
    ActSubmissionCheckDTO,
    ActUpdateDTO,
    ActVerifyDTO,
    ActVerifySignatureDTO,
    FundActFilterDTO,
    MyActFilterDTO,
)
from src.act.storage import ActFileStorage
from src.act.text import act_number
from src.auth.services.eimzo_service import EimzoService
from src.common.responses.exceptions import (
    ActAttachmentNotFoundException,
    ActContentChangedException,
    ActLimitException,
    ActNotApproverException,
    ActNotEditableException,
    ActNotFoundException,
    ActNotReadyException,
    ActPdfNotFoundException,
    ActPeriodException,
    ActPeriodOverlapException,
    ActStatusException,
    ContractClosedException,
    ContractNotFoundException,
    EimzoSignerMismatchException,
    PermissionDeniedException,
    UserNotFoundException,
)
from src.config import settings
from src.utils.base_service import BaseService

REVIEW_READ = "act_review.read"
REVIEW_APPROVE = "act_review.approve"
SIGNING = "act_signing.approve"
ACTS_UPDATE = "acts.update"
ACTS_DELETE = "acts.delete"


def utcnow() -> datetime:
    return datetime.now(UTC)


class ActService(BaseService):
    eimzo = EimzoService()
    storage = ActFileStorage()

    # ---------- загрузка и доступ ----------

    async def _get(self, act_id: int, *, for_update: bool = False) -> ActORM:
        act = await self.db.act.get_orm(act_id, for_update=for_update)
        if act is None:
            raise ActNotFoundException()
        return act

    async def _reload(self, act_id: int) -> ActORM:
        self.db.session.expire_all()
        return await self._get(act_id)

    async def _mine(self, act_id: int, user: CurrentUserDTO, *, for_update: bool = False) -> ActORM:
        act = await self._get(act_id, for_update=for_update)
        if act.contract.contractor_id != user.id:
            raise ActNotFoundException()
        return act

    @staticmethod
    def _is_approver(act: ActORM, user: CurrentUserDTO) -> bool:
        return act.contract.approver_id == user.id and user.has_permission(SIGNING)

    async def _fund(self, act_id: int, user: CurrentUserDTO, *, for_update: bool = False) -> ActORM:
        """Акт в рабочем окне Фонда: проверяющий видит все отправленные, руководитель —
        акты по своим договорам. Черновики Фонду не видны."""
        act = await self._get(act_id, for_update=for_update)
        if act.status == ActStatus.DRAFT:
            raise ActNotFoundException()
        if not (user.has_permission(REVIEW_READ) or self._is_approver(act, user)):
            raise ActNotFoundException()
        return act

    def actions(self, act: ActORM, user: CurrentUserDTO) -> ActActionsDTO:
        mine = act.contract.contractor_id == user.id
        editable = act.status in EDITABLE_STATUSES
        reviewer = user.has_permission(REVIEW_APPROVE)
        approver = self._is_approver(act, user)
        return ActActionsDTO(
            edit=mine and editable and user.has_permission(ACTS_UPDATE),
            delete=mine and act.status == ActStatus.DRAFT and user.has_permission(ACTS_DELETE),
            submit=mine and editable and user.has_permission(ACTS_UPDATE),
            withdraw=mine
            and act.status == ActStatus.SUBMITTED
            and user.has_permission(ACTS_UPDATE),
            accept=reviewer and act.status == ActStatus.SUBMITTED,
            send_back=(reviewer and act.status in (ActStatus.SUBMITTED, ActStatus.ACCEPTED))
            or (approver and act.status == ActStatus.ACCEPTED),
            sign=approver and act.status == ActStatus.ACCEPTED,
            cancel=reviewer
            and act.status in CANCELLABLE_STATUSES
            and act.status != ActStatus.DRAFT,
        )

    def _detail(self, act: ActORM, user: CurrentUserDTO) -> ActDetailDTO:
        return map_act_detail(act, self.actions(act, user))

    def _event(
        self,
        act: ActORM,
        event: ActEventType,
        from_status: ActStatus | None,
        user: CurrentUserDTO | None,
        comment: str | None = None,
    ) -> None:
        # Через сессию, а не act.events: у только что созданного акта коллекция не загружена.
        self.db.session.add(
            ActEventORM(
                act_id=act.id,
                event=event,
                from_status=from_status,
                to_status=act.status,
                actor_id=user.id if user else None,
                actor_name=(user.full_name or user.username) if user else None,
                comment=comment,
                created_at=utcnow(),
            )
        )

    # ---------- исполнитель: список и черновик ----------

    async def my_list(self, user: CurrentUserDTO, filters: MyActFilterDTO, page, per_page) -> dict:
        stmt = self.db.act.my_stmt(user.id, filters)
        return await self.db.act.paginate_list(stmt, page, per_page, map_act_list_item)

    async def my_counters(self, user: CurrentUserDTO) -> dict[str, int]:
        by_status = await self.db.act.count_mine_by_status(user.id)
        return {status.value.lower(): by_status.get(status, 0) for status in ActStatus}

    async def my_detail(self, act_id: int, user: CurrentUserDTO) -> ActDetailDTO:
        return self._detail(await self._mine(act_id, user), user)

    async def _check_period(
        self, contract: ContractORM, period_from: date, period_to: date, act_id: int | None
    ) -> None:
        if (
            period_to < period_from
            or period_from < contract.start_date
            or period_to > contract.end_date
        ):
            raise ActPeriodException()
        if await self.db.act.overlaps(contract.id, period_from, period_to, act_id):
            raise ActPeriodOverlapException()

    async def create(self, data: ActCreateDTO, user: CurrentUserDTO) -> ActDetailDTO:
        contract = await self.db.contract.get_orm(data.contract_id)
        if contract is None or contract.contractor_id != user.id:
            raise ContractNotFoundException(field="contract_id")
        if contract.status != ContractStatus.ACTIVE:
            raise ContractClosedException()
        await self._check_period(contract, data.period_from, data.period_to, None)

        source = None
        if data.copy_from_id is not None:
            source = await self._mine(data.copy_from_id, user)
            if source.contract_id != contract.id:
                raise ActNotFoundException(field="copy_from_id")

        act = ActORM(
            public_id=secrets.token_urlsafe(24),
            contract_id=contract.id,
            period_from=data.period_from,
            period_to=data.period_to,
            act_date=data.act_date or data.period_to,
            intro=source.intro if source else contract.subject,
            appendix_title=source.appendix_title if source else DEFAULT_APPENDIX_TITLE,
            status=ActStatus.DRAFT,
            created_by_id=user.id,
        )
        if source is not None:
            act.items = [
                ActItemORM(
                    position=i.position, content=i.content, period_text=i.period_text, note=i.note
                )
                for i in source.items
            ]
        await self.db.act.add_orm(act)
        act.number = act_number(act.id, act.act_date.year)
        self._event(act, ActEventType.CREATED, None, user)
        await self.db.commit()
        return self._detail(await self._reload(act.id), user)

    async def _editable(self, act_id: int, user: CurrentUserDTO) -> ActORM:
        act = await self._mine(act_id, user, for_update=True)
        if act.status not in EDITABLE_STATUSES:
            raise ActNotEditableException()
        return act

    async def update(self, act_id: int, data: ActUpdateDTO, user: CurrentUserDTO) -> ActDetailDTO:
        act = await self._editable(act_id, user)
        values = data.model_dump(exclude_unset=True, exclude_none=True)
        period_from = values.get("period_from", act.period_from)
        period_to = values.get("period_to", act.period_to)
        if "period_from" in values or "period_to" in values:
            await self._check_period(act.contract, period_from, period_to, act.id)
        for key, value in values.items():
            setattr(act, key, value)
        await self.db.commit()
        return self._detail(await self._reload(act.id), user)

    async def set_items(self, act_id: int, data: ActItemsDTO, user: CurrentUserDTO) -> ActDetailDTO:
        act = await self._editable(act_id, user)
        act.items.clear()
        await self.db.flush()
        for index, item in enumerate(data.items):
            act.items.append(
                ActItemORM(
                    position=index,
                    content=item.content,
                    period_text=item.period_text,
                    note=item.note or None,
                )
            )
        await self.db.commit()
        return self._detail(await self._reload(act.id), user)

    async def delete(self, act_id: int, user: CurrentUserDTO) -> None:
        act = await self._mine(act_id, user, for_update=True)
        if act.status != ActStatus.DRAFT:
            raise ActNotEditableException("Only a draft that was never submitted can be deleted")
        await self.db.act.delete_orm(act)
        await self.db.commit()
        await self.storage.delete_act_dir(act_id)

    # ---------- приложение (скриншоты) ----------

    async def add_attachment(
        self, act_id: int, form: ActAttachmentForm, user: CurrentUserDTO
    ) -> ActDetailDTO:
        act = await self._editable(act_id, user)
        if len(act.attachments) >= settings.ACT_MAX_ATTACHMENTS:
            raise ActLimitException(
                f"An appendix holds at most {settings.ACT_MAX_ATTACHMENTS} files", field="file"
            )
        upload: UploadFile = form.file
        path, size, content_type = await self.storage.save(act.id, upload)
        sha = await self.storage.sha256(path)
        position = max((a.position for a in act.attachments), default=-1) + 1
        act.attachments.append(
            ActAttachmentORM(
                position=position,
                caption=form.caption,
                url=form.url or None,
                file_path=path,
                file_name=(upload.filename or "")[:255] or None,
                content_type=content_type,
                file_size=size,
                sha256=sha,
            )
        )
        await self.db.commit()
        return self._detail(await self._reload(act.id), user)

    async def update_attachment(
        self, act_id: int, attachment_id: int, data: ActAttachmentUpdateDTO, user: CurrentUserDTO
    ) -> ActDetailDTO:
        act = await self._editable(act_id, user)
        attachment = await self._attachment(act, attachment_id)
        values = data.model_dump(exclude_unset=True)
        if values.get("caption"):
            attachment.caption = values["caption"]
        if "url" in values:
            attachment.url = values["url"] or None
        await self.db.commit()
        return self._detail(await self._reload(act.id), user)

    async def delete_attachment(
        self, act_id: int, attachment_id: int, user: CurrentUserDTO
    ) -> ActDetailDTO:
        act = await self._editable(act_id, user)
        attachment = await self._attachment(act, attachment_id)
        path = attachment.file_path
        act.attachments.remove(attachment)
        await self.db.commit()
        await self.storage.delete(path)
        return self._detail(await self._reload(act.id), user)

    async def order_attachments(
        self, act_id: int, data: ActAttachmentOrderDTO, user: CurrentUserDTO
    ) -> ActDetailDTO:
        act = await self._editable(act_id, user)
        current = {a.id: a for a in act.attachments}
        if sorted(data.ids) != sorted(current):
            raise ActLimitException("List every appendix file exactly once", field="ids")
        for index, attachment_id in enumerate(data.ids):
            current[attachment_id].position = index
        await self.db.commit()
        return self._detail(await self._reload(act.id), user)

    @staticmethod
    async def _attachment(act: ActORM, attachment_id: int) -> ActAttachmentORM:
        attachment = next((a for a in act.attachments if a.id == attachment_id), None)
        if attachment is None:
            raise ActAttachmentNotFoundException()
        return attachment

    async def attachment_file(self, act: ActORM, attachment_id: int) -> tuple[Path, str, str]:
        attachment = await self._attachment(act, attachment_id)
        path = self.storage.absolute_path(attachment.file_path)
        if not path.exists():
            raise ActAttachmentNotFoundException()
        name = attachment.file_name or f"ilova-{attachment.position + 1}{path.suffix}"
        return path, attachment.content_type, name

    async def my_attachment_file(self, act_id: int, attachment_id: int, user: CurrentUserDTO):
        return await self.attachment_file(await self._mine(act_id, user), attachment_id)

    async def fund_attachment_file(self, act_id: int, attachment_id: int, user: CurrentUserDTO):
        return await self.attachment_file(await self._fund(act_id, user), attachment_id)

    # ---------- отправка исполнителем ----------

    @staticmethod
    def missing(act: ActORM) -> list[str]:
        missing = []
        if not act.items:
            missing.append("items")
        if not (act.intro or "").strip():
            missing.append("intro")
        if act.contract.status != ContractStatus.ACTIVE:
            missing.append("contract")
        contractor = act.contract.contractor
        if contractor is None or not contractor.pinfl:
            missing.append("contractor.pinfl")
        return missing

    async def submission_check(self, act_id: int, user: CurrentUserDTO) -> ActSubmissionCheckDTO:
        act = await self._mine(act_id, user)
        missing = self.missing(act)
        return ActSubmissionCheckDTO(ready=not missing, missing=missing)

    async def _certificate(self, code: str, user_id: int):
        """Проверяет код моста E-IMZO и что ключ принадлежит этому пользователю."""
        person = await self.db.user.get_orm_by_id(user_id)
        if person is None:
            raise UserNotFoundException()
        certificate = await self.eimzo.verify_code(code)
        if not person.pinfl or certificate.pinfl != person.pinfl:
            raise EimzoSignerMismatchException()
        return certificate

    @staticmethod
    def _signature(act: ActORM, role: ActSignerRole, user: CurrentUserDTO, certificate, previous):
        signed_at = utcnow()
        return ActSignatureORM(
            role=role,
            signer_id=user.id,
            signer_full_name=user.full_name or user.username,
            signed_at=signed_at,
            cert_pinfl=certificate.pinfl,
            cert_full_name=certificate.full_name,
            cert_serial_number=certificate.serial_number,
            cert_valid_from=certificate.valid_from,
            cert_valid_to=certificate.valid_to,
            cert_tin=certificate.individual_tin,
            eimzo_request_id=certificate.request_id,
            document_hash=signature_hash(
                act.content_hash, role.value, certificate.pinfl, signed_at, previous
            ),
        )

    async def submit(self, act_id: int, code: str, user: CurrentUserDTO) -> ActDetailDTO:
        act = await self._editable(act_id, user)
        missing = self.missing(act)
        if missing:
            raise ActNotReadyException(missing)
        await self._check_period(act.contract, act.period_from, act.period_to, act.id)
        certificate = await self._certificate(code, user.id)

        previous_status = act.status
        act.content_hash = content_hash(act)
        act.signatures.append(
            self._signature(act, ActSignerRole.CONTRACTOR, user, certificate, None)
        )
        act.status = ActStatus.SUBMITTED
        act.submitted_at = utcnow()
        act.return_comment = None
        act.returned_at = None
        self._event(act, ActEventType.SUBMITTED, previous_status, user)
        await self.db.commit()
        return self._detail(await self._reload(act.id), user)

    async def withdraw(self, act_id: int, user: CurrentUserDTO) -> ActDetailDTO:
        act = await self._mine(act_id, user, for_update=True)
        if act.status != ActStatus.SUBMITTED:
            raise ActStatusException()
        act.signatures.clear()
        act.content_hash = None
        act.submitted_at = None
        act.status = ActStatus.DRAFT
        self._event(act, ActEventType.WITHDRAWN, ActStatus.SUBMITTED, user)
        await self.db.commit()
        return self._detail(await self._reload(act.id), user)

    # ---------- Фонд ----------

    async def fund_list(
        self, user: CurrentUserDTO, filters: FundActFilterDTO, page, per_page
    ) -> dict:
        if not user.has_permission(REVIEW_READ):
            filters.mine = True  # руководитель без права проверки видит только свои договоры
        stmt = self.db.act.fund_stmt(filters, user.id)
        return await self.db.act.paginate_list(stmt, page, per_page, map_act_list_item)

    async def fund_counters(self, user: CurrentUserDTO) -> dict[str, int]:
        counters = {s.value.lower(): 0 for s in ActStatus if s != ActStatus.DRAFT}
        if user.has_permission(REVIEW_READ):
            by_status = await self.db.act.count_by_status()
            counters.update(
                {s.value.lower(): n for s, n in by_status.items() if s != ActStatus.DRAFT}
            )
        counters["to_sign_mine"] = await self.db.act.count_to_sign_by(user.id)
        return counters

    async def fund_detail(self, act_id: int, user: CurrentUserDTO) -> ActDetailDTO:
        return self._detail(await self._fund(act_id, user), user)

    def _assert_unchanged(self, act: ActORM) -> None:
        if act.content_hash != content_hash(act):
            raise ActContentChangedException()

    async def accept(self, act_id: int, user: CurrentUserDTO) -> ActDetailDTO:
        act = await self._fund(act_id, user, for_update=True)
        if act.status != ActStatus.SUBMITTED:
            raise ActStatusException()
        self._assert_unchanged(act)
        act.status = ActStatus.ACCEPTED
        act.accepted_at = utcnow()
        act.accepted_by_id = user.id
        self._event(act, ActEventType.ACCEPTED, ActStatus.SUBMITTED, user)
        await self.db.commit()
        return self._detail(await self._reload(act.id), user)

    async def send_back(self, act_id: int, comment: str, user: CurrentUserDTO) -> ActDetailDTO:
        act = await self._fund(act_id, user, for_update=True)
        if not self.actions(act, user).send_back:
            if act.status not in (ActStatus.SUBMITTED, ActStatus.ACCEPTED):
                raise ActStatusException()
            raise PermissionDeniedException()
        previous_status = act.status
        act.signatures.clear()
        act.content_hash = None
        act.accepted_at = None
        act.accepted_by_id = None
        act.status = ActStatus.RETURNED
        act.returned_at = utcnow()
        act.return_comment = comment
        self._event(act, ActEventType.RETURNED, previous_status, user, comment)
        await self.db.commit()
        return self._detail(await self._reload(act.id), user)

    async def cancel(self, act_id: int, reason: str, user: CurrentUserDTO) -> ActDetailDTO:
        act = await self._fund(act_id, user, for_update=True)
        if act.status not in CANCELLABLE_STATUSES:
            raise ActStatusException()
        previous_status = act.status
        act.status = ActStatus.CANCELLED
        act.cancelled_at = utcnow()
        act.cancel_reason = reason
        self._event(act, ActEventType.CANCELLED, previous_status, user, reason)
        await self.db.commit()
        return self._detail(await self._reload(act.id), user)

    async def sign(self, act_id: int, code: str, user: CurrentUserDTO) -> ActDetailDTO:
        act = await self._fund(act_id, user, for_update=True)
        if not self._is_approver(act, user):
            raise ActNotApproverException()
        if act.status != ActStatus.ACCEPTED:
            raise ActStatusException()
        self._assert_unchanged(act)
        certificate = await self._certificate(code, user.id)

        contractor_signature = next(
            (s for s in act.signatures if s.role == ActSignerRole.CONTRACTOR), None
        )
        if contractor_signature is None:
            raise ActStatusException("The contractor signature is missing")
        signature = self._signature(
            act, ActSignerRole.APPROVER, user, certificate, contractor_signature.document_hash
        )
        act.signatures.append(signature)
        act.status = ActStatus.SIGNED
        act.signed_at = signature.signed_at
        self._event(act, ActEventType.SIGNED, ActStatus.ACCEPTED, user)
        await self.db.flush()

        pdf = render_act_pdf(act, utcnow())
        act.final_pdf_path = await self.storage.save_pdf(act.id, pdf)
        act.final_pdf_sha256 = ActFileStorage.sha256_bytes(pdf)
        await self.db.commit()
        return self._detail(await self._reload(act.id), user)

    # ---------- PDF ----------

    async def _pdf(self, act: ActORM) -> tuple[bytes, str]:
        name = f"{act.number or act.id}.pdf"
        if act.status == ActStatus.SIGNED:
            if not act.final_pdf_path:
                raise ActPdfNotFoundException()
            path = self.storage.absolute_path(act.final_pdf_path)
            if not path.exists():
                raise ActPdfNotFoundException()
            return await self.storage.read(act.final_pdf_path), name
        return render_act_pdf(act, utcnow()), name

    async def my_pdf(self, act_id: int, user: CurrentUserDTO) -> tuple[bytes, str]:
        return await self._pdf(await self._mine(act_id, user))

    async def fund_pdf(self, act_id: int, user: CurrentUserDTO) -> tuple[bytes, str]:
        return await self._pdf(await self._fund(act_id, user))

    # ---------- проверка по QR ----------

    async def verify(self, public_id: str) -> ActVerifyDTO:
        act = await self.db.act.get_orm_by_public_id(public_id)
        if act is None or act.status == ActStatus.DRAFT:
            raise ActNotFoundException()
        unchanged = act.content_hash is not None and act.content_hash == content_hash(act)
        if act.status == ActStatus.CANCELLED:
            validity = "CANCELLED"
        elif act.status != ActStatus.SIGNED:
            validity = "NOT_SIGNED"
        elif not unchanged:
            validity = "MODIFIED"
        else:
            validity = "VALID"
        contract = act.contract
        return ActVerifyDTO(
            number=act.number,
            status=act.status,
            validity=validity,
            contract_number=contract.number,
            contract_signed_on=contract.signed_on,
            contractor_name=contract.contractor_name,
            approver_name=contract.approver_name,
            period_from=act.period_from,
            period_to=act.period_to,
            act_date=act.act_date,
            signatures=[
                ActVerifySignatureDTO(
                    role=s.role,
                    name=s.cert_full_name or s.signer_full_name,
                    signed_at=s.signed_at,
                    cert_serial_number=s.cert_serial_number,
                )
                for s in act.signatures
            ],
            content_unchanged=unchanged,
            pdf_sha256=act.final_pdf_sha256,
        )
