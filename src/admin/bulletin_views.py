"""Админ-панель: бюллетени Совета и подписи членов Совета.

Создание и правка бюллетеня — в рабочем окне Фонда (API `/fund/bulletins`): там дата
отправки, файл и привязка к заявке проверяются вместе. Здесь Super Admin видит все
бюллетени, статус подписания по каждому члену Совета, файл и QR-код, может отправить
отложенный бюллетень сейчас, аннулировать бюллетень или удалить его целиком
(единственное право override на удаление подписанного бюллетеня — по ТЗ).
"""

from __future__ import annotations

from markupsafe import Markup, escape
from sqladmin import BaseView, ModelView, action, expose
from sqladmin.filters import StaticValuesFilter
from sqlalchemy.orm import selectinload
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse, RedirectResponse, Response

from src.admin.i18n import _, _l, fmt_dt
from src.admin.labels import (
    BULLETIN_DECISION_LABELS,
    BULLETIN_STATUS_LABELS,
    labeled_badge,
    status_badge,
)
from src.admin.views import LocalizedLabelsMixin, fmt_datetime
from src.bulletin.enums import BulletinDecision, BulletinStatus
from src.bulletin.mappers import member_status, summary, verify_url
from src.bulletin.models.bulletin_model import BulletinORM, BulletinSignatureORM
from src.bulletin.qr import qr_svg
from src.bulletin.schemas.bulletin_schema import BulletinCancelDTO
from src.bulletin.services.bulletin_service import BulletinService, utcnow
from src.bulletin.storage import BulletinFileStorage
from src.common.responses.exceptions import ApiException
from src.database import async_session_maker
from src.utils.db_manager import DBManager

CATEGORY_BULLETINS = _l("Бюллетени Совета")


def fmt_bulletin_status(model, attribute) -> Markup | str:
    return labeled_badge(BULLETIN_STATUS_LABELS, model.status)


def fmt_bulletin_decision(model, attribute) -> Markup | str:
    return labeled_badge(BULLETIN_DECISION_LABELS, model.decision)


def fmt_bulletin_application(model, attribute) -> Markup | str:
    application = getattr(model, "application", None)
    if application is None:
        return "—"
    return Markup(
        f'<a href="/admin/application-orm/details/{application.id}">'
        f"{escape(application.number)}</a> "
    ) + status_badge(application.status)


def fmt_bulletin_progress(model, attribute) -> Markup | str:
    if model.status == BulletinStatus.PENDING:
        return "—"
    counts = summary(model)
    color = "green" if counts.total and counts.signed == counts.total else "orange"
    return Markup(f'<span class="badge bg-{color}-lt">{counts.signed} / {counts.total}</span>')


def fmt_bulletin_deadline(model, attribute) -> Markup | str:
    text = escape(fmt_dt(model.deadline_at))
    overdue = (
        model.status
        in (
            BulletinStatus.PUBLISHED,
            BulletinStatus.PARTIALLY_SIGNED,
        )
        and utcnow() > model.deadline_at
    )
    if overdue:
        return Markup(f'<span class="text-danger fw-semibold">{text}</span> ') + Markup(
            f'<span class="badge bg-red-lt">{escape(_("просрочен"))}</span>'
        )
    return Markup(text)


def fmt_signature_bulletin(model, attribute) -> Markup | str:
    bulletin = model.bulletin
    return Markup(
        f'<a href="/admin/bulletin-orm/details/{bulletin.id}">{escape(bulletin.number)}</a>'
        f" · {escape(bulletin.name)}"
    )


def fmt_signature_member(model, attribute) -> Markup | str:
    member = model.council_member
    name = model.member_full_name or (member.full_name if member else None) or "—"
    if member is None:
        return name
    return Markup(f'<a href="/admin/user-orm/details/{member.id}">{escape(name)}</a>')


