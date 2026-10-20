"""Админ-панель на SQLAdmin (Tabler UI): вход только для роли с is_superuser."""

import asyncio
from pathlib import Path

from fastapi import FastAPI
from markupsafe import Markup
from sqladmin import Admin
from sqladmin.authentication import AuthenticationBackend, login_required
from sqlalchemy import func, select
from starlette.requests import Request
from starlette.responses import Response

from src.account.models.user_model import UserORM, UserStatus
from src.admin.views import ALL_VIEWS
from src.application.enums import ApplicationStatus
from src.application.models.application_model import ApplicationORM
from src.application.models.bank_model import BankORM
from src.auth.services.password_service import verify_password
from src.config import settings
from src.database import async_session_maker, engine
from src.rbac.models.role_model import RoleORM
from src.utils.db_manager import DBManager

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

STATUS_LABELS: dict[str, tuple[str, str]] = {
    "DRAFT": ("Черновик", "secondary"),
    "SUBMITTED": ("Подана", "blue"),
    "SCORING_IN_PROGRESS": ("Скоринг KATM", "azure"),
    "SCORING_FAILED": ("Скоринг не пройден", "red"),
    "ELIGIBILITY_FAILED": ("Не соответствует требованиям", "red"),
    "READY_FOR_BANK": ("Готова к отправке в банк", "cyan"),
    "SENT_TO_BANK": ("Отправлена в банк", "indigo"),
    "BANK_REVIEW": ("Банк рассматривает", "purple"),
    "BANK_APPROVED": ("Банк одобрил", "teal"),
    "BANK_REJECTED": ("Банк отказал", "red"),
    "COUNCIL_REVIEW": ("Рассмотрение Советом", "orange"),
    "COUNCIL_APPROVED": ("Совет утвердил", "lime"),
    "COUNCIL_REJECTED": ("Совет отказал", "red"),
    "DEMAND_DOCUMENT_CREATED": ("Требование подтверждено", "green"),
    "RESOURCE_ALLOCATION": ("Выделение ресурсов", "yellow"),
    "COMPLETED": ("Завершена", "success"),
}

PIPELINE_GROUPS: list[tuple[str, list[str]]] = [
    ("Черновики", ["DRAFT"]),
    ("Скоринг", ["SUBMITTED", "SCORING_IN_PROGRESS"]),
    ("Банк", ["READY_FOR_BANK", "SENT_TO_BANK", "BANK_REVIEW"]),
    ("Фонд → Совет", ["BANK_APPROVED", "COUNCIL_REVIEW"]),
    ("Финансирование", ["COUNCIL_APPROVED", "DEMAND_DOCUMENT_CREATED", "RESOURCE_ALLOCATION"]),
    ("Завершены", ["COMPLETED"]),
    ("Отклонены", ["SCORING_FAILED", "ELIGIBILITY_FAILED", "BANK_REJECTED", "COUNCIL_REJECTED"]),
]


def status_badge(value) -> Markup:
    key = value.value if isinstance(value, ApplicationStatus) else str(value)
    label, color = STATUS_LABELS.get(key, (key, "secondary"))
    return Markup(f'<span class="badge bg-{color}-lt">{label}</span>')


class AdminAuth(AuthenticationBackend):
    """Логин/пароль платформы; в админку пускается только суперпользователь."""

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = str(form.get("username", "")).strip()
        password = str(form.get("password", ""))

        async with DBManager(session_factory=async_session_maker) as db:
            user = await db.user.get_orm_by_username(username)
            is_valid = await asyncio.to_thread(
                verify_password, password, user.hashed_password if user else None
            )

            if (
                user is None
                or not is_valid
                or user.status != UserStatus.ACTIVE
                or user.role is None
                or not user.role.is_superuser
            ):
                return False

            await db.user.touch_last_login(user.id)
            await db.commit()

        request.session.update({"user_id": user.id, "username": user.username})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        user_id = request.session.get("user_id")
        if not user_id:
            return False

        async with DBManager(session_factory=async_session_maker) as db:
            access = await db.user.get_access(int(user_id))

        if access is None or not access.is_active or not access.is_superuser:
            request.session.clear()
            return False

        request.state.admin_user = access
        return True


class JamgarmaAdmin(Admin):
    """Admin с дашбордом на главной странице."""

    @login_required
    async def index(self, request: Request) -> Response:
        async with async_session_maker() as session:
            by_status = dict(
                (
                    await session.execute(
                        select(ApplicationORM.status, func.count()).group_by(ApplicationORM.status)
                    )
                ).all()
            )
            counts = {status.value: by_status.get(status, 0) for status in ApplicationStatus}

            users_total = await session.scalar(select(func.count()).select_from(UserORM)) or 0
            users_active = (
                await session.scalar(
                    select(func.count())
                    .select_from(UserORM)
                    .where(UserORM.status == UserStatus.ACTIVE)
                )
                or 0
            )
            roles_total = await session.scalar(select(func.count()).select_from(RoleORM)) or 0
            banks_active = (
                await session.scalar(
                    select(func.count()).select_from(BankORM).where(BankORM.is_active.is_(True))
                )
                or 0
            )

            recent = (
                await session.scalars(
                    select(ApplicationORM).order_by(ApplicationORM.updated_at.desc()).limit(8)
                )
            ).all()
            recent_logins = (
                await session.scalars(
                    select(UserORM)
                    .where(UserORM.last_login_at.is_not(None))
                    .order_by(UserORM.last_login_at.desc())
                    .limit(6)
                )
            ).all()

        total_apps = sum(counts.values())
        pipeline = [
            {
                "title": title,
                "count": sum(counts[s] for s in statuses),
                "statuses": [
                    (STATUS_LABELS[s][0], STATUS_LABELS[s][1], counts[s]) for s in statuses
                ],
            }
            for title, statuses in PIPELINE_GROUPS
        ]
        needs_attention = {
            "scoring_retry": await self._count_retry(),
            "to_council": counts["BANK_APPROVED"],
            "to_allocate": counts["DEMAND_DOCUMENT_CREATED"],
            "new_for_bank": counts["SENT_TO_BANK"],
        }

        return await self.templates.TemplateResponse(
            request,
            "sqladmin/index.html",
            {
                "total_apps": total_apps,
                "users_total": users_total,
                "users_active": users_active,
                "roles_total": roles_total,
                "banks_active": banks_active,
                "pipeline": pipeline,
                "needs_attention": needs_attention,
                "recent": recent,
                "recent_logins": recent_logins,
                "status_badge": status_badge,
                "scoring_mode": settings.SCORING_MODE,
                "oneid_mock": settings.ONEID_MOCK,
            },
        )

    @staticmethod
    async def _count_retry() -> int:
        async with async_session_maker() as session:
            return (
                await session.scalar(
                    select(func.count())
                    .select_from(ApplicationORM)
                    .where(ApplicationORM.scoring_retry_required.is_(True))
                )
                or 0
            )


def setup_admin(app: FastAPI) -> Admin:
    admin = JamgarmaAdmin(
        app,
        engine,
        title="Jamg'arma · Admin",
        base_url="/admin",
        templates_dir=str(TEMPLATES_DIR),
        authentication_backend=AdminAuth(secret_key=settings.ADMIN_SESSION_SECRET),
    )

    for view in ALL_VIEWS:
        admin.add_view(view)

    return admin