class BulletinAdmin(LocalizedLabelsMixin, ModelView, model=BulletinORM):
    name = _l("Бюллетень")
    name_plural = _l("Бюллетени")
    icon = "fa-solid fa-file-signature"
    category = CATEGORY_BULLETINS
    details_template = "sqladmin/bulletin_details.html"

    column_list = [
        BulletinORM.id,
        BulletinORM.number,
        BulletinORM.name,
        BulletinORM.status,
        BulletinORM.application,
        BulletinORM.signatures,
        BulletinORM.send_at,
        BulletinORM.deadline_at,
        BulletinORM.created_at,
    ]
    column_searchable_list = [BulletinORM.number, BulletinORM.name]
    column_sortable_list = [
        BulletinORM.id,
        BulletinORM.send_at,
        BulletinORM.deadline_at,
        BulletinORM.created_at,
    ]
    column_default_sort = [(BulletinORM.id, True)]
    column_filters = [
        StaticValuesFilter(
            BulletinORM.status,
            [(s.value, _l(BULLETIN_STATUS_LABELS[s.value][0])) for s in BulletinStatus],
            title=_l("Статус"),
        ),
    ]
    column_labels = {
        BulletinORM.id: "ID",
        BulletinORM.number: "Номер",
        BulletinORM.name: "Название",
        BulletinORM.description: "Описание",
        BulletinORM.status: "Статус",
        BulletinORM.application: "Заявка",
        BulletinORM.application_id: "Заявка",
        BulletinORM.signatures: "Подписи",
        BulletinORM.send_at: "Отправка",
        BulletinORM.published_at: "Отправлен",
        BulletinORM.deadline_at: "Срок подписания",
        BulletinORM.completed_at: "Подписан всеми",
        BulletinORM.created_at: "Создан",
        BulletinORM.updated_at: "Обновлён",
    }
    column_formatters = {
        BulletinORM.status: fmt_bulletin_status,
        BulletinORM.application: fmt_bulletin_application,
        BulletinORM.signatures: fmt_bulletin_progress,
        BulletinORM.send_at: fmt_datetime,
        BulletinORM.deadline_at: fmt_bulletin_deadline,
        BulletinORM.created_at: fmt_datetime,
    }
    can_create = False
    can_edit = False
    can_delete = True
    can_export = False
    page_size = 25

    async def get_object_for_details(self, request: Request):
        stmt = self.details_query(request).options(
            selectinload(BulletinORM.signatures).selectinload(BulletinSignatureORM.council_member),
            selectinload(BulletinORM.application),
            selectinload(BulletinORM.created_by),
            selectinload(BulletinORM.cancelled_by),
        )
        bulletin = await self._get_object_by_pk(stmt)
        if bulletin is not None:
            now = utcnow()
            bulletin.admin_rows = [
                (signature, member_status(bulletin, signature, now).value)
                for signature in bulletin.signatures
            ]
            bulletin.admin_summary = summary(bulletin)
            bulletin.admin_verify_url = verify_url(bulletin)
            bulletin.admin_overdue = (
                bulletin.status in (BulletinStatus.PUBLISHED, BulletinStatus.PARTIALLY_SIGNED)
                and now > bulletin.deadline_at
            )
        return bulletin

    async def delete_model(self, request: Request, pk) -> None:
        """Удаление целиком (override Super Admin): подписи, файл; заявка, которую
        Совет ещё не решил, возвращается Фонду."""
        async with DBManager(async_session_maker) as db:
            await BulletinService(db).purge(int(pk), request.state.admin_user)

    async def _run(self, request: Request, handler) -> Response:
        pks = [pk for pk in request.query_params.get("pks", "").split(",") if pk]
        if not pks:
            raise HTTPException(status_code=400, detail=_("Не выбран бюллетень"))
        async with DBManager(async_session_maker) as db:
            service = BulletinService(db)
            for pk in pks:
                try:
                    await handler(service, int(pk), request.state.admin_user)
                except ApiException as exc:
                    raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
        target = (
            request.url_for("admin:details", identity=self.identity, pk=pks[0])
            if len(pks) == 1
            else request.url_for("admin:list", identity=self.identity)
        )
        return RedirectResponse(target, status_code=302)

    @action(
        name="publish",
        label=_l("Отправить сейчас"),
        confirmation_message=_l("Отправить бюллетень всем активным членам Совета сейчас?"),
        add_in_list=False,
    )
    async def publish_action(self, request: Request) -> Response:
        return await self._run(request, lambda s, pk, user: s.publish(pk, user))

    @action(
        name="cancel",
        label=_l("Аннулировать"),
        confirmation_message=_l(
            "Аннулировать бюллетень? Подписи сохранятся, страница проверки по QR покажет "
            "«Аннулирован», заявка без итогового решения вернётся Фонду."
        ),
        add_in_list=False,
    )
    async def cancel_action(self, request: Request) -> Response:
        reason = BulletinCancelDTO(reason="Аннулирован Super Admin в админ-панели")
        return await self._run(request, lambda s, pk, user: s.cancel(pk, user, reason))


class BulletinSignatureAdmin(LocalizedLabelsMixin, ModelView, model=BulletinSignatureORM):
    name = _l("Подпись бюллетеня")
    name_plural = _l("Подписи членов Совета")
    icon = "fa-solid fa-signature"
    category = CATEGORY_BULLETINS

    column_list = [
        BulletinSignatureORM.id,
        BulletinSignatureORM.bulletin,
        BulletinSignatureORM.council_member,
        BulletinSignatureORM.viewed_at,
        BulletinSignatureORM.decision,
        BulletinSignatureORM.signed_at,
        BulletinSignatureORM.cert_serial_number,
    ]
    column_details_list = [
        BulletinSignatureORM.id,
        BulletinSignatureORM.bulletin,
        BulletinSignatureORM.council_member,
        BulletinSignatureORM.assigned_at,
        BulletinSignatureORM.viewed_at,
        BulletinSignatureORM.file_viewed_at,
        BulletinSignatureORM.decision,
        BulletinSignatureORM.comment,
        BulletinSignatureORM.signed_at,
        BulletinSignatureORM.cert_full_name,
        BulletinSignatureORM.cert_pinfl,
        BulletinSignatureORM.cert_serial_number,
        BulletinSignatureORM.cert_valid_from,
        BulletinSignatureORM.cert_valid_to,
        BulletinSignatureORM.eimzo_request_id,
        BulletinSignatureORM.document_hash,
    ]
    column_searchable_list = [
        BulletinSignatureORM.member_full_name,
        BulletinSignatureORM.cert_serial_number,
    ]
    column_default_sort = [(BulletinSignatureORM.id, True)]
    column_filters = [
        StaticValuesFilter(
            BulletinSignatureORM.decision,
            [(d.value, _l(BULLETIN_DECISION_LABELS[d.value][0])) for d in BulletinDecision],
            title=_l("Решение"),
        ),
    ]
    column_labels = {
        BulletinSignatureORM.id: "ID",
        BulletinSignatureORM.bulletin: "Бюллетень",
        BulletinSignatureORM.council_member: "Член Совета",
        BulletinSignatureORM.member_full_name: "Член Совета",
        BulletinSignatureORM.assigned_at: "Направлен",
        BulletinSignatureORM.viewed_at: "Открыл",
        BulletinSignatureORM.file_viewed_at: "Открыл файл",
        BulletinSignatureORM.decision: "Решение",
        BulletinSignatureORM.comment: "Комментарий",
        BulletinSignatureORM.signed_at: "Подписал",
        BulletinSignatureORM.cert_full_name: "Владелец сертификата",
        BulletinSignatureORM.cert_pinfl: "ПИНФЛ сертификата",
        BulletinSignatureORM.cert_serial_number: "Серийный номер сертификата",
        BulletinSignatureORM.cert_valid_from: "Сертификат действует с",
        BulletinSignatureORM.cert_valid_to: "Сертификат действует до",
        BulletinSignatureORM.eimzo_request_id: "ID запроса E-IMZO",
        BulletinSignatureORM.document_hash: "SHA-256 подписанного содержимого",
    }
    column_formatters = {
        BulletinSignatureORM.bulletin: fmt_signature_bulletin,
        BulletinSignatureORM.council_member: fmt_signature_member,
        BulletinSignatureORM.decision: fmt_bulletin_decision,
        BulletinSignatureORM.assigned_at: fmt_datetime,
        BulletinSignatureORM.viewed_at: fmt_datetime,
        BulletinSignatureORM.file_viewed_at: fmt_datetime,
        BulletinSignatureORM.signed_at: fmt_datetime,
    }
    column_formatters_detail = column_formatters
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 50


class BulletinFileView(BaseView):
    """Файл и QR-код бюллетеня под cookie-сессией админки. В меню не показывается."""

    name = _l("Файл бюллетеня")

    def is_visible(self, request: Request) -> bool:
        return False

    @staticmethod
    async def _bulletin(request: Request) -> BulletinORM:
        try:
            pk = int(request.path_params["pk"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=404) from None
        async with async_session_maker() as session:
            bulletin = await session.get(BulletinORM, pk)
        if bulletin is None:
            raise HTTPException(status_code=404)
        return bulletin

    @expose("/bulletin-file/{pk}", methods=["GET"], include_in_schema=False)
    async def bulletin_file(self, request: Request):
        bulletin = await self._bulletin(request)
        if not bulletin.file_path:
            raise HTTPException(status_code=404)
        path = BulletinFileStorage().absolute_path(bulletin.file_path)
        if not path.is_file():
            raise HTTPException(status_code=404)
        inline = bulletin.file_content_type == "application/pdf"
        return FileResponse(
            path,
            media_type=bulletin.file_content_type,
            filename=bulletin.file_name,
            content_disposition_type="inline" if inline else "attachment",
        )

    @expose("/bulletin-qr/{pk}", methods=["GET"], include_in_schema=False)
    async def bulletin_qr(self, request: Request):
        bulletin = await self._bulletin(request)
        disposition = "attachment" if request.query_params.get("download") else "inline"
        return Response(
            qr_svg(verify_url(bulletin)),
            media_type="image/svg+xml",
            headers={
                "Content-Disposition": (
                    f'{disposition}; filename="{bulletin.number or bulletin.id}-qr.svg"'
                )
            },
        )


BULLETIN_VIEWS = [BulletinAdmin, BulletinSignatureAdmin, BulletinFileView]
